#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.applicant as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestApplicant(ThisTestCase):
    """Test Applicant dataclass."""

    def test_all_fields_optional(self) -> None:
        a = MOD.Applicant()
        self.assertIsNone(a.name)
        self.assertIsNone(a.phone)
        self.assertIsNone(a.email)
        self.assertIsNone(a.linkedin)

    def test_stores_provided_fields(self) -> None:
        a = MOD.Applicant(name="Jane", phone="555-1234", email="j@example.com")
        self.assertEqual("Jane", a.name)
        self.assertEqual("555-1234", a.phone)
        self.assertEqual("j@example.com", a.email)

    def test_frozen(self) -> None:
        a = MOD.Applicant(name="Jane")
        with self.assertRaises((AttributeError, TypeError)):
            a.name = "John"  # type: ignore[misc]


class TestContactLine(ThisTestCase):
    """Test contact_line method."""

    def test_all_fields(self) -> None:
        a = MOD.Applicant(
            phone="555-1234", email="j@x.com", linkedin="linkedin.com/in/j"
        )
        self.assertEqual("555-1234 | j@x.com | linkedin.com/in/j", a.contact_line())

    def test_omits_unset_fields(self) -> None:
        a = MOD.Applicant(email="j@x.com")
        self.assertEqual("j@x.com", a.contact_line())

    def test_empty_when_all_none(self) -> None:
        a = MOD.Applicant()
        self.assertEqual("", a.contact_line())

    def test_phone_and_email_only(self) -> None:
        a = MOD.Applicant(phone="555-0000", email="a@b.com")
        self.assertEqual("555-0000 | a@b.com", a.contact_line())


class TestFirstLastName(ThisTestCase):
    """Test the FirstLast derivation (design D8)."""

    def test_none_returns_empty(self) -> None:
        self.assertEqual("", MOD.first_last_name(None))

    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual("", MOD.first_last_name(""))

    def test_plain_name(self) -> None:
        self.assertEqual("TilaMer", MOD.first_last_name("Tila Mer"))

    def test_credential_dropped(self) -> None:
        self.assertEqual("TilaMer", MOD.first_last_name("Tila Mer, PhD"))

    def test_multiple_credentials_all_dropped(self) -> None:
        self.assertEqual("TilaMer", MOD.first_last_name("Tila Mer, MD, MBA"))

    def test_generational_suffix_kept_without_comma(self) -> None:
        self.assertEqual("TilaMerJr", MOD.first_last_name("Tila Mer Jr"))

    def test_generational_suffix_kept_with_comma(self) -> None:
        self.assertEqual("TilaMerJr", MOD.first_last_name("Tila Mer, Jr."))

    def test_senior_suffix_kept(self) -> None:
        self.assertEqual("TilaMerSr", MOD.first_last_name("Tila Mer Sr"))

    def test_roman_numeral_suffix_kept(self) -> None:
        self.assertEqual("TilaMerIII", MOD.first_last_name("Tila Mer III"))

    def test_roman_numeral_suffix_kept_with_comma(self) -> None:
        self.assertEqual("TilaMerIII", MOD.first_last_name("Tila Mer, III"))

    def test_suffix_and_credential_combined(self) -> None:
        self.assertEqual("TilaMerJr", MOD.first_last_name("Tila Mer Jr, PhD"))

    def test_strips_punctuation(self) -> None:
        self.assertEqual("MaryJaneOBrien", MOD.first_last_name("Mary-Jane O'Brien"))

    def test_preserves_internal_capitals(self) -> None:
        self.assertEqual("TilaMcMer", MOD.first_last_name("Tila McMer"))

    def test_single_word_name_not_mistaken_for_suffix(self) -> None:
        # A lone word must never be popped off as a "suffix" (nothing would be
        # left of the name).
        self.assertEqual("Cher", MOD.first_last_name("Cher"))


# __END__
