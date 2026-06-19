#!/usr/bin/env python3
"""Classify an input file as a job description, a LinkedIn profile, or unsupported.

Hybrid strategy (cheap first):
  1. Filename fast-path — LinkedIn profile screenshots are named ``*linkedin-in*``.
  2. Text signals — extract the text and score JD vs profile keyword hits.
  3. AI fallback — only when the text is ambiguous and a query service is provided.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from jobjob.ailib.query import query_ai_service
from jobjob.loader.loadstatic import SUPPORTED_SUFFIXES, read_document

JD = "jd"
LINKEDIN_PROFILE = "linkedin_profile"
UNSUPPORTED = "unsupported"

# Image suffixes are "supported" inputs (likely profile screenshots) even though we
# cannot extract text from them without vision.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")

PROFILE_FILENAME_SIGNALS = ("linkedin-in", "linkedin_in")
# Job-board / ATS URL fragments common in saved job-posting screencaptures.
JD_FILENAME_SIGNALS = (
    "careers",
    "myworkdayjobs",
    "-jobs-",
    "-job-",
    "greenhouse",
    "lever.co",
    "ashbyhq",
    "smartrecruiters",
)
PROFILE_TEXT_SIGNALS = (
    "linkedin.com/in/",
    "connections",
    "followers",
    "mutual connection",
    "see all activity",
    "people also viewed",
)
JD_TEXT_SIGNALS = (
    "responsibilities",
    "qualifications",
    "requirements",
    "what you'll do",
    "what you will do",
    "about the role",
    "about the job",
    "we are looking for",
    "we're looking for",
    "job description",
    "minimum qualifications",
    "equal opportunity",
)


def _score(text: str, signals) -> int:
    return sum(1 for signal in signals if signal in text)


def _classify_with_ai(
    text: str,
    query_service: Callable[[str], str],
    use_cache: bool,
    _query: Callable[..., Any],
) -> str:
    prompt = (
        "Classify the document as exactly one of: jd (a job posting / job "
        "description), linkedin_profile (a LinkedIn profile page), or other.\n\n"
        f"DOCUMENT (truncated):\n{text[:2000]}\n\n"
        'Return JSON: {"type": "jd" | "linkedin_profile" | "other"}. Only the JSON.'
    )
    data = _query(prompt, _query_service=query_service, use_cache=use_cache)
    chosen = data.get("type") if isinstance(data, dict) else None
    if chosen == JD:
        return JD
    if chosen == LINKEDIN_PROFILE:
        return LINKEDIN_PROFILE
    return UNSUPPORTED


def classify_file(
    path: Path,
    query_service: Optional[Callable[[str], str]] = None,
    use_cache: bool = True,
    logger: logging.Logger | None = None,
    _read: Callable[[Path], str] = read_document,
    _query: Callable[..., Any] = query_ai_service,
) -> str:
    """Classify ``path`` as ``JD``, ``LINKEDIN_PROFILE``, or ``UNSUPPORTED``.

    Arguments:
        path: The file to classify.
        query_service: Optional AI client; enables the AI fallback for ambiguous
            text. When None, ambiguous files return ``UNSUPPORTED``.
        use_cache: Whether the AI fallback consults/populates the response cache.
        logger: Optional logger for injection.
        _read: Injection point for the document text reader (testing).
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        One of ``JD`` / ``LINKEDIN_PROFILE`` / ``UNSUPPORTED``.
    """
    _logger = logger or logging.getLogger(__name__)
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES and suffix not in IMAGE_SUFFIXES:
        return UNSUPPORTED  # EARLY EXIT: not a file type we handle.

    name = path.name.lower()
    if any(signal in name for signal in PROFILE_FILENAME_SIGNALS):
        return LINKEDIN_PROFILE  # EARLY EXIT: profile filename fast-path.
    if any(signal in name for signal in JD_FILENAME_SIGNALS):
        return JD  # EARLY EXIT: job-board / ATS filename fast-path.

    try:
        text = _read(path).lower()
    except (ValueError, OSError):
        # NOTE: e.g. an image-only PDF yields no text.
        text = ""

    profile_score = _score(text, PROFILE_TEXT_SIGNALS)
    jd_score = _score(text, JD_TEXT_SIGNALS)
    if jd_score > profile_score:
        return JD
    if profile_score > jd_score:
        return LINKEDIN_PROFILE

    # Tie (often 0/0): defer to the AI fallback when available.
    if query_service is not None and text:
        _logger.debug("Ambiguous classification; using AI fallback: %s", path.name)
        return _classify_with_ai(text, query_service, use_cache, _query)
    return UNSUPPORTED


# __END__
