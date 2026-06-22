#!/usr/bin/env python3
"""``jobjob-app`` — scaffold a working dir, launch the local webapp, open the browser.

The installed-app entry point. On first run it creates a visible working directory
(``~/Documents/jobjob`` by default) holding the user's writable ``config/`` and
``data/`` plus a **blank local profile** (``profiles/local/`` — empty-but-valid
``content/``, ``reference/``, ``config/.profile``) so the user starts clean, with no
Tila Mer example content mixed in. The bundled read-only ``example`` profile is always
available to switch to or duplicate. It then sets ``JOBJOB_HOME`` (honored by the webapp
backend), starts uvicorn bound to localhost, and opens the browser, where the setup
wizard guides credentials. Re-running is idempotent (existing files are left as-is); a
legacy ``profile/`` layout is migrated to ``profiles/local/`` in place.
"""

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Iterable, Optional

import platformdirs

APP_NAME = "jobjob"
DEFAULT_HOME = Path.home() / "Documents" / APP_NAME
LOCAL_PROFILE_NAME = "local"
PROFILES_SUBDIR = "profiles"


def _package_root() -> Path:
    """Return the dir holding ``jobjob`` plus the bundled ``webapp``/``static``.

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
        f"{profile_key}={_local_profile_dir(home)}",
        f"JOBJOB_ACTIVE_PROFILE={LOCAL_PROFILE_NAME}",
        "",
    ]
    return "\n".join(lines)


def _local_profile_dir(home: Path) -> Path:
    """Return the user's local profile dir (``<home>/profiles/local``)."""
    return home / PROFILES_SUBDIR / LOCAL_PROFILE_NAME


def _migrate_legacy_profile(home: Path) -> None:
    """Move a pre-unification ``<home>/profile`` to ``<home>/profiles/local`` in place.

    Older installs scaffolded a single ``profile/`` dir (seeded from the Tila Mer
    example). Unifying on ``profiles/<name>/`` keeps the layout consistent. The move
    preserves whatever the user has edited; the ``.env`` registry path is rewritten to
    match. Idempotent and a no-op when there's nothing to migrate.
    """
    legacy = home / "profile"
    target = _local_profile_dir(home)
    if not legacy.is_dir() or target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    legacy.rename(target)

    env_path = home / "config" / ".env"
    if env_path.is_file():
        key = f"JOBJOB_PROFILE_{LOCAL_PROFILE_NAME.upper()}"
        new_lines = []
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{key}=") and not stripped.startswith("#"):
                new_lines.append(f"{key}={target}")
            else:
                new_lines.append(line)
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


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

    # Migrate any legacy single-``profile/`` layout before writing/reading the registry
    # path, so a fresh ``.env`` and an existing install converge on ``profiles/local``.
    _migrate_legacy_profile(home)

    env_path = home / "config" / ".env"
    if not env_path.exists():
        # Always UTF-8: the file is read back by python-dotenv as UTF-8, and the
        # default Windows codepage (cp1252) would mangle non-ASCII (e.g. the em dash).
        env_path.write_text(_env_text(home), encoding="utf-8")

    # The local profile starts BLANK (skeleton), not seeded from the Tila Mer example —
    # the bundled read-only ``example`` profile is there to switch to or
    # duplicate. Users pre-fill the blank profile via the Static Content page or
    # by importing a résumé.
    from jobjob.loader.skeleton import create_blank_profile

    local = _local_profile_dir(home)
    if not local.exists():
        create_blank_profile(local)
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
