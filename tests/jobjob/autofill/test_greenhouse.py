#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.autofill.adapters.greenhouse as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestGreenhouseAdapterMatches(ThisTestCase):
    """Test method."""

    def setUp(self) -> None:
        self.subject = MOD.GreenhouseAdapter()

    def test_recognizes_greenhouse_hosts(self) -> None:
        tests = [
            # (expected, url)
            (True, "https://boards.greenhouse.io/acme/jobs/123"),
            (True, "https://job-boards.greenhouse.io/acme/jobs/123"),
            (True, "HTTPS://BOARDS.GREENHOUSE.IO/acme"),
            (False, "https://acme.myworkdayjobs.com/job"),
            (False, "https://jobs.lever.co/acme/abc"),
            (False, ""),
        ]
        for expected, url in tests:
            with self.subTest(url):
                self.assertEqual(expected, self.subject.matches(url))


# __END__
