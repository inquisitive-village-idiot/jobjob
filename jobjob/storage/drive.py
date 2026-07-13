#!/usr/bin/env python3
"""Drive-backed ``StorageAdapter``: the entity root is a Drive folder id.

Used for Google-Docs-managed artifacts (résumé/cover/README as gdocs) and for
plain files placed alongside them in the same Drive folder (the JD copy).
Archive/promote move by id (``jobjob.gapi.drive.move_to_folder``) rather than
export/re-import, so a Google Doc's revision history survives (design D2/D7).
"""

import io
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any, Optional

from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from jobjob.gapi import drive as gdrive
from jobjob.storage.base import (
    ARCHIVE_DIRNAME,
    EXECUTION_NOTE_FILENAME,
    PlacedArtifact,
    archive_timestamp,
)


class DriveStorageAdapter:
    """Drive API-backed ``StorageAdapter`` scoped to one application folder."""

    def __init__(
        self,
        service: Any,
        folder_id: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize the adapter.

        Arguments:
            service: An already-built Drive ``service`` client.
            folder_id: The application's Drive folder id (the entity root).
            logger: Optional logger for injection.
        """
        self.service = service
        self.folder_id = folder_id
        self._logger = logger or logging.getLogger(__name__)

    def place(self, source: Path, name: str, _media_cls: Any = None) -> PlacedArtifact:
        """Upload/update ``source`` as a plain file named ``name`` in the folder.

        Google-Docs artifacts (résumé/cover/README) are placed by the caller via
        ``jobjob.gapi.drive.copy_resume_template``/``upload_docx_as_google_doc``
        directly (they need Drive's Docs-specific "reset/re-import in place"
        semantics); this covers everything else (e.g. the JD copy).

        Arguments:
            source: The local file to upload.
            name: The name to place it under.
            _media_cls: Injection point for the media-upload class (testing) —
                forwarded to ``jobjob.gapi.drive.upload_file``.
        """
        mimetype = mimetypes.guess_type(str(source))[0] or gdrive.PDF_MIME
        kwargs: dict = {"mimetype": mimetype, "logger": self._logger}
        if _media_cls is not None:
            kwargs["_media_cls"] = _media_cls
        file_id = gdrive.upload_file(
            self.service, Path(source), self.folder_id, name, **kwargs
        )
        return PlacedArtifact(name=name, location=file_id)

    def exists(self, name: str) -> bool:
        """Return whether a file named ``name`` already exists in the folder."""
        return gdrive._find_in_folder(self.service, name, self.folder_id) is not None

    def archive_execution(self, timestamp: str) -> list[PlacedArtifact]:
        """Move every non-``archive`` item in the folder into ``archive/<timestamp>/``.

        Each item is reparented by id (``move_to_folder``) — a Google Doc keeps
        its id and revision history; no export/re-import happens.
        """
        archive_root_id = gdrive.ensure_subfolder(
            self.service, self.folder_id, ARCHIVE_DIRNAME, logger=self._logger
        )
        items = (
            self.service.files()
            .list(
                q=(
                    f"'{self.folder_id}' in parents and trashed = false "
                    f"and name != '{ARCHIVE_DIRNAME}'"
                ),
                fields="files(id, name)",
            )
            .execute()
            .get("files", [])
        )
        if not items:
            return []  # EARLY EXIT: fresh entity, no prior execution to archive.

        archive_dir_id = gdrive.ensure_subfolder(
            self.service, archive_root_id, timestamp, logger=self._logger
        )
        moved = []
        for item in items:
            gdrive.move_to_folder(
                self.service,
                item["id"],
                archive_dir_id,
                current_parent_id=self.folder_id,
                logger=self._logger,
            )
            moved.append(PlacedArtifact(name=item["name"], location=item["id"]))
        return moved

    def list_executions(self) -> list[str]:
        """Return archived execution timestamps (``archive/`` subfolders), sorted."""
        archive_root_id = gdrive._find_in_folder(
            self.service, ARCHIVE_DIRNAME, self.folder_id
        )
        if not archive_root_id:
            return []
        results = (
            self.service.files()
            .list(
                q=(
                    f"'{archive_root_id}' in parents and trashed = false "
                    f"and mimeType = '{gdrive.FOLDER_MIME}'"
                ),
                fields="files(id, name)",
            )
            .execute()
        )
        return sorted(f["name"] for f in results.get("files", []))

    def _archived_execution_folder_id(self, timestamp: str) -> Optional[str]:
        """Return the Drive folder id for ``archive/<timestamp>``, if it exists."""
        archive_root_id = gdrive._find_in_folder(
            self.service, ARCHIVE_DIRNAME, self.folder_id
        )
        if not archive_root_id:
            return None
        return gdrive._find_in_folder(self.service, timestamp, archive_root_id)

    def promote_execution(self, timestamp: str) -> list[PlacedArtifact]:
        """Archive the current root first, then move ``timestamp`` up to root."""
        target_id = self._archived_execution_folder_id(timestamp)
        if not target_id:
            raise FileNotFoundError(f"No archived execution at {timestamp!r}.")

        # Step 1 — archive whatever is currently at root, under a fresh
        # timestamp, so the promoted files never share the root with the
        # outgoing ones (design D2).
        new_ts = archive_timestamp()
        if new_ts == timestamp:
            new_ts = f"{new_ts}-prior"
        self.archive_execution(new_ts)

        # Step 2 — move the promoted execution's files up to root by id (the
        # note/lock sidecar describes archived state and does not travel).
        items = (
            self.service.files()
            .list(
                q=(
                    f"'{target_id}' in parents and trashed = false "
                    f"and name != '{EXECUTION_NOTE_FILENAME}'"
                ),
                fields="files(id, name)",
            )
            .execute()
            .get("files", [])
        )
        moved = []
        for item in items:
            gdrive.move_to_folder(
                self.service,
                item["id"],
                self.folder_id,
                current_parent_id=target_id,
                logger=self._logger,
            )
            moved.append(PlacedArtifact(name=item["name"], location=item["id"]))
        # Discard the now-empty (bar a possible note sidecar) archived folder.
        gdrive.delete_file(self.service, target_id, logger=self._logger)
        return moved

    def _find_note_id(self, dir_id: str) -> Optional[str]:
        """Return the id of the note/lock sidecar in ``dir_id``, if present."""
        return gdrive._find_in_folder(self.service, EXECUTION_NOTE_FILENAME, dir_id)

    def _read_note_content(
        self,
        note_id: Optional[str],
        _download_cls: Any = MediaIoBaseDownload,
    ) -> dict:
        """Read the sidecar given an already-resolved note id (or None: absent)."""
        empty = {"note": None, "locked": False}
        if not note_id:
            return empty
        try:
            buffer = io.BytesIO()
            downloader = _download_cls(
                buffer, self.service.files().get_media(fileId=note_id)
            )
            done = False
            while not done:
                _, done = downloader.next_chunk()
            data = json.loads(buffer.getvalue().decode("utf-8"))
        except (OSError, ValueError) as exc:
            self._logger.warning("Unreadable execution note %s: %s", note_id, exc)
            return empty
        if not isinstance(data, dict):
            return empty
        return {"note": data.get("note"), "locked": bool(data.get("locked", False))}

    def read_execution_note(
        self, timestamp: str, _download_cls: Any = MediaIoBaseDownload
    ) -> dict:
        """Tolerant read of the note/lock sidecar (default when absent/corrupt)."""
        dir_id = self._archived_execution_folder_id(timestamp)
        if not dir_id:
            return {"note": None, "locked": False}
        note_id = self._find_note_id(dir_id)
        return self._read_note_content(note_id, _download_cls=_download_cls)

    def write_execution_note(
        self,
        timestamp: str,
        *,
        note: Optional[str] = None,
        locked: Optional[bool] = None,
        _media_cls: Any = MediaIoBaseUpload,
        _download_cls: Any = MediaIoBaseDownload,
    ) -> dict:
        dir_id = self._archived_execution_folder_id(timestamp)
        if not dir_id:
            raise FileNotFoundError(f"No archived execution at {timestamp!r}.")
        note_id = self._find_note_id(dir_id)
        current = self._read_note_content(note_id, _download_cls=_download_cls)
        if note is not None:
            current["note"] = note
        if locked is not None:
            current["locked"] = bool(locked)
        media = _media_cls(
            io.BytesIO(json.dumps(current).encode("utf-8")),
            mimetype="application/json",
            resumable=False,
        )
        if note_id:
            self.service.files().update(
                fileId=note_id, media_body=media, fields="id"
            ).execute()
        else:
            self.service.files().create(
                body={"name": EXECUTION_NOTE_FILENAME, "parents": [dir_id]},
                media_body=media,
                fields="id",
            ).execute()
        return current

    def purge_executions(self) -> list[str]:
        """Delete archived executions, skipping any locked one."""
        purged = []
        for ts in self.list_executions():
            if self.read_execution_note(ts).get("locked"):
                continue
            dir_id = self._archived_execution_folder_id(ts)
            if dir_id:
                gdrive.delete_file(self.service, dir_id, logger=self._logger)
            purged.append(ts)
        return purged

    def merge_from(
        self, other: "DriveStorageAdapter", timestamp: str
    ) -> list[PlacedArtifact]:
        """Absorb ``other``'s Drive-backed executions into this entity (dedup merge).

        See ``StorageAdapter.merge_from`` for the full contract. Everything
        moves by id (``move_to_folder``) — a Google Doc keeps its id and
        revision history throughout; no export/re-import happens. ``other``'s
        entity-tier files and folder are left untouched here (the caller
        removes them once notes are unioned).
        """
        moved: list[PlacedArtifact] = []
        archive_root_id = gdrive.ensure_subfolder(
            self.service, self.folder_id, ARCHIVE_DIRNAME, logger=self._logger
        )

        # Absorb the loser's current root execution (if any) under a fresh
        # timestamp subfolder.
        items = (
            self.service.files()
            .list(
                q=(
                    f"'{other.folder_id}' in parents and trashed = false "
                    f"and name != '{ARCHIVE_DIRNAME}'"
                ),
                fields="files(id, name)",
            )
            .execute()
            .get("files", [])
        )
        if items:
            dest_dir_id = gdrive.ensure_subfolder(
                self.service, archive_root_id, timestamp, logger=self._logger
            )
            for item in items:
                gdrive.move_to_folder(
                    self.service,
                    item["id"],
                    dest_dir_id,
                    current_parent_id=other.folder_id,
                    logger=self._logger,
                )
                moved.append(PlacedArtifact(name=item["name"], location=item["id"]))

        # Re-parent the loser's own already-archived executions, whole
        # subfolder by id; a timestamp collision is renamed with a suffix.
        # (Resolved directly here — one lookup — rather than via
        # ``other.list_executions()``/``other._archived_execution_folder_id``,
        # which would each re-derive the loser's archive root separately.)
        other_archive_root_id = gdrive._find_in_folder(
            self.service, ARCHIVE_DIRNAME, other.folder_id
        )
        subfolders = (
            self.service.files()
            .list(
                q=(
                    f"'{other_archive_root_id}' in parents and trashed = false "
                    f"and mimeType = '{gdrive.FOLDER_MIME}'"
                ),
                fields="files(id, name)",
            )
            .execute()
            .get("files", [])
            if other_archive_root_id
            else []
        )
        for sub in subfolders:
            ts, src_id = sub["name"], sub["id"]
            dest_ts = ts
            attempt = 0
            while gdrive._find_in_folder(self.service, dest_ts, archive_root_id):
                attempt += 1
                dest_ts = f"{ts}-merged" if attempt == 1 else f"{ts}-merged-{attempt}"
            gdrive.move_to_folder(
                self.service,
                src_id,
                archive_root_id,
                current_parent_id=other_archive_root_id,
                logger=self._logger,
            )
            if dest_ts != ts:
                self.service.files().update(
                    fileId=src_id, body={"name": dest_ts}, fields="id, name"
                ).execute()
            moved.append(PlacedArtifact(name=dest_ts, location=src_id))

        return moved


# __END__
