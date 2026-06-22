#!/usr/bin/env python3
"""Profile lifecycle: create (blank), duplicate, register, and delete profiles.

A profile is a self-contained dir (``content/`` + ``reference/`` + ``config/.profile``)
registered in the app config as ``JOBJOB_PROFILE_<NAME>=<location>``. User-owned
profiles live under ``<JOBJOB_HOME>/profiles/<name>/``; an *external* profile is an
existing dir the user points at (registered, never copied or deleted). The bundled
``example`` (Tila Mer) is read-only and may only be duplicated, never edited or deleted.

These functions are FastAPI-agnostic (they take explicit paths and the registry map) so
they can be unit-tested without a running app; the router wires them to ``app.state``.
"""

import re
import shutil
import tomllib
from pathlib import Path
from typing import Optional

from jobjob.loader.profiles import (
    EXAMPLE_PROFILE_NAME,
    PROFILE_REGISTRY_PREFIX,
    Profile,
)
from services.config_service import remove_config_key, write_config

# Profile names map to ``JOBJOB_PROFILE_<NAME>`` env keys, so they must be valid env-var
# suffixes: start with a letter, then letters/digits/underscores (no hyphens or spaces).
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_RESERVED = {EXAMPLE_PROFILE_NAME, "active"}

# A content file is valid if it parses and carries its ``[tool.<name>]`` table.
_CONTENT_TABLES = {
    "highlights.toml": "highlights",
    "skills.toml": "skills",
    "templates.toml": "templates",
}


class ProfileError(ValueError):
    """A profile operation failed for a user-correctable reason (→ HTTP 400)."""


def normalize_name(raw: str) -> str:
    """Lowercase and validate a profile name; raise ProfileError if malformed."""
    name = (raw or "").strip().lower()
    if not name:
        raise ProfileError("Profile name is required.")
    if name in _RESERVED:
        raise ProfileError(f"'{name}' is reserved.")
    if not _NAME_RE.match(name):
        raise ProfileError(
            "Use lowercase letters, digits, and underscores; start with a letter "
            "(e.g. 'my_profile')."
        )
    return name


def registry_key(name: str) -> str:
    """Return the app-config registry key for a profile name."""
    return f"{PROFILE_REGISTRY_PREFIX}{name.upper()}"


def profiles_base(app_config_path: Path) -> Path:
    """Return ``<JOBJOB_HOME>/profiles`` derived from the app config location.

    The app config lives at ``<home>/config/.env``, so home is two parents up.
    """
    return app_config_path.parent.parent / "profiles"


def validate_profile_dir(path: Path) -> None:
    """Raise ProfileError unless ``path`` is a structurally valid profile dir.

    Requires ``config/.profile`` plus parseable ``content/{highlights,skills,
    templates}.toml`` carrying their ``[tool.*]`` tables — the same shape the loaders
    expect. Guards against registering a path that would silently fall back to the
    bundled demo content (the ``_resolve_dir`` footgun).
    """
    if not path.is_dir():
        raise ProfileError(f"Not a directory: {path}")
    if not (path / "config" / ".profile").is_file():
        raise ProfileError(f"Missing config/.profile in {path}")
    content = path / "content"
    for filename, table in _CONTENT_TABLES.items():
        f = content / filename
        if not f.is_file():
            raise ProfileError(f"Missing content/{filename} in {path}")
        try:
            data = tomllib.loads(f.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ProfileError(f"Invalid TOML in content/{filename}: {exc}")
        if "tool" not in data or table not in data["tool"]:
            raise ProfileError(f"content/{filename} missing [tool.{table}] table")


def _ensure_available(name: str, existing: dict[str, Path]) -> None:
    if name in {k.lower() for k in existing}:
        raise ProfileError(f"A profile named '{name}' already exists.")


def _register(app_config_path: Path, name: str, location: Path) -> None:
    key = registry_key(name)
    write_config(app_config_path, {key: str(location)}, allowed_keys=frozenset({key}))


def create_profile(
    app_config_path: Path, existing: dict[str, Path], raw_name: str
) -> Path:
    """Create a blank profile under ``<home>/profiles/<name>`` and register it."""
    from jobjob.loader.skeleton import create_blank_profile

    name = normalize_name(raw_name)
    _ensure_available(name, existing)
    dest = profiles_base(app_config_path) / name
    if dest.exists() and any(dest.iterdir()):
        raise ProfileError(f"Directory already exists and is not empty: {dest}")
    create_blank_profile(dest)
    _register(app_config_path, name, dest)
    return dest


def duplicate_profile(
    app_config_path: Path,
    available: dict[str, Path],
    source: str,
    raw_name: str,
) -> Path:
    """Copy an existing profile (e.g. ``example``) into a new owned profile."""
    src = source.strip().lower()
    src_dir = available.get(src)
    if src_dir is None:
        raise ProfileError(f"Unknown source profile: {source}")
    name = normalize_name(raw_name)
    _ensure_available(name, available)
    dest = profiles_base(app_config_path) / name
    if dest.exists():
        raise ProfileError(f"Directory already exists: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, dest)
    _register(app_config_path, name, dest)
    return dest


def register_profile(
    app_config_path: Path,
    existing: dict[str, Path],
    raw_name: str,
    location: str,
) -> Path:
    """Register an existing local profile dir (validated, never copied)."""
    name = normalize_name(raw_name)
    _ensure_available(name, existing)
    path = Path(location).expanduser().resolve()
    validate_profile_dir(path)
    _register(app_config_path, name, path)
    return path


def delete_profile(
    app_config_path: Path,
    profile: Profile,
    active_name: Optional[str],
) -> bool:
    """Unregister a profile; delete its files only if jobjob owns the copy.

    Refuses the read-only ``example`` and the currently active profile. External
    (registered-in-place) profiles are unregistered but their files are left on disk —
    jobjob never created them. ``read_only``/``owned`` are read from the resolved
    ``Profile`` (computed once at load) rather than recomputed here. Returns True if
    the on-disk dir was removed.

    Arguments:
        app_config_path: Path to the app ``config/.env`` holding the registry.
        profile: The resolved profile to delete.
        active_name: The currently active profile name, or None.
    """
    name = profile.name
    if profile.read_only:
        raise ProfileError("The example profile is read-only and cannot be deleted.")
    if active_name and name == active_name.strip().lower():
        raise ProfileError(
            "Cannot delete the active profile. Switch to another profile first."
        )
    remove_config_key(app_config_path, registry_key(name))
    # Only delete files we own (a jobjob-created dir under <home>/profiles/).
    if profile.owned and profile.path.is_dir():
        shutil.rmtree(profile.path)
        return True
    return False


# __END__
