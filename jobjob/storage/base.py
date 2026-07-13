#!/usr/bin/env python3
"""Provider-agnostic storage adapter interface.

Mirrors the AI-adapter idiom (``jobjob.ailib.client.base.AIAdapter``): a thin
Protocol plus duck-typed concrete adapters, injected as a default kwarg (see
``_drive_builder`` in ``jobjob.apply.workflow``). An adapter is scoped to one
entity's execution root at construction time (a local directory for
``LocalStorageAdapter``, a Drive folder id for ``DriveStorageAdapter``) and
exposes the same four operations regardless of backend — dispatch per file type
(Google Doc vs. plain file) happens by choosing *which* adapter to call, not by
branching inside a shared implementation.

Design references: ``openspec/changes/application-identity/design.md`` D2
(physical layout: root = primary, ``archive/<timestamp>`` for superseded
executions) and D7 (the adapter seam itself).
"""

import dataclasses as dcs
from datetime import datetime
from typing import Optional, Protocol

# Entity/source-tier files: never archived (they describe the entity across all
# of its executions, not one execution) — same carve-out `metadata.json` gets
# from the artifact-completeness count today.
ENTITY_TIER_FILES = frozenset({"metadata.json", "source.json"})

ARCHIVE_DIRNAME = "archive"

# Per-archived-execution sidecar holding the user's note ("why we kept this
# run") and the purge-exempting lock flag (design D5, phase 6b). Lives inside
# the execution's own ``archive/<timestamp>/`` directory — never at the entity
# root — and does not travel with the execution on promote (see
# ``promote_execution``): it describes the *archived* state, which promotion
# ends.
EXECUTION_NOTE_FILENAME = "execution.json"


def archive_timestamp(_now: datetime | None = None) -> str:
    """Return the human-facing, filesystem/Drive-safe timestamp for an archive dir.

    Seconds resolution; dots instead of colons so the name is valid on every
    filesystem and in Drive. The machine join back to the execution is the
    ``run_id`` inside that execution's ``summary.json`` (design D2), not this
    string.
    """
    now = _now or datetime.now()
    return now.strftime("%Y-%m-%dT%H.%M.%S")


@dcs.dataclass(frozen=True)
class PlacedArtifact:
    """Where one artifact ended up after ``place``/``archive_execution``.

    Attributes:
        name: The artifact's stored name (e.g. ``"TilaMer_Resume"``).
        location: Backend-specific location — a local path string for
            ``LocalStorageAdapter``, a Drive file id for ``DriveStorageAdapter``.
    """

    name: str
    location: str


class StorageAdapter(Protocol):
    """Place/find/archive execution artifacts for one entity's root.

    An implementation is constructed already scoped to one entity (a folder
    path, or a Drive folder id) — every method below operates relative to that
    root, so callers never pass the entity/folder again.
    """

    def place(self, source, name: str) -> PlacedArtifact:
        """Place the local file ``source`` into the entity root as ``name``.

        Returns:
            The ``PlacedArtifact`` describing where it landed.
        """
        ...

    def exists(self, name: str) -> bool:
        """Return whether an artifact named ``name`` already exists at the root."""
        ...

    def archive_execution(self, timestamp: str) -> list[PlacedArtifact]:
        """Move everything currently at the root into ``archive/<timestamp>/``.

        Excludes ``ENTITY_TIER_FILES`` (never archived — they span every
        execution) and any existing ``archive/`` dir (never nested, per D2).
        A root with no execution artifacts (fresh entity) is a no-op.

        Returns:
            The list of artifacts moved (empty when there was nothing to move).
        """
        ...

    def list_executions(self) -> list[str]:
        """Return archived execution timestamps (``archive/`` subdir names), sorted."""
        ...

    def promote_execution(self, timestamp: str) -> list[PlacedArtifact]:
        """Make the archived execution at ``archive/<timestamp>`` the primary one.

        Strictly in this order (design D2, so no overwrite window ever exists):
        (1) archive whatever currently sits at the root, under a *fresh*
        timestamp (as ``archive_execution`` would for any other re-build);
        (2) move the promoted execution's artifacts up to the root. The
        promoted execution's note/lock sidecar (``EXECUTION_NOTE_FILENAME``)
        does not travel to the root — it describes an *archived* state, which
        promotion ends — and the now-empty archive directory is discarded.

        Returns:
            The artifacts placed at the root (the promoted execution's own).
        Raises:
            FileNotFoundError: No archived execution exists at ``timestamp``.
        """
        ...

    def read_execution_note(self, timestamp: str) -> dict:
        """Return ``{"note": str | None, "locked": bool}`` for an archived execution.

        Tolerant read (same posture as ``metadata.json``/``source.json``): a
        missing or corrupt sidecar degrades to the empty default rather than
        raising.
        """
        ...

    def write_execution_note(
        self,
        timestamp: str,
        *,
        note: Optional[str] = None,
        locked: Optional[bool] = None,
    ) -> dict:
        """Update the note/lock sidecar for an archived execution.

        Only the fields explicitly passed (non-``None``) change; the other is
        left as previously stored (or its default). To clear a note, pass
        ``note=""`` explicitly — ``None`` means "leave unchanged", mirroring
        ``application_source.edit_source``.

        Returns:
            The full sidecar dict as written.
        Raises:
            FileNotFoundError: No archived execution exists at ``timestamp``.
        """
        ...

    def purge_executions(self) -> list[str]:
        """Delete every archived execution for this entity, skipping locked ones.

        Returns:
            The timestamps actually purged. A locked execution is silently
            skipped (exempt, not an error) — see design D5.
        """
        ...


# __END__
