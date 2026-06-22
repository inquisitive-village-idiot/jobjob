#!/usr/bin/env python3
"""Track Claude API token usage across calls."""

import dataclasses as dcs
from typing import Any


@dcs.dataclass
class TokenUsage:
    """Accumulate token usage across one or more API responses.

    Attributes:
        input_tokens: Uncached input tokens (full price).
        output_tokens: Generated output tokens.
        cache_creation_input_tokens: Tokens written to the prompt cache (~1.25x).
        cache_read_input_tokens: Tokens served from the prompt cache (~0.1x).
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def add(self, usage: Any) -> None:
        """Accumulate usage from an API response ``usage`` object.

        NOTE: Uses ``getattr`` so it tolerates SDK usage objects that omit the
            cache fields (e.g. when caching is disabled).

        Arguments:
            usage: An object exposing the token-count attributes (e.g. the
                Anthropic response ``usage``).
        Returns:
            None
        """
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_creation_input_tokens += (
            getattr(usage, "cache_creation_input_tokens", 0) or 0
        )
        self.cache_read_input_tokens += (
            getattr(usage, "cache_read_input_tokens", 0) or 0
        )

    def summary(self) -> str:
        """Return a human-readable one-line summary with cache-hit percentage."""
        total_input = (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )
        cache_pct = (
            (self.cache_read_input_tokens / total_input * 100) if total_input else 0.0
        )
        return (
            f"Tokens - Input: {self.input_tokens:,}, Output: {self.output_tokens:,}, "
            f"Cache created: {self.cache_creation_input_tokens:,}, "
            f"Cache read: {self.cache_read_input_tokens:,} "
            f"({cache_pct:.1f}% from cache)"
        )


# __END__
