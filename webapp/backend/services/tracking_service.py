#!/usr/bin/env python3
"""Enumerate the input queue and completed jobs for the tracking view.

Input queue:  ``data/jobs/`` — JD PDFs; ``data/profiles/`` — profile screenshots.
Completed:    ``data/completed/jobs/``   — JDs, verified against Drive (4 artifacts).
              ``data/completed/profiles/`` — profiles, no Drive check (sheet only).
              ``data/completed/`` root    — legacy JD items (treated as JDs).
"""

import hashlib
import json
import logging
import re
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Optional

from jobjob.classify.classify import JD, LINKEDIN_PROFILE, classify_file
from jobjob.storage.base import ARCHIVE_DIRNAME
from jobjob.storage.local import LocalStorageAdapter
from jobjob.structure.dedup import dedup_signal
from services import application_source
from services.application_metadata import (
    DEFAULT_STATUS,
    METADATA_FILENAME,
    ApplicationStatus,
    entity_id_from_metadata,
    read_metadata,
    status_from_metadata,
)
from services.drive_service import list_application_folders

# A completed application folder holds README + JD + resume + cover letter.
_EXPECTED_ARTIFACTS = 4

# Bookkeeping/tiers that are never counted as execution artifacts: metadata.json
# (entity tier) and source.json (source tier) describe the application across
# every execution, not one build's output; archive/ (application-identity phase
# 2) holds *superseded* executions' artifacts, not the current one. Excluding
# all three keeps the completeness count measuring only the primary execution's
# root artifacts, exactly as metadata.json was already carved out.
_NON_ARTIFACT_NAMES = frozenset(
    {METADATA_FILENAME, application_source.SOURCE_FILENAME, ARCHIVE_DIRNAME}
)

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

_SUMMARY_FILENAME = "summary.json"


def _read_insights(folder: Path, logger: logging.Logger) -> dict:
    """Read the fit block and ATS coverage from a folder's ``summary.json``.

    Missing, unreadable, or pre-insight summaries degrade to empty values —
    older applications must still list.
    """
    empty = {"fit": None, "ats_coverage": None}
    summary_path = Path(folder, _SUMMARY_FILENAME)
    if not summary_path.is_file():
        return empty
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Unreadable summary in %s: %s", folder, exc)
        return empty
    fit = summary.get("fit")
    return {
        "fit": fit if isinstance(fit, dict) else None,
        "ats_coverage": summary.get("ats_coverage"),
    }


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
# (e.g. "Applied Research") is not mistaken for the marker. "GENERATED" is kept
# as a legacy alias for "BUILT" (pre-rename folders) and normalized below.
_STATUS_PREFIX_RE = re.compile(
    rf"^({'|'.join([*(s.value for s in ApplicationStatus), 'GENERATED'])})\b[\s-]*"
)


