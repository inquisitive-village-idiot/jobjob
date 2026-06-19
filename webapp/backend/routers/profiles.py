#!/usr/bin/env python3
"""Profiles API: list registered profiles and switch the active one.

Switching rewrites ``JOBJOB_ACTIVE_PROFILE`` in the app config and reloads
``app.state`` (content, applicant identity, template, sandbox) without a restart.
"""

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jobjob.loader.profiles import ENV_ACTIVE_PROFILE
from services.config_service import write_config

router = APIRouter()


def _profiles_payload(request: Request) -> dict:
    profiles = request.app.state.profiles or {}
    return {
        "active": request.app.state.profile_name,
        "profiles": sorted(profiles.keys()),
    }


@router.get("")
def list_profiles(request: Request) -> dict:
    """Return the registered profile names and the active one."""
    return _profiles_payload(request)


class ProfileSwitch(BaseModel):
    name: str


@router.put("/active")
def set_active_profile(body: ProfileSwitch, request: Request) -> dict:
    """Switch the active profile and reload app state.

    Raises:
        400: If the name is not a registered profile.
    """
    name = body.name.strip().lower()
    profiles = request.app.state.profiles or {}
    if name not in profiles:
        raise HTTPException(
            status_code=400, detail=f"Unknown profile: {body.name}"
        )
    # Persist to the app config, then update the live env (load_dotenv will not
    # override an already-set var) before reloading.
    write_config(
        request.app.state.app_config_path,
        {ENV_ACTIVE_PROFILE: name},
        allowed_keys=frozenset({ENV_ACTIVE_PROFILE}),
    )
    os.environ[ENV_ACTIVE_PROFILE] = name
    request.app.state.reload_state()
    return _profiles_payload(request)
