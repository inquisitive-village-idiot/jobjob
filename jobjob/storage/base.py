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
from typing import Protocol

# Entity/source-tier files: never archived (they describe the entity across all
# of its executions, not one execution) — same carve-out `metadata.json` gets
# from the artifact-completeness count today.
ENTITY_TIER_FILES = frozenset({"metadata.json", "source.json"})

ARCHIVE_DIRNAME = "archive"


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


# __END__
