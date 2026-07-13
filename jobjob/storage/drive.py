#!/usr/bin/env python3
"""Drive-backed ``StorageAdapter``: the entity root is a Drive folder id.

Used for Google-Docs-managed artifacts (résumé/cover/README as gdocs) and for
plain files placed alongside them in the same Drive folder (the JD copy).
Archive/promote move by id (``jobjob.gapi.drive.move_to_folder``) rather than
export/re-import, so a Google Doc's revision history survives (design D2/D7).
"""

import logging
import mimetypes
from pathlib import Path
from typing import Any, Optional

from jobjob.gapi import drive as gdrive
from jobjob.storage.base import ARCHIVE_DIRNAME, PlacedArtifact


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


# __END__
