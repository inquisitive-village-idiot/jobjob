#!/usr/bin/env python3
"""Ingest a job posting from a URL or pasted text into a durable snapshot.

A *snapshot* is the durable artifact: the posting's main text written into the
jobs input dir as Markdown. It survives the original posting going 404 after the
role closes and flows through the existing JD parser unchanged (the parser is
text-first). This sits *upstream* of parsing — once a snapshot exists it is just
another input file in ``data/jobs/``.

Two entry points:

* :func:`snapshot_from_url` — a plain server-side GET plus readability-style main
  text extraction. JS-rendered or auth-gated boards (LinkedIn, Workday, iCIMS,
  Greenhouse SPAs) return an empty skeleton to a plain GET, so a minimum-length
  heuristic detects that and raises :class:`JDIngestError` rather than parsing
  empty text. A headless browser is intentionally *not* used here.
* :func:`snapshot_from_text` — the reliable fallback for the hard boards: the user
  pastes the raw posting text and it is snapshotted the same way.

Network access (:func:`_http_get`) and extraction (:func:`extract_main_text`) are
isolated, lazily-imported, and injectable so callers/tests never hit the network.
"""

import logging
import os
import re
from collections.abc import Callable
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

if TYPE_CHECKING:
    import httpx

# Pre-compiled patterns for slugifying filenames.
_SLUG_STRIP_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_SLUG_DASH_RE = re.compile(r"[\s_-]+")


