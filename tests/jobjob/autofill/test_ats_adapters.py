#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

from jobjob.autofill.adapters.ashby import AshbyAdapter
from jobjob.autofill.adapters.lever import LeverAdapter
from jobjob.autofill.adapters.smartrecruiters import SmartRecruitersAdapter
from jobjob.autofill.adapters.workable import WorkableAdapter

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestLeverMatches(ThisTestCase):
    """Test method."""

    def test_recognizes_lever(self) -> None:
        tests = [
            # (expected, url)
            (True, "https://jobs.lever.co/acme/abc-123"),
            (True, "HTTPS://JOBS.LEVER.CO/acme"),
            (False, "https://boards.greenhouse.io/acme"),
            (False, ""),
        ]
        for expected, url in tests:
            with self.subTest(url):
                self.assertEqual(expected, LeverAdapter().matches(url))


class TestAshbyMatches(ThisTestCase):
    """Test method."""

    def test_recognizes_ashby(self) -> None:
        tests = [
            (True, "https://jobs.ashbyhq.com/acme/role"),
            (False, "https://jobs.lever.co/acme"),
            (False, ""),
        ]
        for expected, url in tests:
            with self.subTest(url):
                self.assertEqual(expected, AshbyAdapter().matches(url))


class TestWorkableMatches(ThisTestCase):
    """Test method."""

    def test_recognizes_workable(self) -> None:
        tests = [
            (True, "https://apply.workable.com/acme/j/ABCDEF/"),
            (True, "https://acme.workable.com/jobs/123"),
            (False, "https://jobs.ashbyhq.com/acme"),
            (False, ""),
        ]
        for expected, url in tests:
            with self.subTest(url):
                self.assertEqual(expected, WorkableAdapter().matches(url))


class TestSmartRecruitersMatches(ThisTestCase):
    """Test method."""

    def test_recognizes_smartrecruiters(self) -> None:
        tests = [
            (True, "https://jobs.smartrecruiters.com/Acme/12345-role"),
            (False, "https://apply.workable.com/acme/j/ABC/"),
            (False, ""),
        ]
        for expected, url in tests:
            with self.subTest(url):
                self.assertEqual(expected, SmartRecruitersAdapter().matches(url))


# __END__
