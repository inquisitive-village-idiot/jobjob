#!/usr/bin/env python3
"""Explicit re-parse (application-identity phase 6c / design D3's one
sanctioned overwrite): re-run JD parsing for an already-built application and
overwrite its source-tier ``company``/``role``/``description`` fields.

Parse-once (``application_source.ensure_source``) is otherwise sacred — a
rebuild's parse step never touches an existing ``source.json``, so a user's
manual correction (via **Edit source**) survives every re-build. This is the
single, explicitly user-triggered exception: pick up parser/prompt
improvements at the cost of clobbering whatever was there before, including
any manual corrections. Nothing else about the application changes — no
artifacts are regenerated, entity_id/status/execution history are untouched.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from jobjob.apply.generate.parse import parse_job_description
from services import application_source


class ReparseError(Exception):
    """Re-parse could not run (e.g. no JD file recorded for this application)."""


def reparse_source(
    folder: Path,
    query_service: Any,
    *,
    use_cache: bool = True,
    logger: Optional[logging.Logger] = None,
    _parse: Any = parse_job_description,
) -> dict:
    """Re-run JD parsing and overwrite company/role/description in source.json.

    The JD path comes from the existing ``source.json``'s ``file_uri`` (the JD
    copy placed in the entity folder at build time) — ``web_uri``/
    ``external_ref``/``entity_id`` are left exactly as they were; only the
    parse-once fields are refreshed.

    Arguments:
        folder: The application (entity) folder.
        query_service: AIClient used for the parse call.
        use_cache: Whether the parse call consults/populates the response cache.
        logger: Optional logger.
        _parse: Injection point for ``parse_job_description`` (testing).
    Returns:
        The full, freshly-written source dict.
    Raises:
        ReparseError: No JD file is recorded (or it no longer exists on disk)
            for this application — nothing to re-parse from.
    """
    _logger = logger or logging.getLogger(__name__)
    existing = application_source.read_source(folder)
    file_uri = existing.get("file_uri")
    if not file_uri or not Path(file_uri).is_file():
        raise ReparseError(
            "No job-description file recorded for this application; cannot re-parse."
        )
    job = _parse(Path(file_uri), query_service, use_cache=use_cache)
    _logger.info("Re-parsed %s: %s / %s", folder, job.company_name, job.role_title)
    merged = {
        **existing,
        "company": job.company_name,
        "role": job.role_title,
        "description": job.summary,
    }
    return application_source.write_source(folder, merged)


# __END__
