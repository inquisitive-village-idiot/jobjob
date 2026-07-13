#!/usr/bin/env python3
"""Filesystem-backed ``StorageAdapter``: the entity root is a plain directory.

Used for plain-file artifacts regardless of Drive mode (``summary.json``,
``skills_analysis.json``, the JD copy) and for every artifact in fully local
(``--skip-drive``) mode.
"""

import json
import shutil
from pathlib import Path
from typing import Optional

from jobjob.storage.base import (
    ARCHIVE_DIRNAME,
    ENTITY_TIER_FILES,
    EXECUTION_NOTE_FILENAME,
    PlacedArtifact,
    archive_timestamp,
)


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

    def promote_execution(self, timestamp: str) -> list[PlacedArtifact]:
        """Archive the current root first, then move ``timestamp`` up to root."""
        archive_dir = self.root / ARCHIVE_DIRNAME / timestamp
        if not archive_dir.is_dir():
            raise FileNotFoundError(f"No archived execution at {timestamp!r}.")

        # Step 1 — archive whatever is currently at root, under a fresh
        # timestamp, so the promoted files never share the root with the
        # outgoing ones (design D2). Guard the (exceedingly unlikely) same-
        # second collision with the timestamp being promoted.
        new_ts = archive_timestamp()
        if new_ts == timestamp:
            new_ts = f"{new_ts}-prior"
        self.archive_execution(new_ts)

        # Step 2 — move the promoted execution's artifacts up to root. The
        # note/lock sidecar describes archived state and does not travel.
        moved = []
        for entry in sorted(archive_dir.iterdir()):
            if entry.name == EXECUTION_NOTE_FILENAME:
                continue
            dest = self.root / entry.name
            entry.rename(dest)
            moved.append(PlacedArtifact(name=entry.name, location=str(dest)))
        shutil.rmtree(archive_dir, ignore_errors=True)
        return moved

    def _note_path(self, timestamp: str) -> Path:
        return self.root / ARCHIVE_DIRNAME / timestamp / EXECUTION_NOTE_FILENAME

    def read_execution_note(self, timestamp: str) -> dict:
        """Tolerant read of the note/lock sidecar (default when absent/corrupt)."""
        empty = {"note": None, "locked": False}
        path = self._note_path(timestamp)
        if not path.is_file():
            return empty
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return empty
        if not isinstance(data, dict):
            return empty
        return {"note": data.get("note"), "locked": bool(data.get("locked", False))}

    def write_execution_note(
        self,
        timestamp: str,
        *,
        note: Optional[str] = None,
        locked: Optional[bool] = None,
    ) -> dict:
        archive_dir = self.root / ARCHIVE_DIRNAME / timestamp
        if not archive_dir.is_dir():
            raise FileNotFoundError(f"No archived execution at {timestamp!r}.")
        current = self.read_execution_note(timestamp)
        if note is not None:
            current["note"] = note
        if locked is not None:
            current["locked"] = bool(locked)
        self._note_path(timestamp).write_text(
            json.dumps(current, indent=2) + "\n", encoding="utf-8"
        )
        return current

    def purge_executions(self) -> list[str]:
        """Delete archived executions, skipping any locked one."""
        archive_root = self.root / ARCHIVE_DIRNAME
        if not archive_root.is_dir():
            return []
        purged = []
        for ts in self.list_executions():
            if self.read_execution_note(ts).get("locked"):
                continue
            shutil.rmtree(archive_root / ts, ignore_errors=True)
            purged.append(ts)
        return purged

    def merge_from(
        self, other: "LocalStorageAdapter", timestamp: str
    ) -> list[PlacedArtifact]:
        """Absorb ``other``'s executions into this entity's archive (dedup merge).

        See ``StorageAdapter.merge_from`` for the full contract. ``other`` is
        the "loser" duplicate; its entity-tier files and directory are left
        untouched here (the caller removes them once notes are unioned).
        """
        moved: list[PlacedArtifact] = []

        # Absorb the loser's current root execution (if any) under a fresh
        # timestamp — exactly the archive_execution exclusion rules apply.
        if other.root.is_dir():
            entries = [
                p
                for p in other.root.iterdir()
                if p.name not in ENTITY_TIER_FILES and p.name != ARCHIVE_DIRNAME
            ]
            if entries:
                archive_dir = self.root / ARCHIVE_DIRNAME / timestamp
                archive_dir.mkdir(parents=True, exist_ok=True)
                for entry in entries:
                    dest = archive_dir / entry.name
                    entry.rename(dest)
                    moved.append(PlacedArtifact(name=entry.name, location=str(dest)))

        # Re-parent the loser's own already-archived executions, one whole
        # timestamp directory at a time; a name collision is suffixed rather
        # than silently overwritten.
        for ts in other.list_executions():
            src_dir = other.root / ARCHIVE_DIRNAME / ts
            dest_ts = ts
            attempt = 0
            while (self.root / ARCHIVE_DIRNAME / dest_ts).exists():
                attempt += 1
                dest_ts = f"{ts}-merged" if attempt == 1 else f"{ts}-merged-{attempt}"
            dest_dir = self.root / ARCHIVE_DIRNAME / dest_ts
            dest_dir.parent.mkdir(parents=True, exist_ok=True)
            src_dir.rename(dest_dir)
            for f in sorted(dest_dir.iterdir()):
                moved.append(PlacedArtifact(name=f.name, location=str(f)))

        return moved


# __END__
