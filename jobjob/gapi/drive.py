#!/usr/bin/env python3
"""Google Drive operations: application folders, template copy, export, upload.

Each function takes an already-built Drive ``service`` so it can be unit-tested
with a mock. Config (parent folder, template id) is passed in, not read from env.
"""

import io
import logging
import re
from pathlib import Path
from typing import Any, Optional

from googleapiclient.http import (
    MediaFileUpload,
    MediaIoBaseDownload,
    MediaIoBaseUpload,
)

FOLDER_MIME = "application/vnd.google-apps.folder"
GDOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"

# Pre-compiled patterns for normalizing display/folder names.
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^0-9A-Za-z]+")


def sanitize_name(value: str) -> str:
    """Return ``value`` reduced to alphanumerics, spaces, hyphens, underscores.

    NOTE: collapses runs of whitespace so dropped punctuation (e.g. "Data & AI")
        does not leave double spaces ("Data  AI").
    """
    kept = "".join(c for c in value if c.isalnum() or c in " -_")
    return _WHITESPACE_RE.sub(" ", kept).strip()


def pascal_case(value: str) -> str:
    """Return ``value`` as PascalCase (e.g. "Isomorphic Labs" -> "IsomorphicLabs").

    NOTE: capitalizes the first letter of each word but preserves existing internal
        capitals (so "ML Engineer" -> "MLEngineer").
    """
    words = _NON_ALNUM_RE.split(value)
    return "".join(word[:1].upper() + word[1:] for word in words if word)


def application_folder_name(company: str, role: str) -> str:
    """Return the ``Company - Role`` application folder name.

    NOTE: no date prefix — reprocessing the same role overwrites in place rather
        than creating a dated duplicate (the application's date is recovered from
        the folder's modification time for display). This assumes one application
        per role+company.
    """
    return f"{sanitize_name(company)} - {sanitize_name(role)}"


def find_application_folder(
    service: Any,
    company: str,
    role: str,
    parent_id: Optional[str] = None,
) -> Optional[str]:
    """Return the id of an existing ``company``/``role`` folder, else None."""
    name = application_folder_name(company, role)
    query = f"name = '{name}' and mimeType = '{FOLDER_MIME}' and trashed = false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = (
        service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    )
    existing = results.get("files", [])
    return existing[0]["id"] if existing else None


def _find_in_folder(service: Any, name: str, folder_id: str) -> Optional[str]:
    """Return the id of a non-trashed file named ``name`` in ``folder_id``, else None.

    NOTE: artifacts are updated in place (not deleted + recreated) so the Drive file
        id — and thus the document's revision history and shareable link — survives a
        reprocess.
    """
    query = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    results = (
        service.files().list(q=query, fields="files(id, name)", pageSize=1).execute()
    )
    files = results.get("files", [])
    return files[0]["id"] if files else None


