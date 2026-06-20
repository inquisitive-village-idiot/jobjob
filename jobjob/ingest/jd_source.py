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
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Below this many characters of *extracted* text we assume extraction failed: a
# JS-rendered or auth-gated board returned an empty skeleton to a plain GET.
MIN_SNAPSHOT_CHARS = 200

# Pasted text is vouched for by the user, so only guard against blank/accidental
# submissions rather than applying the skeleton heuristic.
MIN_PASTE_CHARS = 40

# A generous default; a slow board should fail loudly rather than hang a request.
DEFAULT_TIMEOUT = 20.0

_USER_AGENT = (
    "Mozilla/5.0 (compatible; jobjob/1.0; +https://github.com/inquisitive-village-idiot/jobjob)"
)

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
        headers={"User-Agent": _USER_AGENT},
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
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    value = re.sub(r"[\s_-]+", "-", value)
    return value[:max_len].strip("-") or "posting"


def _snapshot_path(jobs_dir: Path, slug: str) -> Path:
    """Build a unique, timestamped snapshot path under ``jobs_dir``."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(jobs_dir) / f"jd-{stamp}-{slug}.md"


def write_snapshot(
    text: str,
    jobs_dir: Path,
    *,
    source_url: Optional[str] = None,
    title: Optional[str] = None,
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
    Returns:
        The path to the written snapshot.
    """
    jobs_dir = Path(jobs_dir)
    jobs_dir.mkdir(parents=True, exist_ok=True)

    slug_source = title or (urlparse(source_url).netloc if source_url else "") or "posting"
    path = _snapshot_path(jobs_dir, _slugify(slug_source))

    header = [f"<!-- captured: {datetime.now().isoformat(timespec='seconds')} -->"]
    if source_url:
        header.insert(0, f"<!-- source: {source_url} -->")
    content = "\n".join(header) + "\n\n" + text.strip() + "\n"

    path.write_text(content, encoding="utf-8")
    logger.info("Wrote JD snapshot: %s (%d chars)", path, len(text))
    return path


def snapshot_from_url(
    url: str,
    jobs_dir: Path,
    *,
    min_chars: int = MIN_SNAPSHOT_CHARS,
    _fetch_html: Callable[[str], str] = _http_get,
    _extract: Callable[[str], str] = extract_main_text,
) -> Path:
    """Fetch ``url``, extract its main text, and write a snapshot into ``jobs_dir``.

    Arguments:
        url: The job-posting URL (http/https).
        jobs_dir: The jobs input directory.
        min_chars: Minimum extracted length below which extraction is treated as a
            failure (JS-rendered/auth-gated board returning an empty skeleton).
        _fetch_html: Injection point for the HTTP GET (testing).
        _extract: Injection point for main-text extraction (testing).
    Returns:
        The path to the written snapshot.
    Raises:
        JDIngestError: If the URL is missing/invalid, the fetch fails, or too little
            text was extracted to parse.
    """
    url = (url or "").strip()
    if not url:
        raise JDIngestError("No URL provided.")
    if not re.match(r"^https?://", url, re.IGNORECASE):
        raise JDIngestError("URL must start with http:// or https://.")

    try:
        html = _fetch_html(url)
    except Exception as exc:  # noqa: BLE001 — any transport/HTTP error → loud, clean.
        raise JDIngestError(f"Could not fetch the URL: {exc}") from exc

    text = _extract(html)
    if len(text) < min_chars:
        logger.warning("Extraction yielded %d chars from %s; refusing to parse.", len(text), url)
        raise JDIngestError(_EXTRACTION_FAILED_MESSAGE)

    return write_snapshot(text, jobs_dir, source_url=url)


def snapshot_from_text(
    text: str,
    jobs_dir: Path,
    *,
    min_chars: int = MIN_PASTE_CHARS,
    title: Optional[str] = None,
) -> Path:
    """Write pasted posting ``text`` as a snapshot into ``jobs_dir``.

    The reliable fallback for boards a plain GET can't read.

    Arguments:
        text: The raw posting text the user pasted.
        jobs_dir: The jobs input directory.
        min_chars: Minimum length below which the text is rejected as too short.
        title: Optional human title used for the filename slug.
    Returns:
        The path to the written snapshot.
    Raises:
        JDIngestError: If the pasted text is empty or too short to be a posting.
    """
    cleaned = (text or "").strip()
    if len(cleaned) < min_chars:
        raise JDIngestError(
            f"Pasted text is too short to be a job posting (need at least {min_chars} characters)."
        )
    return write_snapshot(cleaned, jobs_dir, title=title)


# __END__
