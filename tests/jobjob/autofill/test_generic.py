#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.autofill.adapters as REG
import jobjob.autofill.adapters.generic as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestGenericAdapterMatches(ThisTestCase):
    """Test method."""

    def setUp(self) -> None:
        self.subject = MOD.GenericAdapter()

    def test_matches_any_url(self) -> None:
        urls = [
            "https://careers.acme.com/apply/123",
            "https://acme.myworkdayjobs.com/job",  # named host, but generic still True
            "https://unknown.example.org/jobs/1",
            "",
        ]
        for url in urls:
            with self.subTest(url):
                self.assertTrue(self.subject.matches(url))


class TestGenericInRegistry(ThisTestCase):
    """Test the registry wiring that the generic fallback depends on."""

    def test_generic_is_registered_last(self) -> None:
        # The catch-all must be last, or it would shadow every named adapter.
        self.assertIsInstance(REG.ADAPTERS[-1], MOD.GenericAdapter)

    def test_named_adapters_take_precedence(self) -> None:
        found = REG.select_adapter("https://acme.myworkdayjobs.com/job")
        self.assertEqual("workday", found.name)

    def test_unknown_host_falls_back_to_generic(self) -> None:
        found = REG.select_adapter("https://careers.acme.com/apply/123")
        self.assertEqual("generic", found.name)


# __END__
