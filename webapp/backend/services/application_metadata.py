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
    raw = read_metadata(folder).get("status")
    if raw is None:
        return None
    return ApplicationStatus(raw)


def write_status(folder: Path, status: ApplicationStatus) -> dict:
    """Record ``status`` in the folder's metadata file and return the new dict.

    Existing keys (including future ``notes``) are preserved. The write is
    atomic: a temp file in the same directory is ``os.replace``d over the
    target, which also plays safest with the Drive sync client.

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
    data["schema_version"] = _SCHEMA_VERSION
    data["status"] = status.value
    data["status_updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data.setdefault("notes", [])

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
