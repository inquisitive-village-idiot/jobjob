#!/usr/bin/env python3
"""Append LinkedIn profiles to a Google Sheet (Sheets v4).

NOTE: rows are built **full-width and aligned to the header**, then appended at the
    ``<sheet>!A1`` range. This fixes the enricher's blank-leading-columns bug: the
    old gspread ``append_row`` wrote starting at column A while the values were
    placed by header index, so any non-A-anchored layout shifted everything right.
"""

import contextlib
import logging
from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any, Optional

from jobjob.structure.profile import LinkedInProfile

DEFAULT_SHEET_NAME = "contacts"
MISSING = "--"

# Marker on the protected range used as an advisory write lock, so we can find
# and clear a stale lock left by a previously-crashed run.
LOCK_DESCRIPTION = "Locked by jobjob enrich"

# Field -> candidate header names (lower-cased match).
HEADER_NAMES = {
    "location": ("location", "loc"),
    "company": ("company", "org", "organization"),
    "role": ("role", "title", "position"),
    "name": ("name", "full name", "contact"),
    "linkedin_url": ("linkedin_url", "linkedin", "url", "profile"),
    "request": ("request", "date", "added", "request date"),
    "found_by": ("found_by",),
}


def get_header_row(service: Any, spreadsheet_id: str, sheet_name: str) -> list:
    """Return the header row (row 1) of the given sheet."""
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!1:1")
        .execute()
    )
    values = response.get("values") or [[]]
    return values[0]


def detect_columns(headers: list, header_names: Mapping = HEADER_NAMES) -> dict:
    """Map field name -> column index using the header row.

    Arguments:
        headers: The header row cells.
        header_names: Field -> candidate header-name tuples.
    Returns:
        Mapping of field -> 0-based column index (only for fields found).
    """
    lower = [str(h).lower().strip() for h in headers]
    col_map = {}
    for field, candidates in header_names.items():
        for candidate in candidates:
            if candidate in lower:
                col_map[field] = lower.index(candidate)
                break
    return col_map


def build_row(headers: list, col_map: Mapping, values: Mapping) -> list:
    """Build a header-width row with ``values`` placed at their mapped indices."""
    row = [""] * len(headers)
    for field, index in col_map.items():
        if field in values and index < len(row):
            row[index] = values[field]
    return row


def _profile_values(profile: LinkedInProfile, date: datetime) -> dict:
    return {
        "name": profile.name or MISSING,
        "role": profile.role or MISSING,
        "company": profile.company or MISSING,
        "location": profile.location or MISSING,
        "linkedin_url": profile.linkedin_url or MISSING,
        "request": date.strftime("%m/%d/%Y"),
        "found_by": "screenshot",
    }


def _sheet_id_for(service: Any, spreadsheet_id: str, sheet_name: str) -> Optional[int]:
    """Return the numeric sheetId for ``sheet_name``, or None if not found."""
    meta = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties")
        .execute()
    )
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == sheet_name:
            return props.get("sheetId")
    return None


def _stale_lock_ids(service: Any, spreadsheet_id: str, sheet_name: str) -> list:
    """Return ids of our own (stale) protected-range locks on ``sheet_name``."""
    meta = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(title),protectedRanges(protectedRangeId,description))",
        )
        .execute()
    )
    ids = []
    for sheet in meta.get("sheets", []):
        if sheet.get("properties", {}).get("title") != sheet_name:
            continue
        for protected in sheet.get("protectedRanges", []):
            if protected.get("description") == LOCK_DESCRIPTION:
                ids.append(protected["protectedRangeId"])
    return ids


@contextlib.contextmanager
def sheet_lock(
    service: Any,
    spreadsheet_id: str,
    sheet_name: str = DEFAULT_SHEET_NAME,
    logger: logging.Logger | None = None,
) -> Iterator[None]:
    """Advisory write lock: protect the worksheet (no editors) for the duration.

    Adds a Sheets protected range over the whole tab so a concurrent editor
    cannot interleave writes and corrupt an append; the lock is always removed on
    exit. Any stale lock left by a crashed run (matched by ``LOCK_DESCRIPTION``)
    is cleared first, so this is self-healing. The lock is **best-effort** —
    acquisition failures are logged and the write proceeds unlocked rather than
    blocking, since the owner who holds the OAuth token can still write through
    its own protected range.

    Arguments:
        service: Sheets v4 service client.
        spreadsheet_id: The spreadsheet id.
        sheet_name: The worksheet/tab name to lock.
        logger: Optional logger for injection.
    """
    _logger = logger or logging.getLogger(__name__)
    range_id = None
    try:
        sheet_id = _sheet_id_for(service, spreadsheet_id, sheet_name)
        if sheet_id is None:
            _logger.warning(
                "Sheet %r not found; proceeding without a lock.", sheet_name
            )
        else:
            requests: list = [
                {"deleteProtectedRange": {"protectedRangeId": i}}
                for i in _stale_lock_ids(service, spreadsheet_id, sheet_name)
            ]
            requests.append(
                {
                    "addProtectedRange": {
                        "protectedRange": {
                            "range": {"sheetId": sheet_id},
                            "description": LOCK_DESCRIPTION,
                            "warningOnly": False,
                        }
                    }
                }
            )
            resp = (
                service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
                .execute()
            )
            for reply in reversed(resp.get("replies", [])):
                added = reply.get("addProtectedRange")
                if added:
                    range_id = added.get("protectedRange", {}).get("protectedRangeId")
                    break
            _logger.info("Acquired sheet lock (range %s)", range_id)
    except Exception as exc:  # noqa: BLE001 — advisory lock must never block the write.
        _logger.warning("Could not lock sheet (continuing unlocked): %s", exc)

    try:
        yield
    finally:
        if range_id is not None:
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        "requests": [
                            {"deleteProtectedRange": {"protectedRangeId": range_id}}
                        ]
                    },
                ).execute()
                _logger.info("Released sheet lock")
            except Exception as exc:  # noqa: BLE001
                _logger.error(
                    "Failed to release sheet lock (range %s); manual unlock may be "
                    "needed: %s",
                    range_id,
                    exc,
                )


def append_profile(
    service: Any,
    spreadsheet_id: str,
    profile: LinkedInProfile,
    sheet_name: str = DEFAULT_SHEET_NAME,
    date: Optional[datetime] = None,
    logger: logging.Logger | None = None,
    use_lock: bool = True,
) -> list:
    """Append ``profile`` as a new row aligned to the sheet's header.

    Arguments:
        service: Sheets v4 service client.
        spreadsheet_id: The spreadsheet id.
        profile: The profile to append.
        sheet_name: The worksheet/tab name.
        date: The "request"/added date (defaults to now).
        logger: Optional logger for injection.
        use_lock: Guard the append with an advisory ``sheet_lock`` (default True).
    Returns:
        The row that was appended.
    """
    _logger = logger or logging.getLogger(__name__)
    headers = get_header_row(service, spreadsheet_id, sheet_name)
    col_map = detect_columns(headers)
    row = build_row(headers, col_map, _profile_values(profile, date or datetime.now()))

    guard = (
        sheet_lock(service, spreadsheet_id, sheet_name, logger=_logger)
        if use_lock
        else contextlib.nullcontext()
    )
    with guard:
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
    _logger.info("Appended profile to %s: %s", sheet_name, profile.name or MISSING)
    return row


# __END__
