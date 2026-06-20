#!/usr/bin/env python3
"""Profile registry resolution.

A *profile* is a separate git repo holding one content set (highlights,
reference docs, and a committed ``config/.profile``). The app config registers
profiles by path and names the active one::

    JOBJOB_PROFILE_LOCAL="/path/to/your/profile"
    JOBJOB_ACTIVE_PROFILE="local"

This module is intentionally dependency-light (os + pathlib) so both
``jobjob.config`` and ``jobjob.loader.location`` can import it without a cycle.
It reads ``os.environ`` (populated by ``load_dotenv`` of the app config), so the
active-profile lookup reflects whatever the app config most recently sourced.
"""

import os
from pathlib import Path
from typing import Optional

ENV_ACTIVE_PROFILE = "JOBJOB_ACTIVE_PROFILE"
PROFILE_REGISTRY_PREFIX = "JOBJOB_PROFILE_"
# A profile repo keeps its committed config under ``config/.profile``.
PROFILE_CONFIG_SUBDIR = "config"
PROFILE_CONFIG_NAME = ".profile"

# The bundled, read-only example profile (the Tila Mer demo persona). Its location is
# the package ``static/`` dir, so it is always present and never user-editable (it lives
# in site-packages under an installed wheel). It is offered alongside the registered
# profiles as a reference the user can *duplicate* into a profile they own.
EXAMPLE_PROFILE_NAME = "example"


def list_profiles() -> dict[str, Path]:
    """Return the registered profiles as ``{name: repo_path}`` (names lowercased).

    Reads ``JOBJOB_PROFILE_<NAME>=<path>`` entries from the environment. The
    active-profile pointer (``JOBJOB_ACTIVE_PROFILE``) is not a registry entry.
    """
    profiles: dict[str, Path] = {}
    for key, value in os.environ.items():
        if key.startswith(PROFILE_REGISTRY_PREFIX) and value.strip():
            name = key[len(PROFILE_REGISTRY_PREFIX):].lower()
            profiles[name] = Path(value.strip().strip("\"'")).expanduser()
    return profiles


def bundled_example_dir() -> Optional[Path]:
    """Return the bundled example profile dir (package ``static/``), or None.

    Computed directly from this file's location (``<root>/jobjob/loader/profiles.py``
    → ``<root>/static``) so this module stays import-light (no dependency on
    ``loader.location``). Returns None when ``static/`` is absent (e.g. a stripped
    install), so callers can simply skip the example.
    """
    candidate = Path(__file__).resolve().parents[2] / "static"
    return candidate if candidate.is_dir() else None


def all_profiles() -> dict[str, Path]:
    """Return the registered profiles plus the bundled ``example`` profile.

    The registry (``list_profiles``) is the user-managed source of truth; the
    read-only ``example`` is injected here so it is always switchable for reference
    without polluting the user's config. An explicit ``JOBJOB_PROFILE_EXAMPLE``
    registry entry overrides the bundled location.
    """
    profiles: dict[str, Path] = {}
    example = bundled_example_dir()
    if example is not None:
        profiles[EXAMPLE_PROFILE_NAME] = example
    profiles.update(list_profiles())
    return profiles


def is_read_only(name: str, profile_dir: Optional[Path] = None) -> bool:
    """Return True if the named profile (or dir) is the read-only bundled example.

    Read-only is keyed on *location*, not name: any profile whose dir is the bundled
    ``static/`` cannot be edited (it lives in the read-only package install), even if
    a user registered it under a different name.
    """
    example = bundled_example_dir()
    if example is None:
        return False
    if profile_dir is not None:
        try:
            return profile_dir.resolve() == example.resolve()
        except OSError:
            return False
    if name.lower() == EXAMPLE_PROFILE_NAME:
        return True
    target = list_profiles().get(name.lower())
    return target is not None and target.resolve() == example.resolve()


def active_profile_name() -> Optional[str]:
    """Return the active profile name (lowercased), or None if unset."""
    name = os.environ.get(ENV_ACTIVE_PROFILE)
    return name.strip().strip("\"'").lower() if name and name.strip() else None


def resolve_active_profile_dir() -> Optional[Path]:
    """Return the active profile's repo path, or None when none is configured.

    Returns the registered path even if it does not yet exist on disk — callers
    decide whether a missing dir is an error (config load) or a fallback signal
    (content resolution).
    """
    name = active_profile_name()
    if not name:
        return None
    return all_profiles().get(name)


def profile_config_file(profile_dir: Path) -> Path:
    """Return the path to a profile repo's committed config (``config/.profile``)."""
    return profile_dir / PROFILE_CONFIG_SUBDIR / PROFILE_CONFIG_NAME


def read_env_keys(path: Path) -> set[str]:
    """Return the set of ``KEY`` names assigned in a dotenv-format file.

    Blank lines, comments, and lines without ``=`` are ignored. Used to validate
    that app and profile configs hold disjoint key sets.
    """
    keys: set[str] = set()
    if not path.is_file():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        keys.add(stripped.partition("=")[0].strip())
    return keys


# __END__
