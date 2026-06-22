#!/usr/bin/env python3
"""Enumerate the input queue and completed jobs for the tracking view.

Input queue:  ``data/jobs/`` — JD PDFs; ``data/profiles/`` — profile screenshots.
Completed:    ``data/completed/jobs/``   — JDs, verified against Drive (4 artifacts).
              ``data/completed/profiles/`` — profiles, no Drive check (sheet only).
              ``data/completed/`` root    — legacy JD items (treated as JDs).
"""

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Optional

from jobjob.classify.classify import JD, LINKEDIN_PROFILE, classify_file
from services.application_metadata import (
    DEFAULT_STATUS,
    METADATA_FILENAME,
    ApplicationStatus,
    read_status,
)
from services.drive_service import list_application_folders

# A completed application folder holds README + JD + resume + cover letter.
_EXPECTED_ARTIFACTS = 4

# Cache for the completed list. It is expensive to build (one Drive lookup per
# item), and the underlying state only changes when a job moves a file into the
# completed tree — so we cache it and recompute only on explicit refresh or after
# move_to_completed invalidates it.
_completed_cache: Optional[dict] = None


def invalidate_completed_cache() -> None:
    """Drop the cached completed list so the next call recomputes (Drive checks)."""
    global _completed_cache
    _completed_cache = None


_COMPLETED_DIR = "completed"
_SUPPORTED_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg"})


def _queue_item(f: Path, subfolder: str) -> dict:
    return {
        "name": f.name,
        "path": str(f),
        "subfolder": subfolder,
        "extension": f.suffix.lower(),
    }


