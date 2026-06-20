#!/usr/bin/env python3
"""Self-update support: check PyPI for a newer jobjob release and upgrade in place.

The status view is cheap (reads a small cache, no network) so the Settings page loads
instantly; the check is what hits PyPI. A background check runs on app startup so the
cached "latest version" is usually fresh by the time the user opens Settings.

The cached payload lives at ``~/.cache/jobjob/update.json`` (mirrors ``budget.py``).
"""

import json
import logging
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from jobjob.__about__ import __version__ as CURRENT_VERSION

logger = logging.getLogger("jobjob.update")

PACKAGE_NAME = "jobjob"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
_CACHE_FILE = Path.home() / ".cache" / "jobjob" / "update.json"
_HTTP_TIMEOUT = 10
_UPGRADE_TIMEOUT = 600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Install-method detection ────────────────────────────────────────────────────

def detect_install_method() -> str:
    """Return how jobjob is installed: ``pipx``, ``pip``, or ``source``.

    ``source`` means an editable/dev checkout (not upgradable via the installer).
    """
    try:
        import jobjob

        location = str(Path(jobjob.__file__).resolve()).lower()
    except Exception:  # pragma: no cover - jobjob is always importable here
        return "source"
    if "pipx" in location and "venvs" in location:
        return "pipx"
    if "site-packages" in location or "dist-packages" in location:
        return "pip"
    return "source"


# ── Version comparison ──────────────────────────────────────────────────────────

def _naive_gt(a: str, b: str) -> bool:
    """Compare dotted numeric versions without the ``packaging`` dependency."""

    def parts(v: str) -> list[int]:
        out = []
        for piece in v.split("."):
            digits = "".join(ch for ch in piece if ch.isdigit())
            out.append(int(digits) if digits else 0)
        return out

    return parts(a) > parts(b)


def is_newer(latest: str, current: str) -> bool:
    """Return True if ``latest`` is a newer version than ``current``."""
    try:
        from packaging.version import Version

        return Version(latest) > Version(current)
    except Exception:
        return _naive_gt(latest, current)


# ── PyPI fetch + cache ──────────────────────────────────────────────────────────

def _fetch_pypi(_opener=urllib.request.urlopen) -> dict:
    """Return the parsed PyPI JSON metadata for the package (raises on failure)."""
    request = urllib.request.Request(
        PYPI_JSON_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": f"{PACKAGE_NAME}/{CURRENT_VERSION}",
        },
    )
    with _opener(request, timeout=_HTTP_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _release_date(data: dict, version: str) -> "str | None":
    """Return the earliest upload time for ``version`` from PyPI metadata, or None."""
    files = data.get("releases", {}).get(version) or []
    times = [f.get("upload_time_iso_8601") for f in files if f.get("upload_time_iso_8601")]
    return min(times) if times else None


def _load_cache() -> dict:
    if not _CACHE_FILE.is_file():
        return {}
    try:
        return json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _save_cache(data: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:  # cache is best-effort; never break the request
        logger.warning("Could not write update cache: %s", exc)


def check_for_updates(_opener=urllib.request.urlopen) -> dict:
    """Query PyPI, refresh the cache, and return it.

    Network/parse failures are caught and recorded as ``check_error`` while preserving
    any previously-known latest version — this is the resilience boundary, so it logs
    and continues rather than raising.
    """
    cache = _load_cache()
    cache["last_checked"] = _now_iso()
    try:
        data = _fetch_pypi(_opener)
        latest = (data.get("info") or {}).get("version")
        cache["latest_version"] = latest
        cache["latest_release_date"] = _release_date(data, latest) if latest else None
        cache["current_release_date"] = _release_date(data, CURRENT_VERSION)
        cache["check_error"] = None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        cache["check_error"] = str(exc)
        logger.warning("Update check failed: %s", exc)
    _save_cache(cache)
    return cache


# ── Public status + upgrade ─────────────────────────────────────────────────────

def get_status() -> dict:
    """Return the current update status from the cache (no network)."""
    cache = _load_cache()
    latest = cache.get("latest_version")
    method = detect_install_method()
    update_available = bool(latest and is_newer(latest, CURRENT_VERSION))
    return {
        "current_version": CURRENT_VERSION,
        "current_release_date": cache.get("current_release_date"),
        "latest_version": latest,
        "latest_release_date": cache.get("latest_release_date"),
        "last_checked": cache.get("last_checked"),
        "check_error": cache.get("check_error"),
        "install_method": method,
        "update_available": update_available,
        "can_update": update_available and method in ("pipx", "pip"),
    }


def apply_update(_runner=subprocess.run) -> dict:
    """Upgrade the installed package to the latest PyPI release.

    Picks the command for the detected install method. A source checkout is not
    upgradable this way; returns a clear message instead.
    """
    method = detect_install_method()
    if method == "pipx":
        cmd = ["pipx", "upgrade", PACKAGE_NAME]
    elif method == "pip":
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_NAME]
    else:
        return {
            "ok": False,
            "method": method,
            "message": (
                "Running from a source checkout — update with git, not the installer."
            ),
        }

    try:
        proc = _runner(cmd, capture_output=True, text=True, timeout=_UPGRADE_TIMEOUT)
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "method": method, "message": f"Upgrade failed to start: {exc}"}

    ok = proc.returncode == 0
    return {
        "ok": ok,
        "method": method,
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
        "message": (
            "Update complete — restart jobjob to use the new version."
            if ok
            else "The upgrade command failed; see the output below."
        ),
    }


# __END__
