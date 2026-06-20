#!/usr/bin/env python3
"""Self-update API: report version/update status, check PyPI, and upgrade in place."""

from fastapi import APIRouter

from services import update_service

router = APIRouter()


@router.get("/status")
def status() -> dict:
    """Return current/latest version, release dates, last-checked time, install method."""
    return update_service.get_status()


@router.post("/check")
def check() -> dict:
    """Force a PyPI check now, then return the refreshed status."""
    update_service.check_for_updates()
    return update_service.get_status()


@router.post("/apply")
def apply() -> dict:
    """Upgrade to the latest release (pipx/pip). Returns the command result."""
    return update_service.apply_update()
