#!/usr/bin/env python3
"""Provider-agnostic AI client wrapper.

``AIClient`` binds a thin adapter together with the cross-call state — the cached
context (set once per run) and the accumulated ``TokenUsage`` — and is callable, so
it plugs directly into ``query_ai_service`` as the ``_query_service``.
"""

import base64
from pathlib import Path
from typing import Optional

from jobjob.ailib.client.base import DEFAULT_MAX_TOKENS, AIAdapter
from jobjob.structure.token_usage import TokenUsage

PDF_MEDIA_TYPE = "application/pdf"


class AIClient:
    """Callable wrapper: holds an adapter, the cached context, and usage totals.

    Attributes:
        adapter: The provider adapter.
        max_tokens: Default max output tokens per call.
        usage: Accumulated token usage across calls.
    """

    def __init__(
        self, adapter: AIAdapter, max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> None:
        """Initialize the client.

        Arguments:
            adapter: A provider adapter (e.g. ``AnthropicAdapter``).
            max_tokens: Default max output tokens per call.
        """
        self.adapter = adapter
        self.max_tokens = max_tokens
        self.usage = TokenUsage()
        self._cached_context: Optional[str] = None

    def set_cached_context(self, context: str) -> None:
        """Set the stable context sent (cached) on every subsequent call."""
        self._cached_context = context

    def __call__(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Send ``prompt`` (with the cached context) and return the text response.

        Arguments:
            prompt: The user prompt.
            max_tokens: Per-call override of the default max output tokens.
        Returns:
            The model's text response.
        """
        result = self.adapter.complete(
            prompt,
            system=self._cached_context,
            max_tokens=max_tokens or self.max_tokens,
        )
        if result.usage is not None:
            self.usage.add(result.usage)
        return result.text

    def complete_document(
        self,
        prompt: str,
        path: Path,
        media_type: str = PDF_MEDIA_TYPE,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send ``prompt`` with ``path`` attached as a document (PDF vision/OCR).

        Arguments:
            prompt: The user prompt.
            path: File to attach (base64-encoded).
            media_type: The document media type.
            max_tokens: Per-call override of the default max output tokens.
        Returns:
            The model's text response.
        """
        data = base64.standard_b64encode(Path(path).read_bytes()).decode("utf-8")
        result = self.adapter.complete(
            prompt,
            system=self._cached_context,
            max_tokens=max_tokens or self.max_tokens,
            document=(media_type, data),
        )
        if result.usage is not None:
            self.usage.add(result.usage)
        return result.text


# __END__
