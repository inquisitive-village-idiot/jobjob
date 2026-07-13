#!/usr/bin/env python3
"""Filesystem-backed ``StorageAdapter``: the entity root is a plain directory.

Used for plain-file artifacts regardless of Drive mode (``summary.json``,
``skills_analysis.json``, the JD copy) and for every artifact in fully local
(``--skip-drive``) mode.
"""

import shutil
from pathlib import Path

from jobjob.storage.base import ARCHIVE_DIRNAME, ENTITY_TIER_FILES, PlacedArtifact


class LocalStorageAdapter:
    """Pathlib-backed ``StorageAdapter`` scoped to one entity folder."""

    def __init__(self, root: Path) -> None:
        """Initialize the adapter.

        Arguments:
            root: The entity folder (created lazily on first ``place``/
                ``archive_execution`` call, not at construction time).
        """
        self.root = Path(root)

    def place(self, source: Path, name: str) -> PlacedArtifact:
        """Move ``source`` into the root as ``name`` (created if absent).

        A no-op move (``source`` already *is* the destination — e.g. a caller
        that wrote directly into the entity root) is detected and skipped
        rather than erroring.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        source = Path(source)
        dest = self.root / name
        if source.resolve() != dest.resolve():
            shutil.move(str(source), str(dest))
        return PlacedArtifact(name=name, location=str(dest))

    def exists(self, name: str) -> bool:
        """Return whether ``name`` is present at the root."""
        return (self.root / name).exists()

    def archive_execution(self, timestamp: str) -> list[PlacedArtifact]:
        """Move root entries (bar entity-tier/``archive/``) into ``archive/<ts>/``."""
        if not self.root.is_dir():
            return []  # EARLY EXIT: nothing has ever been placed here.

        entries = [
            p
            for p in self.root.iterdir()
            if p.name not in ENTITY_TIER_FILES and p.name != ARCHIVE_DIRNAME
        ]
        if not entries:
            return []  # EARLY EXIT: fresh entity, no prior execution to archive.

        archive_dir = self.root / ARCHIVE_DIRNAME / timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)
        moved = []
        for entry in entries:
            dest = archive_dir / entry.name
            entry.rename(dest)
            moved.append(PlacedArtifact(name=entry.name, location=str(dest)))
        return moved

    def list_executions(self) -> list[str]:
        """Return archived execution timestamps (``archive/`` subdir names), sorted."""
        archive_root = self.root / ARCHIVE_DIRNAME
        if not archive_root.is_dir():
            return []
        return sorted(p.name for p in archive_root.iterdir() if p.is_dir())


# __END__
