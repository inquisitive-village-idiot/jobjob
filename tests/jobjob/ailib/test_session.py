#!/usr/bin/env python3
"""Test."""

import base64
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock

import jobjob.ailib.session as MOD
from jobjob.ailib.client.base import AIResult

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_adapter(self, *results) -> mock.MagicMock:
        adapter = mock.MagicMock()
        adapter.complete.side_effect = list(results)
        return adapter


def _usage(**kwargs) -> SimpleNamespace:
    defaults = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestCall(ThisTestCase):
    """Test __call__."""

    def test_returns_adapter_text(self) -> None:
        adapter = self.make_adapter(AIResult(text="hi", usage=_usage()))
        client = MOD.AIClient(adapter)
        self.assertEqual("hi", client("q"))

    def test_passes_cached_context_as_system(self) -> None:
        adapter = self.make_adapter(AIResult(text="x", usage=_usage()))
        client = MOD.AIClient(adapter)
        client.set_cached_context("CTX")
        client("q")
        _, kwargs = adapter.complete.call_args
        self.assertEqual("CTX", kwargs["system"])

    def test_accumulates_usage_across_calls(self) -> None:
        adapter = self.make_adapter(
            AIResult(text="a", usage=_usage(input_tokens=10)),
            AIResult(text="b", usage=_usage(input_tokens=3, cache_read_input_tokens=5)),
        )
        client = MOD.AIClient(adapter)
        client("a")
        client("b")
        self.assertEqual(13, client.usage.input_tokens)
        self.assertEqual(5, client.usage.cache_read_input_tokens)

    def test_tolerates_missing_usage(self) -> None:
        adapter = self.make_adapter(AIResult(text="a", usage=None))
        client = MOD.AIClient(adapter)
        self.assertEqual("a", client("q"))
        self.assertEqual(0, client.usage.input_tokens)


class TestCompleteDocument(ThisTestCase):
    """Test method."""

    def test_attaches_base64_pdf(self) -> None:
        adapter = self.make_adapter(AIResult(text="ok", usage=_usage()))
        client = MOD.AIClient(adapter)

        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name, "doc.pdf")
        path.write_bytes(b"%PDF-1.4 hello")

        out = client.complete_document("extract", path)

        self.assertEqual("ok", out)
        _, kwargs = adapter.complete.call_args
        media_type, data = kwargs["document"]
        self.assertEqual("application/pdf", media_type)
        self.assertEqual(base64.standard_b64encode(b"%PDF-1.4 hello").decode(), data)


# __END__
