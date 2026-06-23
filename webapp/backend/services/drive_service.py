#!/usr/bin/env python3
"""Check Google Drive application folder state for the tracking view.

Kept intentionally thin: builds a Drive service using the existing
``jobjob.loader.auth`` flow, then queries for a named folder and its contents.
Returns a plain dict so callers need no Drive SDK knowledge.
"""

import logging
from pathlib import Path
from typing import Any, Optional

_EXPECTED_ARTIFACT_COUNT = 4  # README, JD, resume, cover letter


def _build_drive(
    credentials_file: Optional[Path],
    token_file: Optional[Path],
    logger: logging.Logger,
) -> Optional[Any]:
    """Return an authenticated Drive service, or None if credentials are absent."""
    if not credentials_file or not token_file:
        return None
    token_path = Path(token_file).expanduser().resolve()
    if not token_path.is_file():
        logger.debug("Drive token not found at %s; skipping Drive check.", token_path)
        return None
    try:
        from jobjob.gapi.service import build_drive_service
        from jobjob.loader.auth import get_google_credentials

        creds = get_google_credentials(
            credentials_file=Path(credentials_file).expanduser().resolve(),
            token_file=token_path,
        )
        return build_drive_service(creds)
    except Exception as exc:
        logger.warning("Could not build Drive service: %s", exc)
        return None


def prewarm_credentials(
    credentials_file: Optional[Path],
    token_file: Optional[Path],
    logger: logging.Logger | None = None,
) -> bool:
    """Build the Drive service once, up front.

    Any expired-token refresh (which rewrites the token file) happens here,
    serially, so that concurrent ``check_folder`` calls afterwards only read an
    already-valid token and never race to refresh/rewrite it.

    Returns:
        True if an authenticated service was obtained, else False.
    """
    _logger = logger or logging.getLogger(__name__)
    return _build_drive(credentials_file, token_file, _logger) is not None


def check_folder(
    folder_name: str,
    applications_folder_id: Optional[str],
    credentials_file: Optional[Path],
    token_file: Optional[Path],
    logger: logging.Logger | None = None,
) -> dict:
    """Check whether ``folder_name`` exists in Drive with all expected artifacts.

    Arguments:
        folder_name: Expected Drive folder name (``YYYY-MM-DD - Company - Role``).
        applications_folder_id: Parent Drive folder id.
        credentials_file: Path to Google OAuth credentials JSON.
        token_file: Path to the pickled token.
        logger: Optional logger.
    Returns:
        Dict with keys: found (bool), file_count (int), folder_id (str|None),
        web_link (str|None), complete (bool), error (str|None).
    """
    _logger = logger or logging.getLogger(__name__)
    result: dict = {
        "found": False,
        "file_count": 0,
        "folder_id": None,
        "web_link": None,
        "complete": False,
        "error": None,
    }

    if not applications_folder_id:
        result["error"] = "APPLICATIONS_OUTPUT_DRIVE_ID not configured"
        return result

    service = _build_drive(credentials_file, token_file, _logger)
    if service is None:
        result["error"] = "Drive not authenticated (delete token.pickle to re-auth)"
        return result

    try:
        safe_name = folder_name.replace("'", "\\'")
        query = (
            f"name = '{safe_name}' "
            f"and '{applications_folder_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        resp = (
            service.files()
            .list(q=query, fields="files(id,name,webViewLink)", pageSize=2)
            .execute()
        )
        folders = resp.get("files", [])
        if not folders:
            result["error"] = "Drive folder not found"
            return result

        folder = folders[0]
        result["found"] = True
        result["folder_id"] = folder["id"]
        result["web_link"] = folder.get("webViewLink")

        files_resp = (
            service.files()
            .list(
                q=f"'{folder['id']}' in parents and trashed = false",
                fields="files(id,name,mimeType)",
                pageSize=20,
            )
            .execute()
        )
        file_count = len(files_resp.get("files", []))
        result["file_count"] = file_count
        result["complete"] = file_count >= _EXPECTED_ARTIFACT_COUNT
        if not result["complete"]:
            result["error"] = (
                f"Incomplete: {file_count}/{_EXPECTED_ARTIFACT_COUNT} artifacts found"
            )
    except Exception as exc:
        result["error"] = f"Drive API error: {exc}"

    return result


def list_application_folders(
    applications_folder_id: Optional[str],
    credentials_file: Optional[Path],
    token_file: Optional[Path],
    logger: logging.Logger | None = None,
) -> list[dict]:
    """List the application subfolders directly under the applications root.

    Each subfolder is one completed application. Used as the source for the
    completed-applications list when no local synced mirror is configured.

    Arguments:
        applications_folder_id: Parent Drive folder id.
        credentials_file: Path to the OAuth client-secrets JSON.
        token_file: Path to the pickled token.
        logger: Optional logger.
    Returns:
        List of dicts with keys: name, folder_id, web_link. Empty on any failure.
    """
    _logger = logger or logging.getLogger(__name__)
    if not applications_folder_id:
        return []
    service = _build_drive(credentials_file, token_file, _logger)
    if service is None:
        return []

    folders: list[dict] = []
    query = (
        f"'{applications_folder_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    try:
        page_token = None
        while True:
            resp = (
                service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id,name,webViewLink)",
                    pageSize=100,
                    pageToken=page_token,
                )
                .execute()
            )
            for folder in resp.get("files", []):
                folders.append(
                    {
                        "name": folder["name"],
                        "folder_id": folder["id"],
                        "web_link": folder.get("webViewLink"),
                    }
                )
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    except Exception as exc:
        _logger.warning("Could not list application folders: %s", exc)
    return folders
