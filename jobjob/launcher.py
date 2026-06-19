#!/usr/bin/env python3
"""``jobjob-app`` — scaffold a working dir, launch the local webapp, open the browser.

The installed-app entry point. On first run it creates a visible working directory
(``~/Documents/jobjob`` by default) holding the user's writable ``config/`` and
``data/`` plus a **local profile** (``content/``, ``reference/``, ``config/.profile``)
seeded from the bundled ``static/`` defaults — so content lives on the user's machine
with no git repo. It then sets ``JOBJOB_HOME`` (honored by the webapp backend), starts
uvicorn bound to localhost, and opens the browser, where the setup wizard guides
credentials. Re-running is idempotent (existing files are left as-is).
"""

import argparse
import os
import shutil
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Iterable, Optional

import platformdirs

APP_NAME = "jobjob"
DEFAULT_HOME = Path.home() / "Documents" / APP_NAME
LOCAL_PROFILE_NAME = "local"

_PROFILE_TEMPLATE = """\
# jobjob local profile — applicant identity + resume template.
# Fill these in via the setup wizard (or edit by hand). No secrets or local paths here.
# APPLICANT_NAME=
# APPLICANT_EMAIL=
# APPLICANT_PHONE=
# APPLICANT_LINKEDIN=
# RESUME_TEMPLATE_ID=
"""


def _package_root() -> Path:
    """Return the dir that holds the ``jobjob`` package plus bundled ``webapp``/``static``.

    In a dev checkout this is the repo root; in an installed wheel it is the directory
    the package data was unpacked into (``site-packages``).
    """
    return Path(__file__).resolve().parent.parent


def _env_text(home: Path) -> str:
    """Return the scaffolded ``config/.env`` body with OS-correct, absolute paths."""
    cache_dir = platformdirs.user_cache_dir(APP_NAME)
    config_dir = Path(platformdirs.user_config_dir(APP_NAME))
    profile_key = f"JOBJOB_PROFILE_{LOCAL_PROFILE_NAME.upper()}"
    lines = [
        "# jobjob app config — machine-local. The setup wizard fills the rest.",
        f"DATA_DIR={home / 'data'}",
        f"CACHE_DIR={cache_dir}",
        f"GOOGLE_CREDENTIALS_FILE={config_dir / 'credentials.json'}",
        f"GOOGLE_TOKEN_FILE={config_dir / 'token.pickle'}",
        f"{profile_key}={home / 'profile'}",
        f"JOBJOB_ACTIVE_PROFILE={LOCAL_PROFILE_NAME}",
        "",
    ]
    return "\n".join(lines)


def scaffold(home: Path) -> Path:
    """Create (idempotently) the working dir, app config, and local profile.

    Arguments:
        home: The working directory to populate.
    Returns:
        The working directory path.
    """
    home.mkdir(parents=True, exist_ok=True)
    (home / "config").mkdir(exist_ok=True)
    (home / "data").mkdir(exist_ok=True)

    env_path = home / "config" / ".env"
    if not env_path.exists():
        env_path.write_text(_env_text(home))

    profile = home / "profile"
    if not profile.exists():
        profile.mkdir(parents=True)
        bundled_static = _package_root() / "static"
        for sub in ("content", "reference"):
            src = bundled_static / sub
            if src.is_dir():
                shutil.copytree(src, profile / sub)
        (profile / "config").mkdir(exist_ok=True)
        (profile / "config" / ".profile").write_text(_PROFILE_TEMPLATE)
    return home


def _serve(home: Path, host: str, port: int, open_browser: bool) -> None:
    """Start uvicorn for the bundled backend, rooted at ``home``."""
    os.environ["JOBJOB_HOME"] = str(home)
    backend = _package_root() / "webapp" / "backend"
    sys.path.insert(0, str(backend))

    import uvicorn

    import main  # noqa: E402 — import after sys.path + JOBJOB_HOME are set.

    if open_browser:
        url = f"http://{host}:{port}"
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(main.app, host=host, port=port, log_level="info")


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Scaffold the working dir and launch the local app.

    Arguments:
        argv: Argument vector (defaults to ``sys.argv[1:]``).
    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        prog="jobjob-app", description="Launch the jobjob local dashboard."
    )
    parser.add_argument(
        "--dir",
        default=os.environ.get("JOBJOB_HOME") or str(DEFAULT_HOME),
        help="Working directory (default: ~/Documents/jobjob).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--no-browser", action="store_true", help="Do not open a browser window."
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Scaffold the working dir and exit (no server).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    home = scaffold(Path(args.dir).expanduser().resolve())
    print(f"jobjob working directory: {home}")
    if args.setup_only:
        return 0
    _serve(home, args.host, args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# __END__
