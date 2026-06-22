#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.ailib.processresponse as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestProcessResponseJson(ThisTestCase):
    """Test function."""

    def test_parses_bare_json_object(self) -> None:
        expected = {"a": 1, "b": [2, 3]}
        found = MOD.process_response_json('{"a": 1, "b": [2, 3]}')
        self.assertEqual(expected, found)

    def test_parses_bare_json_array(self) -> None:
        expected = ["x", "y"]
        found = MOD.process_response_json('["x", "y"]')
        self.assertEqual(expected, found)

    def test_parses_fenced_json_block(self) -> None:
        text = 'Here you go:\n```json\n{"k": "v"}\n```\nThanks!'
        expected = {"k": "v"}
        found = MOD.process_response_json(text)
        self.assertEqual(expected, found)

    def test_extracts_object_embedded_in_prose(self) -> None:
        text = 'The result is {"score": 9} overall.'
        expected = {"score": 9}
        found = MOD.process_response_json(text)
        self.assertEqual(expected, found)

    def test_raises_value_error_when_no_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "No valid JSON"):
            MOD.process_response_json("there is nothing structured here")

    def test_falls_through_fenced_invalid_json_to_regex_array(self) -> None:
        # Fenced block contains invalid JSON; the response also has a valid array
        # that the array regex pattern matches.
        text = "```\ninvalid content\n```\n[1, 2, 3]"
        result = MOD.process_response_json(text)
        self.assertEqual([1, 2, 3], result)

    def test_falls_through_fenced_and_regex_when_both_invalid(self) -> None:
        # Both the fenced block and any regex-extracted snippet are invalid JSON.
        text = "```json\n{bad}\n```\nand {also bad} here"
        with self.assertRaisesRegex(ValueError, "No valid JSON"):
            MOD.process_response_json(text)

    def test_regex_match_invalid_json_falls_through_to_next_pattern(self) -> None:
        # The first regex (object pattern) matches but the content is invalid JSON;
        # falls through to the array pattern, which also fails.
        text = "result: {not:json}"
        with self.assertRaisesRegex(ValueError, "No valid JSON"):
            MOD.process_response_json(text)


# __END__
