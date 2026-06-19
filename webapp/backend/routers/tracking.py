#!/usr/bin/env python3
"""Tracking API: input queue, completed jobs, and application status."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from security import safe_path
from services.application_metadata import ApplicationStatus, write_status
from services.tracking_service import (
    invalidate_completed_cache,
    list_completed,
    list_queue,
)

router = APIRouter()


def _settings(request: Request) -> dict:
    return request.app.state.settings


@router.get("/queue")
def get_queue(request: Request) -> list[dict]:
    """Return unprocessed files from ``data/jobs/`` and ``data/profiles/``."""
    s = _settings(request)
    return list_queue(s["data_dir"])


class QueueDelete(BaseModel):
    path: str


@router.delete("/queue")
def delete_queue_item(body: QueueDelete, request: Request) -> dict:
    """Delete a queued input file (e.g. clearing a failed job's JD).

    Restricted to files directly under ``data_dir`` (and its jobs/profiles subdirs);
    completed artifacts are off-limits.
    """
    s = _settings(request)
    data_dir = Path(s["data_dir"]).resolve()
    try:
        target = safe_path(body.path)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    resolved = target.resolve()
    try:
        rel = resolved.relative_to(data_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path is not in the input area.")
    if rel.parts and rel.parts[0] == "completed":
        raise HTTPException(status_code=400, detail="Refusing to delete completed artifacts.")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Queued file not found.")
    resolved.unlink()
    return {"deleted": str(resolved)}


@router.get("/completed")
def get_completed(request: Request, refresh: bool = False) -> list[dict]:
    """Return completed applications (synced mirror or Drive) and completed profiles.

    The list is cached and recomputed only after a job completes or when
    ``refresh=true`` is passed (explicit user refresh).
    """
    s = _settings(request)
    return list_completed(
        data_dir=s["data_dir"],
        applications_folder_id=s.get("applications_folder_id"),
        credentials_file=s.get("credentials_file"),
        token_file=s.get("token_file"),
        applications_local_dir=s.get("applications_local_dir"),
        linkedin_sheet_id=s.get("linkedin_sheet_id"),
        force_refresh=refresh,
    )


class StatusUpdate(BaseModel):
    status: ApplicationStatus


@router.patch("/applications/{folder_name}/status")
def set_application_status(
    folder_name: str, body: StatusUpdate, request: Request
) -> dict:
    """Record an application's status in its folder's ``metadata.json``.

    Writes through the locally-synced Drive mirror (the sync client uploads the
    file), so status changes require ``applications_local_dir`` to be configured.
    """
    s = _settings(request)
    local_dir = s.get("applications_local_dir")
    if not local_dir:
        raise HTTPException(
            status_code=400,
            detail="Local applications mirror not configured; status writes unavailable.",
        )
    # folder_name must be a plain directory name — no separators or traversal.
    if (
        not folder_name
        or folder_name != Path(folder_name).name
        or "\\" in folder_name
        or folder_name.startswith(".")
    ):
        raise HTTPException(status_code=400, detail="Invalid folder name.")
    try:
        folder = safe_path(Path(local_dir).expanduser() / folder_name)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail="Application folder not found.")
    try:
        meta = write_status(folder, body.status)
    except (ValueError, OSError) as exc:
        raise HTTPException(
            status_code=500, detail=f"Could not write metadata: {exc}"
        )
    invalidate_completed_cache()
    return {
        "folder_name": folder_name,
        "app_status": meta["status"],
        "status_updated_at": meta["status_updated_at"],
    }
