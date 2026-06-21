#!/usr/bin/env python3
"""Process raw LLM responses into structured data."""

import json
import re
from collections.abc import Mapping
from typing import Any, Protocol, Union


# Pre-compiled patterns for salvaging JSON wrapped in prose or markdown fences.
_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")
_OBJECT_RE = re.compile(r"\{[\s\S]*\}")
_ARRAY_RE = re.compile(r"\[[\s\S]*\]")


class ProcessResponse(Protocol):
    def __call__(self, response: str) -> Union[Mapping, str]: ...


def process_response_json(response: str) -> Any:
    """Extract JSON from an LLM response.

    Tolerates responses that wrap JSON in prose or markdown code fences. Tries,
    in order: the whole string, a fenced ```json block, the first object, then
    the first array.

    Arguments:
        response: Raw text response from the LLM.
    Returns:
        The decoded JSON (typically a dict or list).
    Raises:
        ValueError: If no valid JSON can be extracted.
    """
    # NOTE: ValueError is the retry signal for query_ai_service; json.JSONDecodeError
    #   subclasses ValueError, but we normalize to a clear message on total failure.
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    if "```" in response:
        match = _FENCE_RE.search(response)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    for pattern in (_OBJECT_RE, _ARRAY_RE):
        match = pattern.search(response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    raise ValueError("No valid JSON found in response")


# __END__
