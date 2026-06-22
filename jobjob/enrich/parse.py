#!/usr/bin/env python3
"""Parse a LinkedIn profile screenshot (PDF) into a LinkedInProfile.

Text extraction when possible, Claude vision for image-only screenshots. See
``jobjob.ailib.extract``.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, Type

from jobjob.ailib.extract import parse_pdf_to_dataclass
from jobjob.ailib.query import query_ai_service
from jobjob.structure.profile import LinkedInProfile


def parse_profile(
    path: Path,
    query_service: Any,
    klass: Type = LinkedInProfile,
    prompt_path: Optional[Path] = None,
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
) -> LinkedInProfile:
    """Parse a LinkedIn profile screenshot PDF into a LinkedInProfile.

    Arguments:
        path: Path to the profile screenshot PDF.
        query_service: AIClient (text + vision document support).
        klass: The dataclass to populate (defines the prompt's field structure).
        prompt_path: Override path to the prompt template.
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        A populated LinkedInProfile.
    """
    return parse_pdf_to_dataclass(
        path,
        klass,
        "linkedin_profile",
        query_service,
        prompt_path=prompt_path,
        use_cache=use_cache,
        _query=_query,
    )


# __END__
