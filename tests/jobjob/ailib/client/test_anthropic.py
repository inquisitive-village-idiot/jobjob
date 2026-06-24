#!/usr/bin/env python3
"""Test."""

import logging
from types import SimpleNamespace
from unittest import TestCase, mock

import anthropic

import jobjob.ailib.client.anthropic as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_adapter(self, text: str = "hello") -> tuple:
        mock_sdk = mock.MagicMock()
        mock_sdk.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(text=text)],
            usage=SimpleNamespace(input_tokens=1, output_tokens=2),
        )
        adapter = MOD.AnthropicAdapter(model="claude-sonnet-4-6", _client=mock_sdk)
        return adapter, mock_sdk


class TestInit(ThisTestCase):
    """Test construction."""

    def test_raises_without_client_or_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "API key"):
            MOD.AnthropicAdapter(model="claude-sonnet-4-6")

    def test_passes_base_url_to_client(self) -> None:
        with mock.patch.object(MOD.anthropic, "Anthropic") as ctor:
            MOD.AnthropicAdapter(
                model="claude-sonnet-4-6",
                api_key="sk-test",
                base_url="http://localhost:3000",
            )
        _, kwargs = ctor.call_args
        self.assertEqual("http://localhost:3000", kwargs["base_url"])

    def test_base_url_defaults_to_none(self) -> None:
        with mock.patch.object(MOD.anthropic, "Anthropic") as ctor:
            MOD.AnthropicAdapter(model="claude-sonnet-4-6", api_key="sk-test")
        _, kwargs = ctor.call_args
        self.assertIsNone(kwargs["base_url"])


class TestComplete(ThisTestCase):
    """Test method."""

    def test_returns_result_with_text_and_usage(self) -> None:
        adapter, _ = self.make_adapter(text="answer")
        result = adapter.complete("q")
        self.assertEqual("answer", result.text)
        self.assertEqual(1, result.usage.input_tokens)

    def test_omits_system_when_no_context(self) -> None:
        adapter, mock_sdk = self.make_adapter()
        adapter.complete("hi")
        _, kwargs = mock_sdk.messages.create.call_args
        self.assertNotIn("system", kwargs)

    def test_sends_cached_system_block(self) -> None:
        adapter, mock_sdk = self.make_adapter()
        adapter.complete("hi", system="STABLE")
        _, kwargs = mock_sdk.messages.create.call_args
        block = kwargs["system"][0]
        self.assertEqual("STABLE", block["text"])
        self.assertEqual({"type": "ephemeral"}, block["cache_control"])

    def test_sends_document_block_when_given(self) -> None:
        adapter, mock_sdk = self.make_adapter()
        adapter.complete("read this", document=("application/pdf", "BASE64DATA"))
        _, kwargs = mock_sdk.messages.create.call_args
        content = kwargs["messages"][0]["content"]
        with self.subTest("document block first"):
            self.assertEqual("document", content[0]["type"])
            self.assertEqual("application/pdf", content[0]["source"]["media_type"])
            self.assertEqual("BASE64DATA", content[0]["source"]["data"])
        with self.subTest("prompt text follows"):
            self.assertEqual("read this", content[1]["text"])

    def test_string_content_when_no_document(self) -> None:
        adapter, mock_sdk = self.make_adapter()
        adapter.complete("hi")
        _, kwargs = mock_sdk.messages.create.call_args
        self.assertEqual("hi", kwargs["messages"][0]["content"])

    def test_remaps_api_timeout(self) -> None:
        adapter, mock_sdk = self.make_adapter()
        mock_sdk.messages.create.side_effect = anthropic.APITimeoutError(
            request=mock.Mock()
        )
        with self.assertRaises(TimeoutError):
            adapter.complete("q")


# __END__
