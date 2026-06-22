#!/usr/bin/env python3
"""Per-application metadata: status (and, later, changelog notes).

Each application folder in the locally-synced Drive mirror may hold a
``metadata.json`` written by this module; the Drive sync client uploads it, so
the metadata travels with the application folder. Schema (version 1)::

    {
      "schema_version": 1,
      "status": "APPLIED",
      "status_updated_at": "2026-06-10T18:24:31+00:00",
      "notes": []
    }

``notes`` is reserved for changelog-style annotations (future work); unknown
keys are preserved verbatim on every write so newer schemas survive round-trips.

Errors raise: a corrupt or unreadable metadata file raises ``ValueError`` /
``OSError``. Callers iterating many folders (the tracking list) catch, log, and
skip; single-item callers (the status endpoint) surface the failure.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


# Mirrored by APP_STATUSES in webapp/frontend/src/types/index.ts — keep in sync.
class ApplicationStatus(str, Enum):
    """Lifecycle status of a job application."""

    GENERATED = "GENERATED"  # default: artifacts produced, nothing submitted
    APPLIED = "APPLIED"
    IGNORED = "IGNORED"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    OFFER = "OFFER"
    ACCEPTED = "ACCEPTED"
    WITHDRAWN = "WITHDRAWN"


DEFAULT_STATUS = ApplicationStatus.GENERATED
METADATA_FILENAME = "metadata.json"
_SCHEMA_VERSION = 1

# Kinds of changelog note. "status" entries are auto-logged on a status transition;
# "note" entries are free-text annotations the user adds. Mirrored by NOTE_KINDS in
# webapp/frontend/src/types/index.ts — keep in sync.
NOTE_STATUS = "status"
NOTE_FREEFORM = "note"


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def status_from_metadata(meta: dict) -> Optional[ApplicationStatus]:
    """Return the status recorded in a metadata dict, if any.

    Arguments:
        meta: A parsed metadata dict (e.g. from :func:`read_metadata`).
    Returns:
        The status, or None when no status field is present.
    Raises:
        ValueError: The stored status string is not a known status.
    """
    raw = meta.get("status")
    return ApplicationStatus(raw) if raw is not None else None


def read_metadata(folder: Path) -> dict:
    """Return the metadata dict for an application folder.

    A missing file is the normal state for most folders and returns ``{}``.

    Arguments:
        folder: The application folder in the local mirror.
    Returns:
        The parsed metadata dict, or ``{}`` when no metadata file exists.
    Raises:
        ValueError: The file is not valid JSON or not a JSON object.
        OSError: The file exists but cannot be read.
    """
    path = folder / METADATA_FILENAME
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return data


def read_status(folder: Path) -> Optional[ApplicationStatus]:
    """Return the recorded status for an application folder, if any.

    Arguments:
        folder: The application folder in the local mirror.
    Returns:
        The status, or None when no metadata file or no status field exists.
    Raises:
        ValueError: The metadata file is corrupt or holds an unknown status.
        OSError: The metadata file cannot be read.
    """
    return status_from_metadata(read_metadata(folder))


def read_notes(folder: Path) -> list[dict]:
    """Return the changelog notes for an application folder (oldest first).

    Arguments:
        folder: The application folder in the local mirror.
    Returns:
        The list of note entries, or ``[]`` when none exist.
    Raises:
        ValueError: The metadata file is corrupt.
        OSError: The metadata file cannot be read.
    """
    notes = read_metadata(folder).get("notes")
    return notes if isinstance(notes, list) else []


def _write_metadata(folder: Path, data: dict) -> dict:
    """Atomically write ``data`` to the folder's metadata file and return it.

    A temp file in the same directory is ``os.replace``d over the target, which
    plays safest with the Drive sync client (no partial reads of the live file).

    Raises:
        OSError: The file cannot be written.
    """
    fd, tmp_name = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp_name, folder / METADATA_FILENAME)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return data


def _append_note(data: dict, text: str, kind: str, ts: str) -> None:
    """Append a note entry to ``data['notes']`` in place (creating the list)."""
    data.setdefault("notes", [])
    data["notes"].append({"ts": ts, "kind": kind, "text": text})


def write_status(folder: Path, status: ApplicationStatus) -> dict:
    """Record ``status`` in the folder's metadata file and return the new dict.

    A status *change* is auto-logged to the changelog ``notes`` (kind ``status``),
    sharing the same timestamp as ``status_updated_at``. Re-setting the same status
    is a no-op for the changelog. Existing keys are preserved.

    Arguments:
        folder: The application folder in the local mirror.
        status: The status to record.
    Returns:
        The full metadata dict as written.
    Raises:
        ValueError: An existing metadata file is corrupt (not overwritten).
        OSError: The file cannot be read or written.
    """
    data = read_metadata(folder)
    previous = status_from_metadata(data)
    now = _now_iso()

    data["schema_version"] = _SCHEMA_VERSION
    data["status"] = status.value
    data["status_updated_at"] = now
    data.setdefault("notes", [])

    if previous != status:
        text = (
            f"Status changed from {previous.value} to {status.value}"
            if previous is not None
            else f"Status set to {status.value}"
        )
        _append_note(data, text, NOTE_STATUS, now)
    return _write_metadata(folder, data)


def add_note(folder: Path, text: str, *, kind: str = NOTE_FREEFORM) -> dict:
    """Append a changelog note to the folder's metadata file and return the dict.

    Arguments:
        folder: The application folder in the local mirror.
        text: The note text (must be non-empty after stripping).
        kind: ``note`` (free-text, default) or ``status`` (a transition entry).
    Returns:
        The full metadata dict as written.
    Raises:
        ValueError: The text is empty, or an existing metadata file is corrupt.
        OSError: The file cannot be read or written.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Note text must not be empty.")
    data = read_metadata(folder)
    data.setdefault("schema_version", _SCHEMA_VERSION)
    _append_note(data, cleaned, kind, _now_iso())
    return _write_metadata(folder, data)
