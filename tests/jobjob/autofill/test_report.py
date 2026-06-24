#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.autofill.report as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestMakeFillReport(ThisTestCase):
    """Test factory function."""

    def test_wraps_fields_in_tuples(self) -> None:
        report = MOD.make_fill_report(
            "workday",
            [MOD.FilledField("First name", "Ada")],
            [MOD.FlaggedField("Start date", "widget")],
        )
        cases = [
            # (expected, found)
            ("workday", report.adapter),
            ((MOD.FilledField("First name", "Ada"),), report.filled),
            ((MOD.FlaggedField("Start date", "widget"),), report.flagged),
        ]
        for expected, found in cases:
            with self.subTest(expected):
                self.assertEqual(expected, found)

    def test_defaults_to_empty(self) -> None:
        report = MOD.make_fill_report("workday")
        self.assertEqual(((), ()), (report.filled, report.flagged))


class TestFillReportRender(ThisTestCase):
    """Test method."""

    def test_names_adapter_and_filled_count(self) -> None:
        report = MOD.make_fill_report("workday", [MOD.FilledField("Email", "a@b.co")])
        text = report.render()
        with self.subTest("adapter"):
            self.assertIn("workday", text)
        with self.subTest("filled count"):
            self.assertIn("filled 1 field(s)", text)
        with self.subTest("field line"):
            self.assertIn("Email: a@b.co", text)

    def test_omits_flagged_section_when_none(self) -> None:
        report = MOD.make_fill_report("workday", [MOD.FilledField("Email", "a@b.co")])
        self.assertNotIn("flagged", report.render())

    def test_lists_flagged_fields_with_reason(self) -> None:
        report = MOD.make_fill_report(
            "workday", flagged=[MOD.FlaggedField("Start date", "custom widget")]
        )
        text = report.render()
        with self.subTest("count"):
            self.assertIn("flagged 1 field(s)", text)
        with self.subTest("reason"):
            self.assertIn("Start date — custom widget", text)


# __END__
