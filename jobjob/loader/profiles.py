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
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Profile:
    """A registered (or bundled) profile with its state resolved once at load time.

    Attributes:
        name: Lowercased profile name (its registry suffix).
        path: The profile directory.
        read_only: True if this is the bundled example (lives in the read-only
            package ``static/example`` and may only be duplicated).
        owned: True if jobjob created and manages this dir (a direct child of the
            home ``profiles/`` base) and so may delete its files. False for the
            bundled example and for externally-registered, in-place dirs.
    """

    name: str
    path: Path
    read_only: bool
    owned: bool


def _same_dir(a: Path, b: Path) -> bool:
    """Return True if two paths resolve to the same location (False on OSError)."""
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def build_profiles(profiles_base: Optional[Path] = None) -> dict[str, "Profile"]:
    """Resolve every profile (registry + bundled example) into ``Profile`` objects.

    ``read_only`` and ``owned`` are computed once here so callers carry the flags
    instead of recomputing predicates. ``profiles_base`` is the home ``profiles/``
    dir (used to decide ``owned``); when None, no profile is considered owned.

    Arguments:
        profiles_base: The ``<home>/profiles`` dir, or None if unknown.
    Returns:
        ``{name: Profile}`` for the bundled example plus all registered profiles.
    """
    example = bundled_example_dir()
    base = profiles_base.resolve() if profiles_base is not None else None
    result: dict[str, Profile] = {}
    for name, path in all_profiles().items():
        path = Path(path)
        read_only = example is not None and _same_dir(path, example)
        owned = bool(
            not read_only and base is not None and _same_dir(path.parent, base)
        )
        result[name] = Profile(name=name, path=path, read_only=read_only, owned=owned)
    return result


def list_profiles() -> dict[str, Path]:
    """Return the registered profiles as ``{name: repo_path}`` (names lowercased).

    Reads ``JOBJOB_PROFILE_<NAME>=<path>`` entries from the environment. The
    active-profile pointer (``JOBJOB_ACTIVE_PROFILE``) is not a registry entry.
    """
    profiles: dict[str, Path] = {}
    for key, value in os.environ.items():
        if key.startswith(PROFILE_REGISTRY_PREFIX) and value.strip():
            name = key[len(PROFILE_REGISTRY_PREFIX) :].lower()
            profiles[name] = Path(value.strip().strip("\"'")).expanduser()
    return profiles


def bundled_example_dir() -> Optional[Path]:
    """Return the bundled example profile dir (``static/example``), or None.

    Computed directly from this file's location (``<root>/jobjob/loader/profiles.py``
    → ``<root>/static/example``) so this module stays import-light (no dependency on
    ``loader.location``). The example lives in its own subdir — isolated from any
    other ``static/`` assets — and doubles as the no-active-profile fallback.
    Returns None when the dir is absent (e.g. a stripped install), so callers can
    simply skip the example.
    """
    candidate = Path(__file__).resolve().parents[2] / "static" / "example"
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
