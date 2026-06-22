#!/usr/bin/env python3
"""Test."""

import logging
from types import SimpleNamespace
from unittest import TestCase

import jobjob.structure.token_usage as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_usage(self, **kwargs) -> SimpleNamespace:
        defaults = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)


class TestAdd(ThisTestCase):
    """Test method."""

    def test_accumulates_across_responses(self) -> None:
        usage = MOD.TokenUsage()
        usage.add(self.make_usage(input_tokens=10, output_tokens=5))
        usage.add(
            self.make_usage(
                input_tokens=3,
                cache_read_input_tokens=100,
                cache_creation_input_tokens=2,
            )
        )

        expected = (13, 5, 2, 100)
        found = (
            usage.input_tokens,
            usage.output_tokens,
            usage.cache_creation_input_tokens,
            usage.cache_read_input_tokens,
        )
        self.assertEqual(expected, found)

    def test_tolerates_missing_cache_fields(self) -> None:
        usage = MOD.TokenUsage()
        usage.add(SimpleNamespace(input_tokens=4, output_tokens=1))

        expected = (4, 1, 0, 0)
        found = (
            usage.input_tokens,
            usage.output_tokens,
            usage.cache_creation_input_tokens,
            usage.cache_read_input_tokens,
        )
        self.assertEqual(expected, found)


class TestSummary(ThisTestCase):
    """Test method."""

    def test_reports_cache_hit_percentage(self) -> None:
        usage = MOD.TokenUsage(input_tokens=0, cache_read_input_tokens=100)
        found = usage.summary()
        self.assertIn("100.0% from cache", found)

    def test_handles_zero_total_without_error(self) -> None:
        found = MOD.TokenUsage().summary()
        self.assertIn("0.0% from cache", found)


# __END__
