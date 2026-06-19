#!/usr/bin/env python3
"""Enrich workflow: parse a LinkedIn profile screenshot and append it to the sheet."""

import dataclasses as dcs
import json
import logging
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, Optional

from jobjob.ailib.session import AIClient
from jobjob.classify.classify import LINKEDIN_PROFILE, classify_file
from jobjob.enrich.parse import parse_profile
from jobjob.gapi.drive import pascal_case
from jobjob.gapi.service import build_sheets_service
from jobjob.gapi.sheets import DEFAULT_SHEET_NAME, append_profile
from jobjob.loader.auth import get_google_credentials

# The capture date embedded in a screencapture filename: "...-YYYY-MM-DD-HH_MM_SS".
# Anchored on the time suffix so a digit run in the profile slug is not mistaken for it.
_FILENAME_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})-\d{2}_\d{2}_\d{2}")


def enrich_profile(
    profile_pdf: Path,
    query_service: AIClient,
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = DEFAULT_SHEET_NAME,
    use_cache: bool = True,
    dry_run: bool = False,
    logger: logging.Logger | None = None,
    _credentials_loader: Callable[..., Any] = get_google_credentials,
    _sheets_builder: Callable[..., Any] = build_sheets_service,
) -> dict:
    """Parse a profile screenshot and (unless dry-run) append it to the sheet.

    Arguments:
        profile_pdf: Path to the LinkedIn profile screenshot PDF.
        query_service: AIClient used to parse the profile.
        spreadsheet_id: Contacts spreadsheet id (required unless ``dry_run``).
        sheet_name: Worksheet/tab name.
        use_cache: Whether the model call consults/populates the response cache.
        dry_run: If True, parse without writing to the sheet.
        logger: Optional logger for injection.
        _credentials_loader: Injection point for Google credentials (testing).
        _sheets_builder: Injection point for the Sheets service builder (testing).
    Returns:
        A results dict with the parsed profile (and the appended row when written).
    Raises:
        ValueError: If writing is requested without a spreadsheet id.
    """
    _logger = logger or logging.getLogger(__name__)
    profile = parse_profile(Path(profile_pdf), query_service, use_cache=use_cache)
    results = {"profile": dcs.asdict(profile)}
    _logger.info(
        "Parsed profile: %s / %s @ %s", profile.name, profile.role, profile.company
    )

    if dry_run:
        _logger.info("Dry run: not writing to the sheet")
        return results  # EARLY EXIT: preview only.

    if not spreadsheet_id:
        raise ValueError("A spreadsheet id is required (set LINKEDIN_SHEET_ID or --dry-run).")

    creds = _credentials_loader()
    service = _sheets_builder(creds)
    results["row"] = append_profile(
        service, spreadsheet_id, profile, sheet_name=sheet_name, logger=_logger
    )
    return results


def extract_filename_date(filename: str) -> Optional[date]:
    """Return the capture date embedded in a screencapture filename, else None.

    Matches the ``-YYYY-MM-DD-HH_MM_SS`` suffix of LinkedIn screenshot filenames
    (e.g. ``screencapture-linkedin-in-<slug>-2026-05-21-09_33_56.pdf``).
    """
    matches = _FILENAME_DATE_RE.findall(filename)
    if not matches:
        return None
    year, month, day = matches[-1]
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def completed_profile_name(
    name: str,
    company: str,
    *,
    created: date,
    processed: Optional[date] = None,
) -> str:
    """Return the ``<created>-<processed>-<Company>-<Person>`` completed-profile name.

    Encodes the contact's created date (from the source filename, else the file's
    mtime), the processing date, the company, and the person — making connections
    easy to track. Dates are 8-digit ``yyyymmdd``; the company and person are
    PascalCase (no internal hyphens), so the name always splits into exactly four
    hyphen-delimited parts. ``processed`` defaults to today.
    """
    processed = processed or date.today()
    return "-".join(
        (
            created.strftime("%Y%m%d"),
            processed.strftime("%Y%m%d"),
            pascal_case(company) or "Unknown",
            pascal_case(name) or "Unknown",
        )
    )


def write_profile_sidecar(
    dest: Path, profile: dict, created: date, processed: date
) -> Path:
    """Write a JSON sidecar beside a completed profile with its parsed fields + dates.

    The PascalCase filename is lossy; the sidecar preserves the original (spaced)
    parsed values so the dashboard can display them, and is the local, queryable
    record of the contact. Returns the sidecar path.
    """
    record = {**profile, "date_created": created.isoformat(), "date_processed": processed.isoformat()}
    sidecar = dest.with_suffix(".json")
    sidecar.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return sidecar


