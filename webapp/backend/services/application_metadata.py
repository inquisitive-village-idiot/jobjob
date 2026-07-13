#!/usr/bin/env python3
"""Per-application metadata: status (and, later, changelog notes).

Each application folder in the locally-synced Drive mirror may hold a
``metadata.json`` written by this module; the Drive sync client uploads it, so
the metadata travels with the application folder. Schema (version 2)::

    {
      "schema_version": 2,
      "status": "APPLIED",
      "status_updated_at": "2026-06-10T18:24:31+00:00",
      "notes": []
    }

``notes`` is reserved for changelog-style annotations (future work); unknown
keys are preserved verbatim on every write so newer schemas survive round-trips.

``entity_id`` (application-identity, phase 1) is this module's entity-tier
field: a uuid4 minted once (``ensure_entity_id``) and reused on every rebuild.
It is additive and round-tripped like any other unknown key — it does **not**
bump ``schema_version``. Its absence marks a folder as legacy: joins fall back
to the folder name, and the id is minted lazily on the folder's next natural
write (no backfill, no mirror rewrite).

Schema versioning: ``schema_version`` is stamped on every write and is the
single source of truth reads key off; it increments only on format changes.
Absence of the stamp is a valid ``v0`` (the entire pre-versioning mirror is
retroactively versioned without touching a byte). ``read_metadata`` runs
``_migrate`` on every read: files at ``schema_version < 2`` have a stored
``status: "GENERATED"`` normalized to ``"BUILT"`` (the v1 status vocabulary
was renamed in the full-build-rename change) — the source file is never
rewritten by a read; only the next write stamps ``2``.

Errors raise: a corrupt or unreadable metadata file raises ``ValueError`` /
``OSError``. Callers iterating many folders (the tracking list) catch, log, and
skip; single-item callers (the status endpoint) surface the failure.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


# Mirrored by APP_STATUSES in webapp/frontend/src/types/index.ts — keep in sync.
class ApplicationStatus(str, Enum):
    """Lifecycle status of a job application."""

    BUILT = "BUILT"  # default: artifacts produced, nothing submitted
    APPLIED = "APPLIED"
    IGNORED = "IGNORED"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    OFFER = "OFFER"
    ACCEPTED = "ACCEPTED"
    WITHDRAWN = "WITHDRAWN"


DEFAULT_STATUS = ApplicationStatus.BUILT
METADATA_FILENAME = "metadata.json"
_SCHEMA_VERSION = 2

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


def entity_id_from_metadata(meta: dict) -> Optional[str]:
    """Return the ``entity_id`` recorded in a metadata dict, if any.

    Arguments:
        meta: A parsed metadata dict (e.g. from :func:`read_metadata`).
    Returns:
        The entity id, or None when absent (a legacy record — see
        ``ensure_entity_id``).
    """
    value = meta.get("entity_id")
    return value if isinstance(value, str) and value else None


def read_entity_id(folder: Path) -> Optional[str]:
    """Return the entity id recorded for an application folder, if any.

    Arguments:
        folder: The application folder in the local mirror.
    Returns:
        The entity id, or None when no metadata file or no ``entity_id`` field
        exists (a legacy folder — joins by name, per the application-identity
        design).
    Raises:
        ValueError: The metadata file is corrupt.
        OSError: The metadata file cannot be read.
    """
    return entity_id_from_metadata(read_metadata(folder))


def ensure_entity_id(folder: Path) -> str:
    """Read-or-mint-and-write the folder's stable ``entity_id``.

    Mint-once / reuse-on-rebuild: an existing ``entity_id`` is always reused
    (no write happens); only a folder with none gets a freshly minted uuid4,
    written back with ``status``/``notes``/other keys preserved unchanged. This
    is the entity tier's home (``metadata.json``) — called at build/enrich time
    so a legacy (id-less) folder gains an id lazily, on its next natural write,
    per the application-identity design (no backfill, no mirror rewrite).

    Arguments:
        folder: The application folder in the local mirror.
    Returns:
        The entity id (existing or freshly minted).
    Raises:
        ValueError: An existing metadata file is corrupt (not overwritten).
        OSError: The file cannot be read or written.
    """
    data = read_metadata(folder)
    existing = entity_id_from_metadata(data)
    if existing:
        return existing
    new_id = str(uuid.uuid4())
    data["schema_version"] = _SCHEMA_VERSION
    data["entity_id"] = new_id
    _write_metadata(folder, data)
    return new_id


def _migrate(data: dict) -> dict:
    """Normalize a metadata dict read from disk to the current in-memory shape.

    Keyed on ``schema_version`` (absent ⇒ ``0``), not on the app version. A file
    at ``schema_version < 2`` (the full-build-rename cutover) has a stored
    ``status: "GENERATED"`` normalized to ``"BUILT"``; a ``v2`` file is already
    post-rename and passed through unchanged. This is a read-only shim — the
    source file is never rewritten here, only the next write stamps the new
    version. Shaped as a single migration step now (YAGNI on a full registry),
    but structured so later non-trivial format changes can grow it into a chain.
    """
    if data.get("schema_version", 0) < 2 and data.get("status") == "GENERATED":
        data = {**data, "status": "BUILT"}
    return data


def read_metadata(folder: Path) -> dict:
    """Return the metadata dict for an application folder.

    A missing file is the normal state for most folders and returns ``{}``.
    The returned dict is migrated to the current schema (see :func:`_migrate`);
    the file on disk is left untouched by a read.

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
    return _migrate(data)


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


def union_notes(folder: Path, incoming: list[dict]) -> dict:
    """Merge externally-sourced changelog notes into this folder's metadata.

    Used by application-identity dedup merge (design D3): the "loser" entity's
    notes are unioned into the surviving entity's changelog, then sorted by
    timestamp. Only ``notes`` changes here — ``entity_id``/``status`` (and
    everything else) are left exactly as they were; the caller
    (``services.dedup_service.merge_applications``) owns those invariants. An
    entry already present (identical ``ts``/``kind``/``text``) is not
    re-added, so calling this twice with the same ``incoming`` is a no-op the
    second time.

    Arguments:
        folder: The surviving entity's folder.
        incoming: Note entries to merge in (e.g. the loser's ``notes`` list).
    Returns:
        The full metadata dict as written.
    Raises:
        ValueError: An existing metadata file is corrupt (not overwritten).
        OSError: The file cannot be read or written.
    """
    data = read_metadata(folder)
    data.setdefault("schema_version", _SCHEMA_VERSION)
    existing = data.setdefault("notes", [])
    seen = {(n.get("ts"), n.get("kind"), n.get("text")) for n in existing}
    for note in incoming:
        key = (note.get("ts"), note.get("kind"), note.get("text"))
        if key not in seen:
            existing.append(note)
            seen.add(key)
    existing.sort(key=lambda n: n.get("ts") or "")
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
