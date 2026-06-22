#!/usr/bin/env python3
"""Config API: read/update the app config (``config/.env``) or the active
profile config (``<profile>/config/.profile``), scoped so neither can write the
other's keys."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from jobjob.config import APP_KEYS, PROFILE_KEYS
from services.config_service import read_config, write_config

router = APIRouter()

# Editable app keys exclude the JOBJOB_* profile registry (managed via /profiles).
_SCOPES = {"app": APP_KEYS, "profile": PROFILE_KEYS}


def _target(request: Request, scope: str) -> tuple[Path, frozenset[str]]:
    """Return (config path, allowed key set) for ``scope``; 4xx on bad input."""
    if scope not in _SCOPES:
        raise HTTPException(status_code=400, detail=f"Unknown config scope: {scope}")
    if scope == "profile":
        path: Optional[Path] = request.app.state.profile_config_path
        if path is None:
            raise HTTPException(
                status_code=400, detail="No active profile; profile config unavailable."
            )
        return path, PROFILE_KEYS
    return request.app.state.app_config_path, APP_KEYS


class ConfigUpdate(BaseModel):
    updates: dict[str, str]


@router.get("")
def get_config(request: Request, scope: str = Query("app")) -> dict:
    """Return the scoped config keys (secrets absent; is_set reflects presence)."""
    path, keys = _target(request, scope)
    return read_config(path, keys=keys)


@router.put("")
def update_config(
    body: ConfigUpdate, request: Request, scope: str = Query("app")
) -> dict:
    """Write non-secret, in-scope key updates to the scoped config file.

    Raises:
        400: If any key is secret or outside the scope.
    """
    path, keys = _target(request, scope)
    try:
        write_config(path, body.updates, allowed_keys=keys)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return read_config(path, keys=keys)
