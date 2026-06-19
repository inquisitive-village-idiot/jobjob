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
from jobjob.structure.job_decription import JobDescription


def parse_job_description(
    path: Path,
    query_service: Any,
    klass: Type = JobDescription,
    prompt_path: Optional[Path] = None,
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
) -> JobDescription:
    """Parse a job-description PDF into a JobDescription.

    Arguments:
        path: Path to the job-description PDF.
        query_service: AIClient (text + vision document support).
        klass: The dataclass to populate (defines the prompt's field structure).
        prompt_path: Override path to the prompt template.
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        A populated JobDescription.
    """
    return parse_pdf_to_dataclass(
        path, klass, "job_description", query_service,
        prompt_path=prompt_path, use_cache=use_cache, _query=_query,
    )


# __END__
