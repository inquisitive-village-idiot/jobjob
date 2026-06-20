#!/usr/bin/env python3
"""Profiles API: list, switch, create, duplicate, register, and delete profiles.

A profile is a self-contained content+reference+config dir registered in the app
config. The bundled ``example`` (Tila Mer) is read-only; users create blank profiles,
duplicate the example, or register an existing local dir. Mutations rewrite the app
config's profile registry and reload ``app.state`` so content, applicant identity, and
the template refresh without a restart.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jobjob.loader.profiles import ENV_ACTIVE_PROFILE, is_read_only
from services import profile_service
from services.config_service import write_config

router = APIRouter()


def _entries(request: Request) -> list[dict]:
    """Return per-profile metadata (name, active, read_only, external)."""
    profiles: dict[str, Path] = request.app.state.profiles or {}
    active = request.app.state.profile_name
    try:
        base = profile_service.profiles_base(
            Path(request.app.state.app_config_path)
        ).resolve()
    except Exception:
        base = None
    out: list[dict] = []
    for name in sorted(profiles):
        path = Path(profiles[name])
        read_only = is_read_only(name, path)
        external = True
        if base is not None:
            try:
                external = not (path.resolve().parent == base)
            except OSError:
                external = True
        out.append(
            {
                "name": name,
                "active": name == active,
                "read_only": read_only,
                "external": external and not read_only,
            }
        )
    return out


def _profiles_payload(request: Request) -> dict:
    profiles = request.app.state.profiles or {}
    return {
        "active": request.app.state.profile_name,
        "profiles": sorted(profiles.keys()),
        "entries": _entries(request),
    }


@router.get("")
def list_profiles(request: Request) -> dict:
    """Return the registered profile names, the active one, and per-profile metadata."""
    return _profiles_payload(request)


class ProfileSwitch(BaseModel):
    name: str


class ProfileCreate(BaseModel):
    name: str


class ProfileDuplicate(BaseModel):
    source: str
    name: str


class ProfileRegister(BaseModel):
    name: str
    location: str


def _app_config(request: Request) -> Path:
    return Path(request.app.state.app_config_path)


def _reload(request: Request) -> None:
    request.app.state.reload_state()


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
        _app_config(request),
        {ENV_ACTIVE_PROFILE: name},
        allowed_keys=frozenset({ENV_ACTIVE_PROFILE}),
    )
    os.environ[ENV_ACTIVE_PROFILE] = name
    _reload(request)
    return _profiles_payload(request)


@router.post("")
def create_profile(body: ProfileCreate, request: Request) -> dict:
    """Create a new blank profile from the skeleton and register it."""
    try:
        dest = profile_service.create_profile(
            _app_config(request), request.app.state.profiles or {}, body.name
        )
    except profile_service.ProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    os.environ[profile_service.registry_key(body.name.strip().lower())] = str(dest)
    _reload(request)
    return _profiles_payload(request)


@router.post("/duplicate")
def duplicate_profile(body: ProfileDuplicate, request: Request) -> dict:
    """Duplicate an existing profile (e.g. the example) into a new owned profile."""
    try:
        dest = profile_service.duplicate_profile(
            _app_config(request),
            request.app.state.profiles or {},
            body.source,
            body.name,
        )
    except profile_service.ProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    os.environ[profile_service.registry_key(body.name.strip().lower())] = str(dest)
    _reload(request)
    return _profiles_payload(request)


@router.post("/register")
def register_profile(body: ProfileRegister, request: Request) -> dict:
    """Register an existing local profile directory (validated, not copied)."""
    try:
        loc = profile_service.register_profile(
            _app_config(request),
            request.app.state.profiles or {},
            body.name,
            body.location,
        )
    except profile_service.ProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    os.environ[profile_service.registry_key(body.name.strip().lower())] = str(loc)
    _reload(request)
    return _profiles_payload(request)


@router.delete("/{name}")
def delete_profile(name: str, request: Request) -> dict:
    """Unregister a profile (deleting its files only if it is an owned copy)."""
    profiles = request.app.state.profiles or {}
    key = name.strip().lower()
    profile_dir = profiles.get(key)
    try:
        profile_service.delete_profile(
            _app_config(request),
            key,
            Path(profile_dir) if profile_dir is not None else None,
            request.app.state.profile_name,
        )
    except profile_service.ProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    os.environ.pop(profile_service.registry_key(key), None)
    _reload(request)
    return _profiles_payload(request)
