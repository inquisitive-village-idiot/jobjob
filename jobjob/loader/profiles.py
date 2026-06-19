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
    return list_profiles().get(name)


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
