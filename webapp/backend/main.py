#!/usr/bin/env python3
"""jobjob webapp backend.

Binds to 127.0.0.1 only. CSRF double-submit cookie protects state-changing
endpoints. Secrets are never returned by any API response.

Run (development):
    cd webapp/backend
    uvicorn main:app --host 127.0.0.1 --port 8000 --reload

Run (production build — serves the Vite dist from /):
    uvicorn main:app --host 127.0.0.1 --port 8000
"""

import logging
import os
import secrets
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# Add the backend dir to sys.path so ``from routers import ...`` works when
# uvicorn is launched from the webapp/backend directory.
sys.path.insert(0, str(Path(__file__).parent))

from routers import (
    config,
    jobs,
    profiles,
    resume_import,
    setup,
    static_content,
    tracking,
    update,
)
from security import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SAFE_METHODS, configure_sandbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Paths ──────────────────────────────────────────────────────────────────────
# In a dev checkout the writable roots (config/, data/) sit beside the package at the
# repo root. When installed and launched as an app, ``JOBJOB_HOME`` points at the
# user's writable working dir (scaffolded by the launcher); config and data live there
# while the bundled, read-only ``static`` defaults and frontend ``dist`` stay inside the
# package. Unset ``JOBJOB_HOME`` ⇒ unchanged behavior (tests, dev, docs).
_BACKEND_DIR = Path(__file__).parent.resolve()
_PACKAGE_ROOT = (_BACKEND_DIR / "../..").resolve()
_HOME = (
    Path(os.environ["JOBJOB_HOME"]).expanduser().resolve()
    if os.environ.get("JOBJOB_HOME")
    else _PACKAGE_ROOT
)
_REPO_ROOT = _HOME
_APP_CONFIG = _HOME / "config" / ".env"
_DATA_DIR = _HOME / "data"
_STATIC_DIR = _PACKAGE_ROOT / "static"
_FRONTEND_DIST = _BACKEND_DIR / "../frontend/dist"

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="jobjob",
    description="Job application automation — local dashboard.",
    docs_url="/api/docs",
    redoc_url=None,
)

# ── CORS: only the local Vite dev server ───────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", CSRF_HEADER_NAME],
    expose_headers=[CSRF_HEADER_NAME],
)


# ── CSRF double-submit cookie middleware ───────────────────────────────────────
class _CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in SAFE_METHODS:
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            header_token = request.headers.get(CSRF_HEADER_NAME)
            if not cookie_token or cookie_token != header_token:
                return JSONResponse(
                    {"detail": "CSRF token mismatch"}, status_code=403
                )
        response = await call_next(request)
        if CSRF_COOKIE_NAME not in request.cookies:
            response.set_cookie(
                CSRF_COOKIE_NAME,
                secrets.token_hex(32),
                httponly=False,  # JS must read it for double-submit
                samesite="strict",
                secure=False,  # local HTTP only
            )
        return response


app.add_middleware(_CSRFMiddleware)

# ── Settings/state assembly (re-runnable for profile switching) ────────────────
def reload_state() -> None:
    """Load app + active-profile config and (re)populate ``app.state``.

    Re-runnable: the profile-switch endpoint calls this after changing the active
    profile so content, applicant identity, template, and the sandbox refresh
    without a server restart.
    """
    from jobjob.config import load_settings
    from jobjob.loader.profiles import all_profiles, is_read_only, profile_config_file

    settings = load_settings(_APP_CONFIG)
    roots = [_STATIC_DIR, _DATA_DIR, _REPO_ROOT / "config"]
    if settings.google.credentials_file:
        roots.append(Path(settings.google.credentials_file).parent)
    # Synced Drive applications mirror — read-only source for re-running a
    # completed application's JD when it isn't in data/completed/jobs/.
    if settings.google.applications_local_dir:
        roots.append(Path(settings.google.applications_local_dir))
    # Active profile repo — content/reference reads and (via the editor) writes.
    if settings.profile_dir:
        roots.append(Path(settings.profile_dir))
    configure_sandbox(roots)

    app.state.app_config_path = _APP_CONFIG
    app.state.repo_root = _REPO_ROOT
    app.state.profile_name = settings.profile_name
    app.state.profile_dir = settings.profile_dir
    app.state.profile_config_path = (
        profile_config_file(settings.profile_dir) if settings.profile_dir else None
    )
    # The switcher/registry includes the bundled read-only ``example`` profile.
    app.state.profiles = all_profiles()
    app.state.profile_read_only = is_read_only(
        settings.profile_name or "",
        Path(settings.profile_dir) if settings.profile_dir else None,
    )
    app.state.reload_state = reload_state
    data_dir = (
        settings.data_dir
        if settings.data_dir.is_absolute()
        else (_REPO_ROOT / settings.data_dir)
    )
    app.state.settings = {
        "data_dir": data_dir,
        "applications_folder_id": settings.google.applications_folder_id,
        "applications_local_dir": settings.google.applications_local_dir,
        "credentials_file": settings.google.credentials_file,
        "token_file": settings.google.token_file,
        "linkedin_sheet_id": settings.linkedin_sheet_id,
        "profile_name": settings.profile_name,
        "per_run_budget": 2.0,
        "daily_budget": 20.0,
    }


def _background_update_check() -> None:
    """Refresh the PyPI update cache in a daemon thread so app open doesn't block."""
    import threading

    def _run() -> None:
        try:
            from services import update_service

            update_service.check_for_updates()
        except Exception:  # never let a background check disturb startup
            logging.getLogger("jobjob.update").debug(
                "background update check failed", exc_info=True
            )

    threading.Thread(target=_run, name="jobjob-update-check", daemon=True).start()


# ── Startup: configure sandbox and attach settings to app.state ────────────────
@app.on_event("startup")
def _startup() -> None:
    reload_state()
    _background_update_check()


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(tracking.router, prefix="/api/tracking", tags=["tracking"])
app.include_router(static_content.router, prefix="/api/static", tags=["static"])
app.include_router(
    resume_import.router, prefix="/api/resume-import", tags=["resume-import"]
)
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(setup.router, prefix="/api/setup", tags=["setup"])
app.include_router(update.router, prefix="/api/update", tags=["update"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ── Serve built frontend (production mode) ─────────────────────────────────────
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
