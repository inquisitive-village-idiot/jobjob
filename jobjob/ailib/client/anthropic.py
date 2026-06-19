#!/usr/bin/env python3
"""Thin Anthropic adapter: one call onto ``messages.create``.

NOTE: model and api key are passed in (from config), not read from env here.
TODO: normalize ``AIResult.usage`` to a provider-agnostic shape if/when a second
    provider is added (TokenUsage.add currently tolerates any object via getattr).
"""

from typing import Optional

import anthropic

from jobjob.ailib.client.base import DEFAULT_MAX_TOKENS, AIResult


class AnthropicAdapter:
    """Minimal adapter around the Anthropic Messages API."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        _client: Optional[anthropic.Anthropic] = None,
    ) -> None:
        """Initialize the adapter.

        Arguments:
            model: Claude model id.
            api_key: Anthropic API key. Used only when no client is injected.
            _client: Injected ``anthropic.Anthropic`` instance (for testing).
        Raises:
            ValueError: If no client is injected and no API key is available.
        """
        self.model = model
        if _client is not None:
            self._client = _client
        elif api_key:
            self._client = anthropic.Anthropic(api_key=api_key)
        else:
            raise ValueError("Anthropic API key is required (no client injected).")

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        document: Optional[tuple] = None,
    ) -> AIResult:
        """Send one prompt (with optional cached system context) and return the result.

        The cached ``system`` context is sent as a cached block; the volatile prompt
        goes last, per the prompt-caching prefix rule. When ``document`` is given it
        is attached to the user turn as a base64 document block (PDF vision/OCR).

        Arguments:
            prompt: The user prompt.
            system: Stable cached context, if any.
            max_tokens: Max output tokens.
            document: Optional ``(media_type, base64_data)`` to attach (e.g. a PDF).
        Returns:
            An AIResult with the text response and provider usage.
        Raises:
            TimeoutError: On an API timeout (so query_ai_service can retry).
        """
        if document is None:
            content: object = prompt
        else:
            media_type, data = document
            content = [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data,
                    },
                },
                {"type": "text", "text": prompt},
            ]
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        try:
            response = self._client.messages.create(**kwargs)
        except anthropic.APITimeoutError as err:
            raise TimeoutError(str(err))
        return AIResult(text=response.content[0].text, usage=response.usage)


# __END__