def _env_int(name: str, default: int) -> int:
    """Read a non-negative int from the environment, falling back to ``default``.

    A blank or unparseable value falls back rather than crashing module import.
    """
    raw = (os.environ.get(name) or "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float from the environment, falling back to ``default``."""
    raw = (os.environ.get(name) or "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


# Below this many characters of *extracted* text we assume extraction failed: a
# JS-rendered or auth-gated board returned an empty skeleton to a plain GET.
# Env-overridable so a deployment can tune the heuristic without a code change.
MIN_SNAPSHOT_CHARS = _env_int("JOBJOB_JD_MIN_SNAPSHOT_CHARS", 200)

# Pasted text is vouched for by the user, so only guard against blank/accidental
# submissions rather than applying the skeleton heuristic.
MIN_PASTE_CHARS = _env_int("JOBJOB_JD_MIN_PASTE_CHARS", 40)

# A generous default; a slow board should fail loudly rather than hang a request.
DEFAULT_TIMEOUT = _env_float("JOBJOB_JD_FETCH_TIMEOUT", 20.0)


@cache
def get_user_agent() -> str:
    """Return the outbound User-Agent string (cached).

    Identifies the fetcher as an automated, contactable client.
    """
    platform = "compatible"  # indicate automated fetcher
    software = "jobjob/1.0"
    contact = "https://github.com/inquisitive-village-idiot/jobjob"
    return f"Mozilla/5.0 ({platform}; {software}; +{contact})"


# Guidance shown when a URL yields too little text — the actionable fallback.
_EXTRACTION_FAILED_MESSAGE = (
    "Couldn't extract text from this URL — save the posting as a PDF and upload it "
    "instead, or paste the posting text. Many job boards render the posting with "
    "JavaScript or require sign-in, which a simple fetch can't see."
)


class JDIngestError(ValueError):
    """A URL or pasted text yielded too little job text to parse.

    Carries a user-facing message; the webapp surfaces it as a 422 so the user can
    fall back to PDF upload or paste-text.
    """


def safe_url(url: str) -> "httpx.URL":
    """Parse and validate ``url`` into an ``httpx.URL`` (http/https only).

    Uses ``httpx.URL`` (imported lazily) to encode and validate rather than a regex,
    so callers never re-derive or re-overwrite the raw string.

    Arguments:
        url: The candidate job-posting URL.
    Returns:
        The parsed, validated URL.
    Raises:
        JDIngestError: If the URL is blank, unparseable, or not http(s).
    """
    import httpx

    cleaned = (url or "").strip()
    if not cleaned:
        raise JDIngestError("No URL provided.")
    try:
        parsed = httpx.URL(cleaned)
    except (TypeError, ValueError) as exc:
        raise JDIngestError("URL is not valid.") from exc
    if parsed.scheme not in ("http", "https"):
        raise JDIngestError("URL must start with http:// or https://.")
    return parsed


def _http_get(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> str:
    """GET ``url`` and return the response body as text.

    Imports ``httpx`` lazily so importing this module stays cheap and offline.

    Arguments:
        url: The absolute http(s) URL to fetch.
        timeout: Per-request timeout in seconds.
    Returns:
        The response body decoded as text.
    Raises:
        httpx.HTTPError: On a transport error or non-2xx status.
    """
    import httpx

    resp = httpx.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": get_user_agent()},
    )
    resp.raise_for_status()
    return resp.text


def extract_main_text(html: str) -> str:
    """Extract the main article/posting text from ``html``.

    Uses ``trafilatura`` (readability-style extraction), imported lazily. Returns
    the stripped text, or ``""`` when nothing meaningful could be extracted.

    Arguments:
        html: Raw HTML of the fetched page.
    Returns:
        The extracted main text, stripped (possibly empty).
    """
    import trafilatura

    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    return (text or "").strip()


def _slugify(value: str, max_len: int = 60) -> str:
    """Return a filesystem-safe, lowercase, hyphenated slug for a filename."""
    value = _SLUG_STRIP_RE.sub("", value).strip().lower()
    value = _SLUG_DASH_RE.sub("-", value)
    return value[:max_len].strip("-") or "posting"


def _get_slug_source(source_url: Optional[str], title: Optional[str]) -> str:
    """Pick the basis for the filename slug: an explicit title, else the URL host."""
    if title:
        return title
    if source_url:
        return urlparse(source_url).netloc or "posting"
    return "posting"


def _snapshot_path(jobs_dir: Path, slug: str, _now: datetime | None = None) -> Path:
    """Build a unique, timestamped snapshot path under ``jobs_dir``.

    Arguments:
        jobs_dir: The jobs input directory (already a Path).
        slug: Filesystem-safe slug for the filename.
        _now: Optional timestamp so the caller can share one value between the
            filename and the snapshot header (and for deterministic tests).
    """
    stamp = (_now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return Path(jobs_dir, f"jd-{stamp}-{slug}.md")


def write_snapshot(
    text: str,
    jobs_dir: Path,
    *,
    source_url: Optional[str] = None,
    title: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> Path:
    """Write ``text`` as a Markdown snapshot into ``jobs_dir`` and return the path.

    The snapshot leads with provenance comments (source URL, capture time) followed
    by the posting text. HTML comments are ignored by the downstream JD parser, so
    the captured text reaches the model unchanged.

    Arguments:
        text: The posting text to snapshot (already extracted/cleaned).
        jobs_dir: The jobs input directory (created if missing).
        source_url: Originating URL, recorded for provenance and used for the slug.
        title: Optional human title used for the filename slug.
        logger: Optional logger; falls back to the module logger.
    Returns:
        The path to the written snapshot.
    """
    _logger = logger or logging.getLogger(__name__)
    jobs_dir = Path(jobs_dir)
    jobs_dir.mkdir(exist_ok=True)

    slug_source = _get_slug_source(source_url, title)
    now = datetime.now()
    path = _snapshot_path(jobs_dir, _slugify(slug_source), _now=now)

    header = [f"<!-- captured: {now.isoformat(timespec='seconds')} -->"]
    if source_url:
        header.insert(0, f"<!-- source: {source_url} -->")
    content = "\n".join(header) + "\n\n" + text.strip() + "\n"

    path.write_text(content, encoding="utf-8")
    _logger.info("Wrote JD snapshot: %s (%d chars)", path, len(text))
    return path


def snapshot_from_url(
    url: str,
    jobs_dir: Path,
    *,
    min_chars: int = MIN_SNAPSHOT_CHARS,
    logger: Optional[logging.Logger] = None,
    _fetch_html: Callable[[str], str] = _http_get,
    _extract: Callable[[str], str] = extract_main_text,
) -> Path:
    """Fetch ``url``, extract its main text, and write a snapshot into ``jobs_dir``.

    Arguments:
        url: The job-posting URL (http/https).
        jobs_dir: The jobs input directory.
        min_chars: Minimum extracted length below which extraction is treated as a
            failure (JS-rendered/auth-gated board returning an empty skeleton).
        logger: Optional logger; falls back to the module logger.
        _fetch_html: Injection point for the HTTP GET (testing).
        _extract: Injection point for main-text extraction (testing).
    Returns:
        The path to the written snapshot.
    Raises:
        JDIngestError: If the URL is missing/invalid, the fetch fails, or too little
            text was extracted to parse.
    """
    _logger = logger or logging.getLogger(__name__)
    clean_url = str(safe_url(url))

    try:
        html = _fetch_html(clean_url)
    except Exception as exc:  # noqa: BLE001 — any transport/HTTP error → loud, clean.
        raise JDIngestError(f"Could not fetch the URL: {exc}") from exc

    text = _extract(html)
    if len(text) < min_chars:
        _logger.warning(
            "Extraction yielded %d chars from %s; refusing to parse.",
            len(text),
            clean_url,
        )
        raise JDIngestError(_EXTRACTION_FAILED_MESSAGE)

    return write_snapshot(text, jobs_dir, source_url=clean_url, logger=logger)


def snapshot_from_text(
    text: str,
    jobs_dir: Path,
    *,
    min_chars: int = MIN_PASTE_CHARS,
    title: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> Path:
    """Write pasted posting ``text`` as a snapshot into ``jobs_dir``.

    The reliable fallback for boards a plain GET can't read.

    Arguments:
        text: The raw posting text the user pasted.
        jobs_dir: The jobs input directory.
        min_chars: Minimum length below which the text is rejected as too short.
        title: Optional human title used for the filename slug.
        logger: Optional logger; passed through to the snapshot writer.
    Returns:
        The path to the written snapshot.
    Raises:
        JDIngestError: If the pasted text is empty or too short to be a posting.
    """
    cleaned = (text or "").strip()
    if len(cleaned) < min_chars:
        raise JDIngestError(
            f"Pasted text is too short to be a job posting "
            f"(need at least {min_chars} characters)."
        )
    return write_snapshot(cleaned, jobs_dir, title=title, logger=logger)


# __END__
