#!/usr/bin/env python3
"""Step 1: parse a job description PDF into a structured JobDescription.

Uses text extraction when possible, Claude vision for image-only PDFs (e.g. saved
job-board screencaptures). See ``jobjob.ailib.extract``.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, Type

from jobjob.ailib.extract import parse_pdf_to_dataclass
from jobjob.ailib.query import query_ai_service
from jobjob.loader.loadstatic import load_document_text_or_none
from jobjob.structure.job_decription import JobDescription


def parse_job_description(
    path: Path,
    query_service: Any,
    klass: Type = JobDescription,
    prompt_path: Optional[Path] = None,
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
    _load_text: Callable[[Path], Optional[str]] = load_document_text_or_none,
) -> JobDescription:
    """Parse a job description into a JobDescription.

    Accepts a PDF *or* a text/Markdown snapshot (e.g. captured from a URL or pasted
    text). The document-aware loader reads snapshots and text-extractable PDFs
    directly; image-only PDFs fall through to the vision path.

    Arguments:
        path: Path to the job-description PDF or text/Markdown snapshot.
        query_service: AIClient (text + vision document support).
        klass: The dataclass to populate (defines the prompt's field structure).
        prompt_path: Override path to the prompt template.
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
        _load_text: Injection point for the text reader (testing).
    Returns:
        A populated JobDescription.
    """
    return parse_pdf_to_dataclass(
        path,
        klass,
        "job_description",
        query_service,
        prompt_path=prompt_path,
        use_cache=use_cache,
        _query=_query,
        _load_text=_load_text,
    )


# __END__
