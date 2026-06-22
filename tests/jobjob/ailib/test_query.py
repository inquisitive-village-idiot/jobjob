#!/usr/bin/env python3
"""Test."""

import logging
import subprocess
from unittest import TestCase, expectedFailure, mock

import jobjob.ailib.query as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def setUp(self) -> None:
        self.addCleanup(MOD.clear_cache)


class TestClearCache(ThisTestCase):
    """Test function."""

    @expectedFailure
    def test_empties_cache(self) -> None:
        self.fail()

    def test_noop_when_no_cache_registered(self) -> None:
        # Ensure no global cache is set; clear_cache should not raise.
        import jobjob.ailib.cachemanager as cm

        self.assertIsNone(cm._CACHE)
        MOD.clear_cache()  # Should be a no-op.

    def test_clears_active_cache(self) -> None:
        import tempfile
        from pathlib import Path

        import jobjob.ailib.cachemanager as cm

        tmpdir = Path(tempfile.mkdtemp())
        cache = cm.CacheManager(tmpdir)
        cm._CACHE = cache
        cm._CACHE_PATH = cache.cache_path

        try:
            MOD.clear_cache()
            self.assertIsNone(cm._CACHE)
        finally:
            # Safety: ensure cleanup even on failure.
            if cm._CACHE is not None:
                MOD.clear_cache()


class TestQueryService(ThisTestCase):
    """Test function."""

    def test_raises_for_service_timeout_with_retry(self) -> None:
        mock_service = mock.MagicMock(__name__="service")
        mock_service.side_effect = subprocess.TimeoutExpired("command", 120)

        kwargs = {"max_attempt": 5, "prompt": "... some text ...", "use_cache": False}
        inject = {"_query_service": mock_service}

        with self.assertRaises(TimeoutError):
            MOD.query_ai_service(**kwargs, **inject)

        expected = kwargs["max_attempt"]
        found = mock_service.call_count
        self.assertEqual(expected, found)

    def test_raises_for_process_response_with_retry(self) -> None:
        mock_service = mock.MagicMock(__name__="service")
        mock_process = mock.MagicMock(__name__="process")
        mock_process.side_effect = ValueError("e.g., json encoding")

        kwargs = {"max_attempt": 5, "prompt": "... some text ...", "use_cache": False}
        inject = {"_query_service": mock_service, "_process_response": mock_process}

        with self.assertRaisesRegex(ValueError, "Failed to process response"):
            MOD.query_ai_service(**kwargs, **inject)

        expected = kwargs["max_attempt"]
        found = mock_process.call_count
        self.assertEqual(expected, found)

    def test_raises_service_error_without_retry(self) -> None:
        mock_service = mock.MagicMock(__name__="service")
        mock_service.side_effect = RuntimeError("... some error ...")

        kwargs = {"max_attempt": 5, "prompt": "... some text ...", "use_cache": False}
        inject = {"_query_service": mock_service}

        with self.assertRaisesRegex(RuntimeError, "some error"):
            MOD.query_ai_service(**kwargs, **inject)

        expected = 1  # NOTE: Unknown exceptions are not retried
        found = mock_service.call_count
        self.assertEqual(expected, found)

    def test_cache_behavior(self) -> None:
        mock_lcache = mock.MagicMock()
        mock_scache = mock.MagicMock()
        mock_service = mock.MagicMock(__name__="service")
        mock_process = mock.MagicMock(__name__="process")

        mock_lcache.side_effect = (None, "cached_response")

        kwargs = {"max_attempt": 5, "prompt": "... some text ...", "use_cache": False}
        inject = {
            "_query_service": mock_service,
            "_process_response": mock_process,
            "_load_cache": mock_lcache,
            "_save_cache": mock_scache,
        }

        response_1 = MOD.query_ai_service(**kwargs, **inject)
        response_2 = MOD.query_ai_service(**kwargs, **inject)

        with self.subTest("returns process then cache"):
            # NOTE: second call is a cache hit; the loader's side_effect yields
            #   "cached_response", so that (not the loader's return_value) is returned.
            expected = (mock_process.return_value, "cached_response")
            found = (response_1, response_2)
            self.assertEqual(expected, found)

        with self.subTest("attemps to load from cache twice"):
            expected = 2
            found = mock_lcache.call_count
            self.assertEqual(expected, found)

        with self.subTest("saved to cache once"):
            expected = [mock.call(kwargs["prompt"], mock_process.return_value)]
            found = mock_scache.mock_calls
            self.assertEqual(expected, found)

    def test_default_load_cache_returns_none_on_miss(self) -> None:
        mock_cache = mock.MagicMock()
        mock_cache.load_from_cache.side_effect = MOD.cachemanager.CacheMissError
        with mock.patch.object(MOD.cachemanager, "get_cache", return_value=mock_cache):
            result = MOD._default_load_cache("prompt")
        self.assertIsNone(result)

    def test_default_load_cache_returns_none_on_invalid_cache(self) -> None:
        mock_cache = mock.MagicMock()
        mock_cache.load_from_cache.side_effect = MOD.cachemanager.InvalidCacheError
        with mock.patch.object(MOD.cachemanager, "get_cache", return_value=mock_cache):
            result = MOD._default_load_cache("prompt")
        self.assertIsNone(result)

    def test_default_save_cache_calls_save(self) -> None:
        mock_cache = mock.MagicMock()
        with mock.patch.object(MOD.cachemanager, "get_cache", return_value=mock_cache):
            MOD._default_save_cache("prompt_key", {"data": 1})
        mock_cache.save_to_cache.assert_called_once_with("prompt_key", {"data": 1})

    def test_use_cache_true_wires_default_load_and_save(self) -> None:
        mock_service = mock.MagicMock(__name__="svc", return_value='{"ok": true}')
        with (
            mock.patch.object(
                MOD, "_default_load_cache", return_value=None
            ) as mock_load,
            mock.patch.object(MOD, "_default_save_cache") as mock_save,
        ):
            MOD.query_ai_service(
                prompt="test", use_cache=True, _query_service=mock_service
            )
        mock_load.assert_called_once()
        mock_save.assert_called_once()

    def test_extract_json_from_response_by_default(self) -> None:
        mock_service = mock.MagicMock(__name__="service")

        kwargs = {"max_attempt": 5, "prompt": "... some text ...", "use_cache": False}
        inject = {"_query_service": mock_service}

        with mock.patch.object(MOD, "process_response_json") as mobj:
            response_1 = MOD.query_ai_service(**kwargs, **inject)

        with self.subTest("processed json by default"):
            expected = [mock.call(mock_service.return_value)]
            found = mobj.mock_calls
            self.assertEqual(expected, found)

        with self.subTest("returned processed json"):
            expected = mobj.return_value
            found = response_1
            self.assertEqual(expected, found)


# __END__
