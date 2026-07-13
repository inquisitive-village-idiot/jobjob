#!/usr/bin/env python3
"""Per-application source tier: the posting itself (``source.json``).

Phase 1 of the application-identity model (see ``openspec/changes/
application-identity``). Three tiers share a folder: the **entity**
(``metadata.json`` — status/notes/``entity_id``), the **source** (this module —
the posting: URIs, external ref, and the parse-once ``company``/``role``/
``description``), and **executions** (the build artifacts + ``summary.json``).

Schema (version 1)::

    {
      "schema_version": 1,
      "entity_id": "5b1e...",
      "company": "Acme",
      "role": "Principal Engineer",
      "description": "2-3 sentence summary of the role.",
      "file_uri": "/path/to/JD_Acme_PrincipalEngineer.pdf",
      "web_uri": "https://example.test/jobs/123",
      "external_ref": null
    }

**Parse-once**: ``company``/``role``/``description`` are written once, at first
processing (:func:`ensure_source`); a rebuild reads them back rather than
overwriting, so a re-parse never clobbers a user's correction. Editable fields
(:func:`edit_source`) are limited to ``company``/``role``/``web_uri``/
``external_ref`` — correcting a parse error, not an analysis edit.

Tolerant reads: unlike ``application_metadata`` (which raises on a corrupt
file so single-item callers can surface it), ``source.json`` degrades to ``{}``
on any read problem — missing, corrupt, or not an object — since a folder
listing must never crash on one bad sidecar (D4/legacy posture in design.md).
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

SOURCE_FILENAME = "source.json"
_SCHEMA_VERSION = 1

# Fields correctable by the user (parse-error fixups); "description" and
# "entity_id" are deliberately excluded — see the module docstring.
EDITABLE_FIELDS = ("company", "role", "web_uri", "external_ref")

_LOGGER = logging.getLogger(__name__)


def read_source(folder: Path) -> dict:
    """Return the source dict for an application folder (tolerant read).

    A missing file, unreadable file, corrupt JSON, or non-object JSON all
    degrade to ``{}`` rather than raising — a folder listing must never crash
    on one bad ``source.json`` (same posture as a legacy, id-less folder).

    Arguments:
        folder: The application (entity) folder in the local mirror.
    Returns:
        The parsed source dict, or ``{}`` when absent/unreadable.
    """
    path = Path(folder) / SOURCE_FILENAME
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _LOGGER.warning("Unreadable source.json in %s: %s", folder, exc)
        return {}
    if not isinstance(data, dict):
        _LOGGER.warning("source.json in %s is not a JSON object", folder)
        return {}
    return data


def _write_source(folder: Path, data: dict) -> dict:
    """Atomically write ``data`` to the folder's ``source.json`` and return it.

    Mirrors ``application_metadata._write_metadata``: a temp file in the same
    directory is ``os.replace``d over the target, so the Drive sync client
    never observes a partial read.

    Raises:
        OSError: The file cannot be written.
    """
    folder = Path(folder)
    payload = {"schema_version": _SCHEMA_VERSION, **data}
    fd, tmp_name = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        os.replace(tmp_name, folder / SOURCE_FILENAME)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return payload


def write_source(folder: Path, data: dict) -> dict:
    """Write ``data`` as the folder's ``source.json`` (unconditional overwrite).

    Low-level primitive used by :func:`ensure_source` (parse-once, gated on
    absence) and :func:`edit_source` (merge then overwrite). Most callers want
    one of those instead of this directly.
    """
    return _write_source(folder, data)


def ensure_source(
    folder: Path,
    *,
    entity_id: str,
    company: str,
    role: str,
    description: str,
    file_uri: Optional[str] = None,
    web_uri: Optional[str] = None,
    external_ref: Optional[str] = None,
) -> dict:
    """Write ``source.json`` only when absent (parse-once); return the effective dict.

    A rebuild of a folder that already has a ``source.json`` is a no-op here —
    the existing dict (with the user's own corrections, if any) is returned
    unchanged. This is the enforcement point for the parse-once invariant: the
    parsed company/role/description are only ever written once, at first
    processing.

    Arguments:
        folder: The application (entity) folder.
        entity_id: The entity's id (see ``application_metadata.ensure_entity_id``).
        company: Parsed company name.
        role: Parsed role title.
        description: Parsed role summary.
        file_uri: Local file path/URI for the posting, if known.
        web_uri: The posting's URL, when the input was a URL/paste snapshot.
        external_ref: A JD-embedded requisition id, if any (an attribute, never
            the key).
    Returns:
        The effective source dict (freshly written, or the pre-existing one).
    """
    existing = read_source(folder)
    if existing:
        return existing
    data = {
        "entity_id": entity_id,
        "company": company,
        "role": role,
        "description": description,
        "file_uri": file_uri,
        "web_uri": web_uri,
        "external_ref": external_ref,
    }
    return _write_source(folder, data)


def edit_source(folder: Path, **fields) -> dict:
    """Update only the editable source fields; return the merged dict.

    Any keyword not in :data:`EDITABLE_FIELDS` (e.g. ``description``,
    ``entity_id``) is silently ignored — this function is the last line of
    defense for the parse-once/entity-id-is-not-editable invariants even if a
    caller passes them by mistake. Keys explicitly passed as ``None`` are
    ignored (no-op), not cleared.

    Arguments:
        folder: The application (entity) folder.
        **fields: Any of ``company``/``role``/``web_uri``/``external_ref``.
    Returns:
        The full source dict as written.
    Raises:
        OSError: The file cannot be written.
    """
    data = read_source(folder)
    for key in EDITABLE_FIELDS:
        if key in fields and fields[key] is not None:
            data[key] = fields[key]
    return _write_source(folder, data)


# __END__