def list_queue(
    data_dir: Path, _classify: Callable[..., str] = classify_file
) -> list[dict]:
    """Return unprocessed input files from ``data/``.

    Files dropped directly in ``data/`` are classified (filename/text heuristics,
    no model call) and routed to the apply (``jobs``) or enrich (``profiles``)
    queue; unrecognized files are skipped. Files already sorted into the legacy
    ``data/jobs/`` and ``data/profiles/`` subdirs are still included (their
    location sets the type).

    Arguments:
        data_dir: Repo ``data/`` directory.
        _classify: Injection point for the file classifier (testing).
    Returns:
        List of dicts with: name, path, subfolder, extension.
    """
    items: list[dict] = []
    seen: set[str] = set()

    # Files dropped directly in data/ — classify (no query_service → heuristics).
    if data_dir.is_dir():
        for f in sorted(data_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            kind = _classify(f)
            subfolder = (
                "jobs"
                if kind == JD
                else "profiles" if kind == LINKEDIN_PROFILE else None
            )
            if subfolder is None:
                continue
            items.append(_queue_item(f, subfolder))
            seen.add(str(f))

    # Legacy sorted subdirs.
    for subdir in ("jobs", "profiles"):
        folder = data_dir / subdir
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if (
                f.suffix.lower() in _SUPPORTED_EXTENSIONS
                and f.is_file()
                and str(f) not in seen
            ):
                items.append(_queue_item(f, subdir))
    return items


# Application folder name: "YYYY-MM-DD - Company - Role". Company is the first
# segment after the date; the role is the remainder (may itself contain " - ").
_APP_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*-\s*(.+?)\s*-\s*(.+)$")
# A status marker the user (or the status endpoint's seed convention) prepends to
# the folder name, e.g. "APPLIED 2026-01-02 - Acme - Role". Matched
# case-sensitively at the start so a word like "Applied" inside a role title
# (e.g. "Applied Research") is not mistaken for the marker.
_STATUS_PREFIX_RE = re.compile(
    rf"^({'|'.join(s.value for s in ApplicationStatus)})\b[\s-]*"
)


def _parse_app_name(name: str) -> dict:
    """Split an application folder name into date/company/title (best-effort).

    Also detects a leading status marker (``APPLIED``, ``IGNORED``, …) and strips
    it before parsing, exposing it as ``prefix_status`` (None when absent).
    """
    match = _STATUS_PREFIX_RE.match(name)
    prefix_status = match.group(1) if match else None
    cleaned = _STATUS_PREFIX_RE.sub("", name) if match else name
    match = _APP_NAME_RE.match(cleaned)
    if not match:
        return {
            "date": "",
            "company": "",
            "title": cleaned,
            "prefix_status": prefix_status,
        }
    return {
        "date": match.group(1),
        "company": match.group(2),
        "title": match.group(3),
        "prefix_status": prefix_status,
    }


def _application_item(
    folder_name: str,
    *,
    path: str,
    status: str,
    drive,
    metadata_status: Optional[ApplicationStatus] = None,
    status_writable: bool = False,
) -> dict:
    """Build a completed-application item, including parsed date/company/title.

    ``app_status`` precedence: metadata.json > folder-name prefix > GENERATED.
    ``status`` (artifact completeness) is a separate axis and untouched.
    """
    parsed = _parse_app_name(folder_name)
    prefix_status = parsed.pop("prefix_status")
    # Dateless folders ("Company - Role") recover their date from the folder's
    # modification time — the application's effective last-processed date.
    if not parsed.get("date") and path:
        try:
            p = Path(path)
            if p.exists():
                parsed["date"] = datetime.fromtimestamp(p.stat().st_mtime).strftime(
                    "%Y-%m-%d"
                )
        except OSError:
            pass
    app_status = (
        metadata_status.value
        if metadata_status
        else prefix_status or DEFAULT_STATUS.value
    )
    return {
        "name": folder_name,
        "path": path,
        "folder_name": folder_name,
        "type": "jd",
        "status": status,
        "app_status": app_status,
        "status_writable": status_writable,
        "drive": drive,
        **parsed,
    }


def _application_items(
    applications_local_dir: Optional[Path],
    applications_folder_id: Optional[str],
    credentials_file: Optional[Path],
    token_file: Optional[Path],
    logger: logging.Logger,
) -> list[dict]:
    """Return completed-application items (type ``jd``).

    Prefers the **locally-synced** Drive applications mirror when configured (fast,
    no API calls): each subdirectory is one application, complete when it holds at
    least the expected number of artifacts. Falls back to the **Drive API** listing
    of the applications folder otherwise.
    """
    if applications_local_dir:
        local = Path(applications_local_dir).expanduser()
        if local.is_dir():
            # The mirror gives completeness/status without per-item API calls, but
            # not the Drive web-link. Recover links with a single folder listing
            # (matched by name); list_completed caches the result, so this is one
            # call per refresh. Falls back to no link if Drive is unavailable.
            links = {
                f["name"]: f
                for f in list_application_folders(
                    applications_folder_id, credentials_file, token_file, logger
                )
            }
            items = []
            for folder in sorted(
                (p for p in local.iterdir() if p.is_dir()), key=lambda p: p.name
            ):
                # metadata.json is bookkeeping, not an artifact — don't let it
                # tip an incomplete folder over the completeness threshold.
                complete = (
                    sum(1 for p in folder.iterdir() if p.name != METADATA_FILENAME)
                    >= _EXPECTED_ARTIFACTS
                )
                try:
                    metadata_status = read_status(folder)
                except (ValueError, OSError) as exc:
                    logger.warning("Unreadable metadata in %s: %s", folder, exc)
                    metadata_status = None
                match = links.get(folder.name)
                items.append(
                    _application_item(
                        folder.name,
                        path=str(folder),
                        status="completed" if complete else "error",
                        metadata_status=metadata_status,
                        status_writable=True,
                        drive=(
                            {
                                "found": True,
                                "complete": complete,
                                "file_count": 0,
                                "folder_id": match["folder_id"],
                                "web_link": match["web_link"],
                                "error": None,
                            }
                            if match
                            else None
                        ),
                    )
                )
            return items
        logger.warning(
            "APPLICATIONS_LOCAL_DIR %s not found; using the Drive API.", local
        )

    # Drive fallback: list the application folders under the applications root.
    folders = list_application_folders(
        applications_folder_id, credentials_file, token_file, logger
    )
    return [
        _application_item(
            folder["name"],
            path="",
            status="completed",
            drive={
                "found": True,
                "complete": True,
                "file_count": 0,
                "folder_id": folder["folder_id"],
                "web_link": folder["web_link"],
                "error": None,
            },
        )
        for folder in folders
    ]


# Completed-profile name: "<created8>-<processed8>-<Company>-<Person>" (Company and
# Person are PascalCase with no hyphens, so exactly four parts).
_PROFILE_NAME_RE = re.compile(r"^(\d{8})-(\d{8})-(.+?)-(.+)$")


def _fmt_yyyymmdd(value: str) -> str:
    """Format an 8-digit ``yyyymmdd`` as ``yyyy-mm-dd`` (else return it unchanged)."""
    return (
        f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
        if value.isdigit() and len(value) == 8
        else value
    )


def _profile_completed_item(f: Path, sheet_url: Optional[str] = None) -> dict:
    """Build a completed-item dict for a profile file.

    Parses the structured filename into created/processed dates, company, and person;
    a ``<stem>.json`` sidecar (written at enrich time) is preferred for the original
    spaced company/person names. A profile's record also lives in the contacts Google
    Sheet (in Drive); when the sheet id is known, link to it via ``drive.web_link`` so
    the UI can offer a "Sheet" link. Names that don't match the scheme (legacy files)
    degrade to blank fields.
    """
    company = person = date_created = date_processed = ""
    match = _PROFILE_NAME_RE.match(f.stem)
    if match:
        date_created = _fmt_yyyymmdd(match.group(1))
        date_processed = _fmt_yyyymmdd(match.group(2))
        company, person = match.group(3), match.group(4)

    sidecar = f.with_suffix(".json")
    if sidecar.is_file():
        try:
            record = json.loads(sidecar.read_text(encoding="utf-8"))
            company = record.get("company") or company
            person = record.get("name") or person
            date_created = record.get("date_created") or date_created
            date_processed = record.get("date_processed") or date_processed
        except (ValueError, OSError):
            pass  # Fall back to the filename-derived values.

    return {
        "name": f.name,
        "path": str(f),
        "folder_name": f.stem,
        "type": "profile",
        "status": "completed",
        "company": company,
        "person": person,
        "date_created": date_created,
        "date_processed": date_processed,
        "drive": (
            {
                "found": True,
                "complete": True,
                "file_count": 0,
                "folder_id": None,
                "web_link": sheet_url,
                "error": None,
            }
            if sheet_url
            else None
        ),
    }


def list_completed(
    data_dir: Path,
    applications_folder_id: Optional[str],
    credentials_file: Optional[Path],
    token_file: Optional[Path],
    logger: logging.Logger | None = None,
    force_refresh: bool = False,
    applications_local_dir: Optional[Path] = None,
    linkedin_sheet_id: Optional[str] = None,
    _classify: Callable[..., str] = classify_file,
) -> list[dict]:
    """Return completed applications and completed profiles.

    **Applications** (type ``jd``) come from the locally-synced Drive mirror
    (``applications_local_dir``) when configured, else the Drive API — so they
    reflect the actual Drive state regardless of how a job was run. **Profiles**
    (type ``profile``) come from ``completed/profiles/`` plus any LinkedIn profile
    screenshots in the legacy flat ``completed/`` root (classified), with no Drive
    check — their record lives in the Google Sheet.

    The result is cached (see ``_completed_cache``); a cached value is returned
    unless ``force_refresh`` is set or the cache was invalidated by a completed
    job. The cache is keyed by ``data_dir`` so a settings change recomputes.

    Arguments:
        data_dir: Repo ``data/`` directory (source of completed *profiles*).
        applications_folder_id: Drive applications-root folder id (Drive fallback).
        credentials_file: Google OAuth credentials path (Drive fallback).
        token_file: Pickled token path (Drive fallback).
        logger: Optional logger.
        force_refresh: Bypass the cache and recompute.
        applications_local_dir: Local synced Drive applications mirror; preferred
            source for completed applications when set.
    Returns:
        List of dicts with: name, path, folder_name, type, status, drive.
    """
    global _completed_cache
    _logger = logger or logging.getLogger(__name__)
    cache_key = str(data_dir)
    if (
        not force_refresh
        and _completed_cache is not None
        and _completed_cache["key"] == cache_key
    ):
        return _completed_cache["items"]

    # Completed applications — synced mirror or Drive (authoritative).
    items: list[dict] = _application_items(
        applications_local_dir,
        applications_folder_id,
        credentials_file,
        token_file,
        _logger,
    )

    # Completed profiles — local only (the completed/profiles/ subdir plus any
    # profiles found in the legacy flat completed/ root), sorted by name.
    completed_root = data_dir / _COMPLETED_DIR
    if completed_root.is_dir():

        def _supported(folder: Path) -> list[Path]:
            if not folder.is_dir():
                return []
            return [
                f
                for f in sorted(folder.iterdir())
                if f.suffix.lower() in _SUPPORTED_EXTENSIONS and f.is_file()
            ]

        sheet_url = (
            f"https://docs.google.com/spreadsheets/d/{linkedin_sheet_id}"
            if linkedin_sheet_id
            else None
        )
        profile_files = [
            f for f in _supported(completed_root) if _classify(f) == LINKEDIN_PROFILE
        ]
        profile_files.extend(_supported(completed_root / "profiles"))
        for f in sorted(profile_files, key=lambda p: p.name):
            items.append(_profile_completed_item(f, sheet_url))

    _completed_cache = {"key": cache_key, "items": items}
    return items


def move_to_completed(
    source: Path,
    data_dir: Path,
    folder_name: str,
    item_type: str = "jd",
    logger: logging.Logger | None = None,
) -> Path:
    """Move ``source`` into the appropriate completed subdirectory.

    JDs go to ``data/completed/jobs/<folder_name><ext>`` (renamed to match the
    Drive folder). Profiles go to ``data/completed/profiles/<original_name>``
    (filename preserved — the sheet is the record of what was processed).

    Arguments:
        source: Input file to move.
        data_dir: Repo ``data/`` directory.
        folder_name: Drive folder name for JDs; ignored for profiles (original
            filename is kept).
        item_type: ``"jd"`` or ``"profile"``.
        logger: Optional logger.
    Returns:
        The new path.
    """
    _logger = logger or logging.getLogger(__name__)
    if item_type == "profile":
        dest_dir = data_dir / _COMPLETED_DIR / "profiles"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name
    else:
        dest_dir = data_dir / _COMPLETED_DIR / "jobs"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{folder_name}{source.suffix}"
    source.rename(dest)
    _logger.info("Moved %s → %s", source, dest)
    # The completed set just changed; force the next list_completed to recompute.
    invalidate_completed_cache()
    return dest
