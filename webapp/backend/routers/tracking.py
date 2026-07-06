#!/usr/bin/env python3
"""Tracking API: input queue, completed jobs, and application status."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jobjob.apply.recheck import assessment_as_dict, reassess_application
from security import safe_path
from services.application_metadata import (
    ApplicationStatus,
    add_note,
    read_notes,
    read_status,
    write_status,
)
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
    return list_queue(s["applications_input_dir"])


class QueueDelete(BaseModel):
    path: str


@router.delete("/queue")
def delete_queue_item(body: QueueDelete, request: Request) -> dict:
    """Delete a queued input file (e.g. clearing a failed job's JD).

    Restricted to files directly under ``data_dir`` (and its jobs/profiles subdirs);
    completed artifacts are off-limits.
    """
    s = _settings(request)
    data_dir = Path(s["applications_input_dir"]).resolve()
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
        raise HTTPException(
            status_code=400, detail="Refusing to delete completed artifacts."
        )
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
        data_dir=s["applications_input_dir"],
        applications_folder_id=s.get("applications_output_drive_id"),
        credentials_file=s.get("credentials_file"),
        token_file=s.get("token_file"),
        applications_local_dir=s.get("applications_output_dir"),
        linkedin_sheet_id=s.get("enrichment_output_sheet_id"),
        force_refresh=refresh,
    )


def _resolve_app_folder(request: Request, folder_name: str) -> Path:
    """Resolve and validate an application folder in the local mirror.

    Writes/reads go through the locally-synced Drive mirror, so this requires
    ``applications_local_dir`` to be configured and the folder to exist.

    Raises:
        HTTPException: 400 if the mirror is unconfigured or the name is unsafe;
            404 if the folder does not exist.
    """
    local_dir = _settings(request).get("applications_output_dir")
    if not local_dir:
        raise HTTPException(
            status_code=400,
            detail=(
                "Local applications mirror not configured; status writes "
                "unavailable."
            ),
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
    return folder


class StatusUpdate(BaseModel):
    status: ApplicationStatus


@router.patch("/applications/{folder_name}/status")
def set_application_status(
    folder_name: str, body: StatusUpdate, request: Request
) -> dict:
    """Record an application's status in its folder's ``metadata.json``.

    A status change is auto-logged to the application's changelog notes.
    """
    folder = _resolve_app_folder(request, folder_name)
    try:
        meta = write_status(folder, body.status)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not write metadata: {exc}")
    invalidate_completed_cache()
    return {
        "folder_name": folder_name,
        "app_status": meta["status"],
        "status_updated_at": meta["status_updated_at"],
        "note_count": len(meta.get("notes") or []),
    }


@router.get("/applications/{folder_name}/notes")
def get_application_notes(folder_name: str, request: Request) -> dict:
    """Return an application's changelog notes (oldest first) and current status."""
    folder = _resolve_app_folder(request, folder_name)
    try:
        status = read_status(folder)
        notes = read_notes(folder)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not read metadata: {exc}")
    return {
        "folder_name": folder_name,
        "app_status": status.value if status else None,
        "notes": notes,
    }


class NoteCreate(BaseModel):
    text: str


@router.get("/applications/{folder_name}/ats")
def get_application_ats(folder_name: str, request: Request) -> dict:
    """Re-run the ATS assessment for a processed application, from saved
    artifacts + one Docs read. Zero AI calls; nothing is mutated.

    Raises:
        HTTPException: 404 for an unknown folder; 409 when the saved
            artifacts are missing/invalid (e.g. pre-ATS application).
    """
    folder = _resolve_app_folder(request, folder_name)
    try:
        assessment = reassess_application(folder)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return assessment_as_dict(assessment)


@router.post("/applications/{folder_name}/notes")
def add_application_note(folder_name: str, body: NoteCreate, request: Request) -> dict:
    """Append a free-text changelog note to an application's ``metadata.json``."""
    folder = _resolve_app_folder(request, folder_name)
    try:
        meta = add_note(folder, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not write metadata: {exc}")
    invalidate_completed_cache()
    return {
        "folder_name": folder_name,
        "notes": meta.get("notes") or [],
    }
