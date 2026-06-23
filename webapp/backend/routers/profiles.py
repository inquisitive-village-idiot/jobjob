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

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jobjob.config import (
    DEFAULT_CONTENT_DIR,
    DEFAULT_PROMPT_DIR,
    DEFAULT_REFERENCE_DIR,
    ENV_CONTENT_DIR,
    ENV_PROMPT_DIR,
    ENV_REFERENCE_DIR,
    PROFILE_KEYS,
)
from jobjob.loader.profiles import ENV_ACTIVE_PROFILE, Profile, profile_config_file
from services import profile_service
from services.config_service import read_config, write_config

router = APIRouter()

# Resource directories surfaced on a profile (env key, conventional default).
_RESOURCE_DIRS = (
    (ENV_CONTENT_DIR, DEFAULT_CONTENT_DIR),
    (ENV_REFERENCE_DIR, DEFAULT_REFERENCE_DIR),
    (ENV_PROMPT_DIR, DEFAULT_PROMPT_DIR),
)


def _count_files(directory: Path) -> int:
    """Count non-hidden files under ``directory`` recursively.

    Skips dotfiles and anything inside a hidden directory (e.g. ``.git``,
    ``.DS_Store``). Returns 0 when the directory is absent.
    """
    if not directory.is_dir():
        return 0
    return sum(
        1
        for p in directory.rglob("*")
        if p.is_file()
        and not any(part.startswith(".") for part in p.relative_to(directory).parts)
    )


def _profiles(request: Request) -> dict[str, Profile]:
    """Return the resolved ``{name: Profile}`` map from app state."""
    return request.app.state.profiles or {}


def _registry(request: Request) -> dict[str, Path]:
    """Project the Profile map to the ``{name: path}`` map profile_service expects."""
    return {name: p.path for name, p in _profiles(request).items()}


def _entries(request: Request) -> list[dict]:
    """Return per-profile metadata (name, active, read_only, external).

    Reads the read_only/owned flags carried on each ``Profile`` (resolved once at
    load time) rather than recomputing them per request.
    """
    profiles = _profiles(request)
    active = request.app.state.profile_name
    out: list[dict] = []
    for name in sorted(profiles):
        p = profiles[name]
        out.append(
            {
                "name": name,
                "active": name == active,
                "read_only": p.read_only,
                # External = registered in place; not bundled and not jobjob-owned.
                "external": not p.read_only and not p.owned,
            }
        )
    return out


def _profiles_payload(request: Request) -> dict:
    return {
        "active": request.app.state.profile_name,
        "profiles": sorted(_profiles(request).keys()),
        "entries": _entries(request),
    }


@router.get("")
def list_profiles(request: Request) -> dict:
    """Return the registered profile names, the active one, and per-profile metadata."""
    return _profiles_payload(request)


@router.get("/{name}/resources")
def profile_resources(name: str, request: Request) -> dict:
    """Return a profile's location and its resource dirs (resolved path + file count).

    The dir names come from the profile's own committed config (CONTENT_DIR/
    REFERENCE_DIR/PROMPT_DIR), each falling back to its conventional default, so the
    counts are correct even for a non-active profile.

    Raises:
        400: If the name is not a registered profile.
    """
    profile = _profiles(request).get(name.strip().lower())
    if profile is None:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {name}")
    cfg = read_config(profile_config_file(profile.path), keys=PROFILE_KEYS)
    resources = []
    for env_key, default in _RESOURCE_DIRS:
        configured = str(cfg.get(env_key, {}).get("value") or "").strip() or default
        path = profile.path / configured
        resources.append(
            {
                "name": default,
                "dir": configured,
                "path": str(path),
                "exists": path.is_dir(),
                "count": _count_files(path),
            }
        )
    return {
        "name": profile.name,
        "location": str(profile.path),
        "resources": resources,
    }


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
    if name not in _profiles(request):
        raise HTTPException(status_code=400, detail=f"Unknown profile: {body.name}")
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
            _app_config(request), _registry(request), body.name
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
            _registry(request),
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
            _registry(request),
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
    key = name.strip().lower()
    profile = _profiles(request).get(key)
    if profile is None:
        raise HTTPException(status_code=400, detail=f"Unknown profile: {name}")
    try:
        profile_service.delete_profile(
            _app_config(request), profile, request.app.state.profile_name
        )
    except profile_service.ProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    os.environ.pop(profile_service.registry_key(key), None)
    _reload(request)
    return _profiles_payload(request)
