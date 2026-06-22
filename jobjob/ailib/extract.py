#!/usr/bin/env python3
"""Parse a PDF into a dataclass: text first, Claude vision as a fallback.

Text-extractable PDFs are parsed from their text (cacheable). Image-only PDFs
(scanned screenshots / saved web pages) have no extractable text, so the PDF is
attached as a document and the model reads it directly. Shared by the JD parser
and the LinkedIn-profile parser.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

from jobjob.ailib.query import query_ai_service
from jobjob.loader.loadprompt import format_dataclass_prompt
from jobjob.loader.loadstatic import load_pdf_text_or_none
from jobjob.structure.build import from_mapping

T = TypeVar("T")

VISION_TEXT_PLACEHOLDER = "(See the attached PDF document.)"


def parse_pdf_to_dataclass(
    path: Path,
    klass: Type[T],
    prompt_stem: str,
    query_service: Any,
    prompt_path: Optional[Path] = None,
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
    _load_text: Callable[[Path], Optional[str]] = load_pdf_text_or_none,
) -> T:
    """Parse ``path`` into ``klass`` using text extraction, or vision if image-only.

    Arguments:
        path: The PDF to parse.
        klass: The dataclass to populate (its field docs define the schema).
        prompt_stem: Stem of the prompt template in ``static/prompt``.
        query_service: AIClient (``__call__`` for text; ``complete_document`` for
            vision).
        prompt_path: Override path to the prompt template.
        use_cache: Whether the text path consults/populates the response cache.
            The vision path never caches (the prompt is identical across files).
        _query: Injection point for ``query_ai_service`` (testing).
        _load_text: Injection point for the text reader (testing).
    Returns:
        A populated ``klass`` instance.
    """
    path = Path(path)
    text = _load_text(path)
    if text:
        prompt = format_dataclass_prompt(
            klass, prompt_stem, text, prompt_path=prompt_path
        )
        data = _query(prompt, _query_service=query_service, use_cache=use_cache)
    else:
        # NOTE: vision path — attach the PDF and let the model read it. The prompt is
        #   the same for every image-only file, so caching is disabled to avoid
        #   collisions.
        prompt = format_dataclass_prompt(
            klass, prompt_stem, VISION_TEXT_PLACEHOLDER, prompt_path=prompt_path
        )

        def _vision_service(text_prompt: str) -> str:
            return query_service.complete_document(text_prompt, path)

        data = _query(prompt, _query_service=_vision_service, use_cache=False)
    return from_mapping(klass, data)


# __END__
