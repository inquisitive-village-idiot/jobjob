#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.autofill.adapters._common as MOD
from jobjob.autofill.report import FilledField, FlaggedField

LOGGER = logging.getLogger(__name__)


class FakeLocator:
    """Minimal Playwright-Locator stand-in: present/absent + capture .fill()."""

    def __init__(self, present: bool) -> None:
        self._present = present
        self.filled: str | None = None

    def count(self) -> int:
        return 1 if self._present else 0

    @property
    def first(self) -> "FakeLocator":
        return self

    def fill(self, value: str) -> None:
        self.filled = value


class FakePage:
    """Minimal Page stand-in: ``.locator(sel)`` resolves against a present set."""

    def __init__(self, present: set[str]) -> None:
        self._present = present
        self.locators: dict[str, FakeLocator] = {}

    def locator(self, selector: str) -> FakeLocator:
        if selector not in self.locators:
            self.locators[selector] = FakeLocator(selector in self._present)
        return self.locators[selector]


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestSplitName(ThisTestCase):
    """Test function."""

    def test_splits_on_last_whitespace(self) -> None:
        tests = [
            # (expected, given)
            (("", ""), None),
            (("", ""), "   "),
            (("Cher", ""), "Cher"),
            (("Ada", "Lovelace"), "Ada Lovelace"),
            (("Ada B.", "Lovelace"), "Ada B. Lovelace"),
        ]
        for expected, given in tests:
            with self.subTest(given):
                self.assertEqual(expected, MOD.split_name(given))


class TestFindFirst(ThisTestCase):
    """Test function."""

    def test_returns_first_present_selector(self) -> None:
        page = FakePage(present={"#b", "#c"})
        found = MOD.find_first(page, ["#a", "#b", "#c"])
        self.assertIs(page.locator("#b"), found)

    def test_returns_none_when_none_present(self) -> None:
        page = FakePage(present=set())
        self.assertIsNone(MOD.find_first(page, ["#a", "#b"]))


class TestFillContactField(ThisTestCase):
    """Test function."""

    def setUp(self) -> None:
        self.filled: list[FilledField] = []
        self.flagged: list[FlaggedField] = []

    def _fill(self, page: FakePage, value: str, *, required: bool) -> None:
        MOD.fill_contact_field(
            page,
            ["#email"],
            value,
            "Email",
            required=required,
            filled=self.filled,
            flagged=self.flagged,
        )

    def test_fills_present_field_with_value(self) -> None:
        page = FakePage(present={"#email"})
        self._fill(page, "ada@example.com", required=True)
        with self.subTest("recorded as filled"):
            self.assertEqual([FilledField("Email", "ada@example.com")], self.filled)
        with self.subTest("written to the field"):
            self.assertEqual("ada@example.com", page.locator("#email").filled)
        with self.subTest("nothing flagged"):
            self.assertEqual([], self.flagged)

    def test_flags_required_field_with_no_value(self) -> None:
        page = FakePage(present={"#email"})
        self._fill(page, "", required=True)
        self.assertEqual(1, len(self.flagged))
        self.assertEqual("Email", self.flagged[0].label)
        self.assertEqual([], self.filled)

    def test_skips_optional_field_with_no_value(self) -> None:
        page = FakePage(present={"#email"})
        self._fill(page, "", required=False)
        self.assertEqual(([], []), (self.filled, self.flagged))

    def test_absent_field_is_skipped_silently(self) -> None:
        page = FakePage(present=set())
        self._fill(page, "ada@example.com", required=True)
        self.assertEqual(([], []), (self.filled, self.flagged))


# __END__
