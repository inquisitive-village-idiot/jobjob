#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.autofill.adapters.workday as MOD
from jobjob.structure.experience import Role

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestSplitName(ThisTestCase):
    """Test function."""

    def test_splits_on_last_whitespace(self) -> None:
        tests = [
            # (expected, given)
            (("", ""), None),
            (("", ""), ""),
            (("", ""), "   "),
            (("Cher", ""), "Cher"),
            (("Ada", "Lovelace"), "Ada Lovelace"),
            (("Ada B.", "Lovelace"), "Ada B. Lovelace"),
            (("Ada", "Lovelace"), "  Ada Lovelace  "),
        ]
        for expected, given in tests:
            with self.subTest(given):
                self.assertEqual(expected, MOD.split_name(given))


class TestFormatDescription(ThisTestCase):
    """Test function."""

    def _role(self, description: str) -> Role:
        return Role(company="C", title="T", description=description)

    def test_renders_bullets(self) -> None:
        tests = [
            # (expected, given_description)
            ("", ""),
            ("", "   \n  "),  # only blank lines -> empty
            ("• one", "- one"),
            ("• one\n• two", "- one\n- two"),
            ("• one\n• two", "* one\n• two"),
            # an unmarked line still becomes a bullet (content is never dropped)
            ("• plain", "plain"),
        ]
        for expected, given in tests:
            with self.subTest(given):
                self.assertEqual(expected, MOD.format_description(self._role(given)))


class TestWorkdayAdapterMatches(ThisTestCase):
    """Test method."""

    def setUp(self) -> None:
        self.subject = MOD.WorkdayAdapter()

    def test_recognizes_workday_hosts(self) -> None:
        tests = [
            # (expected, url)
            (True, "https://acme.wd5.myworkdayjobs.com/en-US/careers/job/x"),
            (True, "https://impl.workday.com/acme/d/inst/1/9925$1.htmld"),
            (True, "HTTPS://ACME.MYWORKDAYJOBS.COM/job"),
            (False, "https://boards.greenhouse.io/acme/jobs/123"),
            (False, "https://jobs.lever.co/acme/abc"),
            (False, ""),
        ]
        for expected, url in tests:
            with self.subTest(url):
                self.assertEqual(expected, self.subject.matches(url))


# __END__