def _parse_app_name(name: str) -> dict:
    """Split an application folder name into date/company/title (best-effort).

    Also detects a leading status marker (``APPLIED``, ``IGNORED``, …) and strips
    it before parsing, exposing it as ``prefix_status`` (None when absent). A
    legacy ``GENERATED`` marker is normalized to ``BUILT``.
    """
    match = _STATUS_PREFIX_RE.match(name)
    prefix_status = match.group(1) if match else None
    if prefix_status == "GENERATED":
        prefix_status = ApplicationStatus.BUILT.value
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
    note_count: int = 0,
    insights: Optional[dict] = None,
    entity_id: Optional[str] = None,
    posting_url: Optional[str] = None,
    execution_count: int = 0,
    dedup_company: Optional[str] = None,
    dedup_role: Optional[str] = None,
) -> dict:
    """Build a completed-application item, including parsed date/company/title.

    ``app_status`` precedence: metadata.json > folder-name prefix > BUILT.
    ``status`` (artifact completeness) is a separate axis and untouched.
    ``note_count`` is the number of changelog notes recorded for the application.
    ``insights`` carries the summary.json fit block + ATS coverage (mirror only).
    ``entity_id`` (application-identity, phase 1) is read from metadata.json; None
    marks a legacy folder (joins by folder name — see ``run_matches_application``).
    ``posting_url`` (autofill-apply-wiring) is the source tier's ``web_uri``, or
    None when absent — the webapp's Apply row action is gated on this being set.
    ``execution_count`` (application-identity, phase 6b) is the number of
    archived (superseded) executions under ``archive/`` — 0 for most
    applications (only a re-build with "archive instead of overwrite" creates
    one).
    ``dedup_company``/``dedup_role`` (application-identity, phase 6c) are the
    source tier's parse-once ``company``/``role`` fields, when known — the
    dedup signal prefers them (they survive a folder rename) over the
    folder-name-parsed fallback, which only a legacy (no ``source.json``)
    folder ever falls back to. ``possible_duplicate``/``duplicate_group`` are
    always seeded False/None here; ``list_completed`` sets them across the
    full list (grouping needs every item, not just this one).
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
    # application-identity, phase 6c: normalized company+role dedup signal.
    # An empty signal (blank company/role both sides) never groups.
    signal = dedup_signal(
        dedup_company or parsed.get("company"), dedup_role or parsed.get("title")
    )
    return {
        "name": folder_name,
        "path": path,
        "folder_name": folder_name,
        "type": "jd",
        "status": status,
        "app_status": app_status,
        "status_writable": status_writable,
        "note_count": note_count,
        "drive": drive,
        "entity_id": entity_id,
        "posting_url": posting_url,
        "execution_count": execution_count,
        "dedup_signal": signal or None,
        "possible_duplicate": False,
        "duplicate_group": None,
        **(insights or {"fit": None, "ats_coverage": None}),
        **parsed,
    }


def run_matches_application(run: Mapping, item: Mapping) -> bool:
    """Return whether a run record and a completed-application item are the same.

    Id-preferring join (application-identity, phase 1): prefer ``entity_id``
    equality when both sides carry one — this is what lets the match survive a
    folder rename since the run happened. Falls back to ``folder_name`` equality
    (today's exact behavior) when either side lacks an id, i.e. a legacy record.
    """
    run_id = run.get("entity_id")
    item_id = item.get("entity_id")
    if run_id and item_id:
        return run_id == item_id
    return run.get("folder_name") == item.get("folder_name")


def _flag_duplicates(items: list[dict]) -> None:
    """Flag possible-duplicate applications in place (application-identity, D3).

    Groups completed *application* items (``type == "jd"``) by their
    normalized company+role ``dedup_signal``; any group with more than one
    member is flagged ``possible_duplicate = True`` with a shared
    ``duplicate_group`` id. The id is a short hash of the signal purely as a
    compact, stable-within-this-listing key for the UI to group rows by — it
    is recomputed fresh on every call, never persisted (the normalized signal
    itself is the substance, per design D3). Items with no signal (blank
    company/role — typically a pre-identity legacy folder) are never grouped.
    Never auto-merges anything; this only sets flags for the UI to surface.
    """
    by_signal: dict[str, list[dict]] = {}
    for item in items:
        signal = item.get("dedup_signal")
        if item.get("type") != "jd" or not signal:
            continue
        by_signal.setdefault(signal, []).append(item)
    for signal, group in by_signal.items():
        if len(group) < 2:
            continue
        group_id = hashlib.sha256(signal.encode("utf-8")).hexdigest()[:8]
        for item in group:
            item["possible_duplicate"] = True
            item["duplicate_group"] = group_id


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
                # metadata.json/source.json/archive/ are bookkeeping or superseded
                # executions, not this execution's artifacts — don't let them tip
                # an incomplete folder over the completeness threshold (or mask
                # one that's actually incomplete).
                complete = (
                    sum(
                        1 for p in folder.iterdir() if p.name not in _NON_ARTIFACT_NAMES
                    )
                    >= _EXPECTED_ARTIFACTS
                )
                try:
                    meta = read_metadata(folder)
                    metadata_status = status_from_metadata(meta)
                except (ValueError, OSError) as exc:
                    logger.warning("Unreadable metadata in %s: %s", folder, exc)
                    meta, metadata_status = {}, None
                note_count = len(meta.get("notes") or [])
                match = links.get(folder.name)
                # application-identity phase 1's source tier (source.json);
                # tolerant read — a missing/legacy folder degrades to {}, same
                # posture as application_source.read_source itself. Read once
                # and reuse for both the posting URL and the dedup signal.
                source = application_source.read_source(folder)
                posting_url = source.get("web_uri")
                # application-identity phase 6b: count of archived (superseded)
                # executions — surfaced in the Applications table so a user
                # knows there's history to promote/note/lock/purge.
                execution_count = len(LocalStorageAdapter(folder).list_executions())
                items.append(
                    _application_item(
                        folder.name,
                        path=str(folder),
                        status="completed" if complete else "error",
                        metadata_status=metadata_status,
                        status_writable=True,
                        note_count=note_count,
                        insights=_read_insights(folder, logger),
                        entity_id=entity_id_from_metadata(meta),
                        posting_url=posting_url,
                        execution_count=execution_count,
                        dedup_company=source.get("company"),
                        dedup_role=source.get("role"),
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
            "APPLICATIONS_OUTPUT_DIR %s not found; using the Drive API.", local
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

    # application-identity, phase 6c: flag possible duplicates across the full
    # application list (grouping needs every item at once, not just one).
    _flag_duplicates(items)

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
