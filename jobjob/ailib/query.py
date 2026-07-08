#!/usr/bin/env python3
"""Query an AI service with retry, response processing, and optional caching."""

import functools
import logging
import subprocess
from collections.abc import Callable
from typing import Any, Optional, TypeVar

from jobjob.ailib import cachemanager
from jobjob.ailib.processresponse import process_response_json

T = TypeVar("T")


def clear_cache(logger: logging.Logger | None = None) -> None:
    """Purge and deregister the global query cache, if one has been created.

    NOTE: This is a no-op when no global cache has been instantiated, so it is
        safe to call in test cleanup without creating cache directories.

    Arguments:
        logger: Optional logger for injection.
    Returns:
        None
    """
    _logger = logger or logging.getLogger(__name__)
    if cachemanager._CACHE is None:
        return  # EARLY EXIT: nothing to clear.
    _logger.debug("Clearing global query cache")
    cachemanager.purge_cache()
    cachemanager.deregister_cache()


def _default_load_cache(prompt: str, model: str | None = None) -> Any:
    """Load a processed response from the global cache. Returns None on miss.

    Arguments:
        prompt: The prompt string.
        model: Optional model identifier; scopes the cache key alongside the prompt.
    """
    try:
        return cachemanager.get_cache().load_from_cache(prompt, model=model)
    except (cachemanager.CacheMissError, cachemanager.InvalidCacheError):
        return None


def _default_save_cache(prompt: str, response: Any, model: str | None = None) -> None:
    """Save a processed response to the global cache.

    Arguments:
        prompt: The prompt string.
        response: The response. Must be JSON encodable.
        model: Optional model identifier; scopes the cache key alongside the prompt.
    """
    cachemanager.get_cache().save_to_cache(prompt, response, model=model)


def query_ai_service(
    prompt: str,
    max_attempt: int = 3,
    use_cache: bool = True,
    _query_service: Optional[Callable[[str], Any]] = None,
    _process_response: Optional[Callable[..., T]] = None,
    _load_cache: Optional[Callable[[str], Any]] = None,
    _save_cache: Optional[Callable[[str, Any], None]] = None,
    logger: logging.Logger | None = None,
) -> T:
    """Call the service and return the processed response.

    Retries on service timeout and on response-processing failure (ValueError),
    up to ``max_attempt`` times. Unknown exceptions are not retried.

    Caching: a cache hit (a non-None result from ``_load_cache``) short-circuits
    the service call. On a miss, the processed response is written via
    ``_save_cache``. When ``use_cache`` is True and no cache callables are
    injected, the global CacheManager is wired in by default; injected callables
    are always honored regardless of ``use_cache``. The default cache key is
    model-scoped: the model is derived from ``_query_service.model`` (``None``
    if absent) and bound into the default callables, so the same prompt under a
    different model never collides with -- or is served by -- another model's
    cached response.

    Arguments:
        prompt: The prompt.
        max_attempt: Max number of attempts. Defaults to 3.
        use_cache: If true, wire the default global cache when none is injected.
            Defaults to True.
        _query_service: Wrapper around the service. Expected to raise
            subprocess.TimeoutExpired or TimeoutError on timeout.
        _process_response: Wrapper around response processing. Expected to raise
            ValueError on failure. Defaults to ``process_response_json``.
        _load_cache: Cache reader; returns the cached processed response or None
            on miss.
        _save_cache: Cache writer; called with ``(prompt, processed)``.
        logger: Optional logger for injection.
    Returns:
        The processed response.
    Raises:
        TimeoutError: If the service call timed out on every attempt.
        ValueError: If the response could not be processed on every attempt.
        RuntimeError: On any other failure / exhausted attempts.
    """
    _logger = logger or logging.getLogger(__name__)
    _process_response = _process_response or process_response_json
    model = getattr(_query_service, "model", None)

    # NOTE: use_cache only gates default-wiring; injected callables always apply.
    if _load_cache is None and use_cache:
        _load_cache = functools.partial(_default_load_cache, model=model)
    if _save_cache is None and use_cache:
        _save_cache = functools.partial(_default_save_cache, model=model)

    if _load_cache is not None:
        cached = _load_cache(prompt)
        if cached is not None:
            _logger.debug("Cache hit")
            return cached  # EARLY EXIT: served from cache.

    for attempt in range(1, max_attempt + 1):
        try:
            response = _query_service(prompt)
        except (TimeoutError, subprocess.TimeoutExpired) as err:
            if attempt < max_attempt:
                _logger.warning(
                    "Query timeout, retrying (%d/%d, %s)",
                    attempt,
                    max_attempt,
                    _query_service.__name__,
                )
                continue
            raise TimeoutError(f"Timeout to service call: {str(err)}")

        try:
            processed = _process_response(response)
        except ValueError as err:
            if attempt < max_attempt:
                _logger.warning(
                    "Error processing response, retrying (%d/%d, %s, %s): %s",
                    attempt,
                    max_attempt,
                    _query_service.__name__,
                    _process_response.__name__,
                    str(err),
                )
                continue
            raise ValueError(f"Failed to process response: {str(err)}")

        if _save_cache is not None:
            _save_cache(prompt, processed)

        return processed  # EARLY EXIT: We have a valid response.

    raise RuntimeError(f"max retry exceeded ({_query_service.__name__})")


# __END__