def _reset_doc_to_template(
    service: Any,
    doc_id: str,
    template_id: str,
    logger: logging.Logger,
    _download_cls: Any = MediaIoBaseDownload,
    _upload_cls: Any = MediaIoBaseUpload,
) -> None:
    """Reset an existing resume Google Doc to the pristine template content in place.

    Exports the template (a Google Doc) as DOCX bytes and re-imports them onto the
    existing ``doc_id`` via ``files().update``. The doc keeps its id (preserving
    revision history) but its content is reset to the clean template, ready to be
    re-tailored. Used on reprocess so the resume's history survives.
    """
    buffer = io.BytesIO()
    request = service.files().export_media(fileId=template_id, mimeType=DOCX_MIME)
    downloader = _download_cls(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    media = _upload_cls(buffer, mimetype=DOCX_MIME, resumable=False)
    service.files().update(fileId=doc_id, media_body=media, fields="id").execute()
    logger.info("Reset resume to template in place: %s", doc_id)


def create_application_folder(
    service: Any,
    company: str,
    role: str,
    parent_id: Optional[str] = None,
    logger: logging.Logger | None = None,
) -> str:
    """Create (or reuse) the application folder and return its id.

    Arguments:
        service: Drive service client.
        company: Company name.
        role: Role title.
        parent_id: Parent folder id (the applications root), if any.
        logger: Optional logger for injection.
    Returns:
        The folder id.
    """
    _logger = logger or logging.getLogger(__name__)
    name = application_folder_name(company, role)

    existing_id = find_application_folder(service, company, role, parent_id)
    if existing_id:
        _logger.info("Reusing folder: %s", name)
        return existing_id  # EARLY EXIT: reuse.

    metadata = {"name": name, "mimeType": FOLDER_MIME}
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = (
        service.files().create(body=metadata, fields="id, name, webViewLink").execute()
    )
    _logger.info("Created folder: %s", folder["name"])
    return folder["id"]


def copy_resume_template(
    service: Any,
    folder_id: str,
    template_id: str,
    name: str = "Resume",
    logger: logging.Logger | None = None,
) -> str:
    """Place a pristine copy of the resume template in ``folder_id``, return its id.

    On a fresh folder the template is copied. On reprocess (an existing resume of the
    same ``name`` is present) the existing doc is reset to the template content in
    place so its id and revision history survive; either way the caller re-tailors the
    returned doc.

    Arguments:
        service: Drive service client.
        folder_id: Destination folder id.
        template_id: Google Doc id of the resume template.
        name: Name for the copied document.
        logger: Optional logger for injection.
    Returns:
        The document id (existing on reprocess, new on a fresh copy).
    Raises:
        ValueError: If ``template_id`` is missing.
    """
    _logger = logger or logging.getLogger(__name__)
    if not template_id:
        raise ValueError("template_id is required (set RESUME_TEMPLATE_ID).")

    existing_id = _find_in_folder(service, name, folder_id)
    if existing_id:
        _reset_doc_to_template(service, existing_id, template_id, _logger)
        return existing_id  # EARLY EXIT: reset in place, history preserved.

    copied = (
        service.files()
        .copy(
            fileId=template_id,
            body={"name": name, "parents": [folder_id]},
            fields="id, name, webViewLink",
        )
        .execute()
    )
    _logger.info("Copied resume: %s", copied["name"])
    return copied["id"]


def export_doc_as_pdf(
    service: Any,
    doc_id: str,
    output_path: Path,
    logger: logging.Logger | None = None,
    _downloader_cls: Any = MediaIoBaseDownload,
) -> Path:
    """Export a Google Doc as a PDF to ``output_path`` and return that path."""
    _logger = logger or logging.getLogger(__name__)
    output_path = Path(output_path)
    request = service.files().export_media(fileId=doc_id, mimeType=PDF_MIME)
    with open(output_path, "wb") as handle:
        downloader = _downloader_cls(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    _logger.info("Exported PDF: %s", output_path)
    return output_path


def upload_file(
    service: Any,
    file_path: Path,
    folder_id: str,
    name: str,
    mimetype: str = PDF_MIME,
    logger: logging.Logger | None = None,
    _media_cls: Any = MediaFileUpload,
) -> str:
    """Upload ``file_path`` into ``folder_id`` as ``name``, updating any existing.

    Updates the existing file's content in place (same id/link) when one of ``name``
    is already present, else creates it.
    """
    _logger = logger or logging.getLogger(__name__)
    media = _media_cls(str(file_path), mimetype=mimetype)
    existing_id = _find_in_folder(service, name, folder_id)
    if existing_id:
        updated = (
            service.files()
            .update(fileId=existing_id, media_body=media, fields="id, name")
            .execute()
        )
        _logger.info("Updated in place: %s", name)
        return updated["id"]
    uploaded = (
        service.files()
        .create(
            body={"name": name, "parents": [folder_id]},
            media_body=media,
            fields="id, name, webViewLink",
        )
        .execute()
    )
    _logger.info("Uploaded: %s", uploaded["name"])
    return uploaded["id"]


def upload_docx_as_google_doc(
    service: Any,
    docx_path: Path,
    folder_id: str,
    name: str,
    logger: logging.Logger | None = None,
    _media_cls: Any = MediaFileUpload,
) -> str:
    """Upload a .docx into ``folder_id`` converting it to a Google Doc.

    Updates the existing Google Doc of ``name`` in place when present — re-importing
    the docx onto the same doc id preserves its revision history and link — else
    creates a new Google Doc.
    """
    _logger = logger or logging.getLogger(__name__)
    media = _media_cls(str(docx_path), mimetype=DOCX_MIME)
    existing_id = _find_in_folder(service, name, folder_id)
    if existing_id:
        # Re-import onto the existing doc; it stays a Google Doc (no mimeType in body).
        updated = (
            service.files()
            .update(fileId=existing_id, media_body=media, fields="id, name")
            .execute()
        )
        _logger.info("Updated Google Doc in place: %s", name)
        return updated["id"]
    metadata = {"name": name, "parents": [folder_id], "mimeType": GDOC_MIME}
    uploaded = (
        service.files()
        .create(body=metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )
    _logger.info("Uploaded as Google Doc: %s", uploaded["name"])
    return uploaded["id"]


# __END__
