#!/usr/bin/env python3
"""Provider-agnostic AI adapter interface.

An adapter is a *thin* wrapper around one provider SDK: given a prompt and an
optional cached system context, it makes a single completion call and returns an
``AIResult``. All cross-call state (cached context, accumulated usage) lives in the
``AIClient`` wrapper (``jobjob.ailib.session``), not here — so adding a provider is
just a new adapter.
"""

import dataclasses as dcs
from typing import Any, Optional, Protocol

# NOTE: the single source for the per-call output-token default; the adapter and
#   the AIClient wrapper both reference this rather than re-declaring 4096.
DEFAULT_MAX_TOKENS = 4096


@dcs.dataclass(frozen=True)
class AIResult:
    """The result of a single completion call.

    Attributes:
        text: The model's text response.
        usage: The provider's usage object (exposes token-count attributes; consumed
            by ``TokenUsage.add``). May be None if the provider returns none.
    """

    text: str
    usage: Any = None


class AIAdapter(Protocol):
    """Thin, single-call interface implemented per provider."""

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        document: Optional[tuple] = None,
    ) -> AIResult:
        """Make one completion call and return its result.

        ``document`` is an optional ``(media_type, base64_data)`` pair attached to
        the user turn (e.g. a PDF for vision/OCR on image-only files).
        """
        ...


# __END__
