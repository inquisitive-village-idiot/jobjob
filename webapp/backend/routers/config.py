#!/usr/bin/env python3
"""Config API: read/update the app config (``config/.env``) or the active
profile config (``<profile>/config/.profile``), scoped so neither can write the
other's keys."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from jobjob.config import APP_KEYS, PROFILE_KEYS
from jobjob.loader.profiles import Profile, profile_config_file
from services.config_service import read_config, write_config

router = APIRouter()

# Editable app keys exclude the JOBJOB_* profile registry (managed via /profiles).
_SCOPES = {"app": APP_KEYS, "profile": PROFILE_KEYS}


def _resolve_profile(request: Request, name: Optional[str]) -> Profile:
    """Resolve a registered profile by name (or the active one when ``name`` is None).

    Raises:
        400: If no profile is active (and none named) or the name is unregistered.
    """
    profiles: dict[str, Profile] = request.app.state.profiles or {}
    resolved = name if (name and name.strip()) else request.app.state.profile_name
    if not resolved:
        raise HTTPException(
            status_code=400, detail="No active profile; profile config unavailable."
        )
    profile = profiles.get(resolved.strip().lower())
    if profile is None:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {resolved}")
    return profile


def _target(
    request: Request, scope: str, name: Optional[str] = None
) -> tuple[Path, frozenset[str], bool]:
    """Return (config path, allowed key set, read_only) for ``scope``; 4xx on bad input.

    For the profile scope, ``name`` selects a specific registered profile; when None
    the active profile is used. ``read_only`` is True for the bundled example profile.
    """
    if scope not in _SCOPES:
        raise HTTPException(status_code=400, detail=f"Unknown config scope: {scope}")
    if scope == "profile":
        profile = _resolve_profile(request, name)
        return profile_config_file(profile.path), PROFILE_KEYS, profile.read_only
    return request.app.state.app_config_path, APP_KEYS, False


class ConfigUpdate(BaseModel):
    updates: dict[str, str]


@router.get("")
def get_config(
    request: Request,
    scope: str = Query("app"),
    name: Optional[str] = Query(None),
) -> dict:
    """Return the scoped config keys (secrets absent; is_set reflects presence).

    For ``scope=profile``, ``name`` selects a registered profile (default: active).
    """
    path, keys, _ = _target(request, scope, name)
    return read_config(path, keys=keys)


@router.put("")
def update_config(
    body: ConfigUpdate,
    request: Request,
    scope: str = Query("app"),
    name: Optional[str] = Query(None),
) -> dict:
    """Write non-secret, in-scope key updates to the scoped config file.

    For ``scope=profile``, ``name`` selects a registered profile (default: active).

    Raises:
        400: If any key is secret or outside the scope.
        403: If the target profile is read-only (the bundled example).
    """
    path, keys, read_only = _target(request, scope, name)
    if read_only:
        raise HTTPException(
            status_code=403,
            detail="This profile is read-only; duplicate it to make an editable copy.",
        )
    try:
        write_config(path, body.updates, allowed_keys=keys)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return read_config(path, keys=keys)
