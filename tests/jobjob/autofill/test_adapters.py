#!/usr/bin/env python3
"""Test."""

import dataclasses as dcs
import logging
from unittest import TestCase

import jobjob.autofill.adapters as MOD

LOGGER = logging.getLogger(__name__)


@dcs.dataclass
class FakeAdapter:
    """Minimal adapter that matches URLs containing a token."""

    name: str
    token: str

    def matches(self, url: str) -> bool:
        return self.token in url

    def fill(self, page, data):  # pragma: no cover - unused in selection tests
        raise NotImplementedError


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestSelectAdapter(ThisTestCase):
    """Test function."""

    def setUp(self) -> None:
        self.adapters = (
            FakeAdapter(name="alpha", token="alpha.com"),
            FakeAdapter(name="beta", token="beta.com"),
        )

    def test_returns_first_match(self) -> None:
        tests = [
            # (expected_name, url)
            ("alpha", "https://x.alpha.com/job"),
            ("beta", "https://y.beta.com/job"),
        ]
        for expected, url in tests:
            with self.subTest(url):
                found = MOD.select_adapter(url, self.adapters)
                self.assertEqual(expected, found.name)

    def test_returns_none_when_no_match(self) -> None:
        self.assertIsNone(MOD.select_adapter("https://gamma.com", self.adapters))

    def test_default_registry_routes_known_hosts(self) -> None:
        tests = [
            # (expected_name, url)
            ("workday", "https://acme.myworkdayjobs.com/job"),
            ("greenhouse", "https://boards.greenhouse.io/acme/jobs/1"),
        ]
        for expected, url in tests:
            with self.subTest(url):
                self.assertEqual(expected, MOD.select_adapter(url).name)


# __END__
