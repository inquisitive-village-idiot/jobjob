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


# __END__