def move_completed_profile(
    src: Path,
    data_dir: Path,
    profile_name: str,
    logger: logging.Logger | None = None,
) -> Path:
    """Move an enriched profile into ``<data_dir>/completed/profiles/<name><ext>``.

    Called on a successful enrichment (the profile is in the sheet) so it leaves
    the input area — the enrich analog of ``apply.move_completed_jd``.

    Arguments:
        src: The processed profile screenshot file.
        data_dir: Root holding ``profiles/``/``completed/``.
        profile_name: Base name for the moved file (see ``completed_profile_name``).
        logger: Optional logger for injection.
    Returns:
        The new path.
    """
    _logger = logger or logging.getLogger(__name__)
    src = Path(src)
    dest_dir = Path(data_dir) / "completed" / "profiles"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{profile_name}{src.suffix}"
    src.rename(dest)
    _logger.info("Moved profile to completed: %s", dest)
    return dest


def enrich_inputs(
    input_path: Path,
    query_service: AIClient,
    spreadsheet_id: Optional[str] = None,
    sheet_name: str = DEFAULT_SHEET_NAME,
    use_cache: bool = True,
    dry_run: bool = False,
    data_dir: Optional[Path] = None,
    logger: logging.Logger | None = None,
    _credentials_loader: Callable[..., Any] = get_google_credentials,
    _sheets_builder: Callable[..., Any] = build_sheets_service,
    _classify: Callable[..., str] = classify_file,
) -> dict:
    """Enrich every LinkedIn profile at ``input_path`` (a file or a directory).

    A single file is enriched directly. For a directory, each entry is classified
    and **only LinkedIn profiles are enriched**; non-profile files (JDs, anything
    unsupported) are skipped with a log line — this is enrich's half of the
    shared single-input-directory: it ignores what isn't relevant to it.
    Processing continues past a per-file error.

    Arguments:
        input_path: A profile screenshot, or a directory of mixed inputs.
        query_service: AIClient used to parse profiles (and classify ambiguous files).
        spreadsheet_id: Contacts spreadsheet id (required unless ``dry_run``).
        sheet_name: Worksheet/tab name.
        use_cache: Whether model calls consult/populate the response cache.
        dry_run: If True, parse without writing to the sheet.
        data_dir: Root holding ``completed/``; when set (and not ``dry_run``), a
            successfully-enriched profile is moved into ``<data_dir>/completed/profiles/``.
        logger: Optional logger for injection.
        _credentials_loader: Injection point for Google credentials (testing).
        _sheets_builder: Injection point for the Sheets service builder (testing).
        _classify: Injection point for the file classifier (testing).
    Returns:
        Summary dict: ``{processed, skipped, failed, items: [{name, status, ...}]}``.
    Raises:
        FileNotFoundError: If ``input_path`` does not exist.
    """
    _logger = logger or logging.getLogger(__name__)
    input_path = Path(input_path)
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = sorted(f for f in input_path.iterdir() if f.is_file())
    else:
        raise FileNotFoundError(str(input_path))

    summary: dict = {"processed": 0, "skipped": 0, "failed": 0, "items": []}
    for f in files:
        # A directly-named file is processed as-is; within a directory, skip
        # anything that isn't a LinkedIn profile.
        if input_path.is_dir():
            kind = _classify(f, query_service=query_service, use_cache=use_cache, logger=_logger)
            if kind != LINKEDIN_PROFILE:
                _logger.info("Skipping non-profile (%s): %s", kind, f.name)
                summary["skipped"] += 1
                summary["items"].append(
                    {"name": f.name, "path": str(f), "status": "skipped", "kind": kind}
                )
                continue

        try:
            result = enrich_profile(
                f,
                query_service=query_service,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                use_cache=use_cache,
                dry_run=dry_run,
                logger=_logger,
                _credentials_loader=_credentials_loader,
                _sheets_builder=_sheets_builder,
            )
            # On a real (sheet) completion, move the profile out of the input area
            # into completed/ — the enrich analog of apply moving a JD on success.
            profile = result.get("profile") if isinstance(result, dict) else None
            if data_dir is not None and not dry_run and profile:
                # Created date: from the source filename when present (most cases),
                # else the file's mtime. Processed date: today.
                created = extract_filename_date(f.name) or date.fromtimestamp(
                    f.stat().st_mtime
                )
                processed = date.today()
                name = completed_profile_name(
                    profile.get("name", "Unknown"),
                    profile.get("company", "Unknown"),
                    created=created,
                    processed=processed,
                )
                try:
                    dest = move_completed_profile(f, data_dir, name, logger=_logger)
                    write_profile_sidecar(dest, profile, created, processed)
                except OSError as exc:
                    _logger.warning("Could not move profile to completed: %s", exc)
            summary["processed"] += 1
            summary["items"].append(
                {"name": f.name, "path": str(f), "status": "ok", "result": result}
            )
        except Exception as exc:  # noqa: BLE001 — continue-on-error is intentional.
            _logger.error("Failed to enrich %s: %s", f.name, exc)
            summary["failed"] += 1
            summary["items"].append(
                {"name": f.name, "path": str(f), "status": "error", "error": str(exc)}
            )

    return summary


# __END__
