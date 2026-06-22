#!/usr/bin/env python3
"""First-run setup API: drive the browser setup wizard.

Reports what is still missing (API key, Google credentials, OAuth token, applicant
identity), accepts the Anthropic key (a secret the generic config API refuses to
write), saves an uploaded ``credentials.json``, runs the Google OAuth flow, and
records a "don't show again" dismissal. Applicant identity and the optional Drive/
sheet/template IDs are set through the existing config API (non-secret).
"""

import json
import logging
import threading
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from jobjob.config import APP_KEYS, PROFILE_KEYS
from services.config_service import _parse_env_line, read_config

router = APIRouter()

_DISMISS_MARKER = ".setup_dismissed"

# OAuth runs in a background thread (run_local_server blocks until consent); the
# wizard polls /status for the resulting token. Single-user local app → module state.
_auth_state: dict = {"running": False, "error": None}


def _set_env_key(path: Path, key: str, value: str) -> None:
    """Upsert ``key=value`` in a dotenv file, preserving other lines."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    out: list[str] = []
    found = False
    for line in lines:
        parsed = _parse_env_line(line)
        if parsed and parsed[0] == key:
            out.append(f'{key}="{value}"')
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f'{key}="{value}"')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _key_is_set(env_path: Path, key: str, keys) -> bool:
    cfg = read_config(env_path, keys=keys)
    return bool(cfg.get(key, {}).get("is_set"))


@router.get("/status")
def setup_status(request: Request) -> dict:
    """Report which setup essentials are present, plus the dismissed flag."""
    s = request.app.state
    settings = s.settings
    app_config = Path(s.app_config_path)
    profile_config = s.profile_config_path

    anthropic = _key_is_set(app_config, "ANTHROPIC_API_KEY", APP_KEYS)
    creds = settings.get("credentials_file")
    has_creds = bool(creds and Path(creds).is_file())
    token = settings.get("token_file")
    has_token = bool(token and Path(token).is_file())
    applicant = bool(
        profile_config
        and _key_is_set(Path(profile_config), "APPLICANT_NAME", PROFILE_KEYS)
    )
    dismissed = (app_config.parent / _DISMISS_MARKER).is_file()

    # Essentials for a usable run: the API key + an applicant name. Google is optional
    # (local-only mode), so it does not gate completeness.
    complete = anthropic and applicant
    return {
        "anthropic_key": anthropic,
        "credentials_file": has_creds,
        "google_token": has_token,
        "applicant": applicant,
        "dismissed": dismissed,
        "complete": complete,
        "auth_running": _auth_state["running"],
        "auth_error": _auth_state["error"],
    }


class SecretUpdate(BaseModel):
    value: str


@router.put("/anthropic-key")
def set_anthropic_key(body: SecretUpdate, request: Request) -> dict:
    """Write the Anthropic API key to the app config (a secret the API blocks)."""
    if not body.value.strip():
        raise HTTPException(status_code=400, detail="Empty API key.")
    _set_env_key(
        Path(request.app.state.app_config_path), "ANTHROPIC_API_KEY", body.value.strip()
    )
    return {"ok": True}


@router.post("/credentials")
async def upload_credentials(request: Request, file: UploadFile = File(...)) -> dict:
    """Save an uploaded Google ``credentials.json`` to the configured path."""
    dest = request.app.state.settings.get("credentials_file")
    if not dest:
        raise HTTPException(
            status_code=400, detail="GOOGLE_CREDENTIALS_FILE is not configured."
        )
    raw = await file.read()
    try:
        json.loads(raw)  # validate it is JSON before saving.
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Not a valid JSON credentials file."
        )
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(raw)
    return {"ok": True, "path": str(dest_path)}


def _run_google_auth(
    credentials_file, token_file, *, logger: logging.Logger | None = None
) -> None:
    from jobjob.loader.auth import get_google_credentials

    _logger = logger or logging.getLogger("jobjob.setup")
    _auth_state.update(running=True, error=None)
    try:
        get_google_credentials(
            credentials_file=Path(credentials_file) if credentials_file else None,
            token_file=Path(token_file) if token_file else None,
            force_reauth=True,
        )
    except Exception as exc:  # noqa: BLE001 — surface any failure to the wizard.
        _logger.error("Google OAuth failed: %s", exc)
        _auth_state["error"] = str(exc)
    finally:
        _auth_state["running"] = False


@router.post("/google-auth")
def start_google_auth(request: Request) -> dict:
    """Start the Google OAuth loopback flow in the background (poll /status)."""
    if _auth_state["running"]:
        return {"started": False, "detail": "Already running."}
    settings = request.app.state.settings
    creds = settings.get("credentials_file")
    if not creds or not Path(creds).is_file():
        raise HTTPException(
            status_code=400, detail="Upload credentials.json before connecting Google."
        )
    threading.Thread(
        target=_run_google_auth,
        args=(creds, settings.get("token_file")),
        daemon=True,
    ).start()
    return {"started": True}


class DismissUpdate(BaseModel):
    dismissed: bool = True


@router.post("/dismiss")
def dismiss(body: DismissUpdate, request: Request) -> dict:
    """Persist (or clear) the 'don't show again' flag."""
    marker = Path(request.app.state.app_config_path).parent / _DISMISS_MARKER
    if body.dismissed:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("", encoding="utf-8")
    elif marker.is_file():
        marker.unlink()
    return {"dismissed": body.dismissed}
