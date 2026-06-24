#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.experience as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def roles_for(self, companies: list[str]) -> list[MOD.Role]:
        """Return one Role per company, titled ``r0``, ``r1``, … to track order."""
        return [
            MOD.Role(company=company, title=f"r{i}")
            for i, company in enumerate(companies)
        ]


class TestRole(ThisTestCase):
    """Test dataclass."""

    def test_optional_fields_default_empty(self) -> None:
        subject = MOD.Role(company="C", title="T")
        cases = [
            # (expected, attribute)
            ("", "location"),
            ("", "start"),
            ("", "end"),
            (False, "current"),
            ("", "description"),
        ]
        for expected, attr in cases:
            with self.subTest(attr):
                self.assertEqual(expected, getattr(subject, attr))

    def test_frozen(self) -> None:
        subject = MOD.Role(company="C", title="T")
        with self.assertRaises((AttributeError, TypeError)):
            subject.company = "X"  # type: ignore[misc]


class TestRoleBullets(ThisTestCase):
    """Test method."""

    def test_parses_markers_and_drops_blank_lines(self) -> None:
        tests = [
            # (expected, given_description)
            ((), ""),
            (("one",), "- one"),
            (("one", "two"), "- one\n- two"),
            (("one", "two"), "* one\n• two"),
            (("one",), "\n- one\n\n"),
            (("plain",), "plain"),
            (("indented",), "    - indented"),
        ]
        for expected, given in tests:
            with self.subTest(given):
                found = MOD.Role(company="C", title="T", description=given).bullets()
                self.assertEqual(expected, found)


class TestExperienceSet(ThisTestCase):
    """Test dataclass."""

    def test_roles_default_to_empty_tuple(self) -> None:
        self.assertEqual((), MOD.ExperienceSet().roles)


class TestExperienceSetGrouped(ThisTestCase):
    """Test method."""

    def test_groups_consecutive_same_company(self) -> None:
        tests = [
            # (expected_blocks, given_companies); expected block = (company, role_count)
            ([], []),
            ([("A", 1)], ["A"]),
            ([("A", 2)], ["A", "A"]),
            ([("A", 1), ("B", 1)], ["A", "B"]),
            # left and rejoined the same company → two separate blocks, not merged
            ([("A", 1), ("B", 1), ("A", 1)], ["A", "B", "A"]),
            # a promotion (adjacent) groups; the earlier employer stays its own block
            ([("Lattice", 2), ("Meridian", 1)], ["Lattice", "Lattice", "Meridian"]),
        ]
        for expected, given in tests:
            with self.subTest(given):
                subject = MOD.make_experience_set(self.roles_for(given))
                found = [(b.company, len(b.roles)) for b in subject.grouped()]
                self.assertEqual(expected, found)

    def test_preserves_role_order_within_a_block(self) -> None:
        subject = MOD.make_experience_set(self.roles_for(["A", "A"]))
        (block,) = subject.grouped()
        self.assertEqual(("r0", "r1"), tuple(r.title for r in block.roles))


class TestMakeExperienceSet(ThisTestCase):
    """Test factory function."""

    def test_wraps_roles_in_tuple(self) -> None:
        subject = MOD.make_experience_set(self.roles_for(["A", "B"]))
        self.assertIsInstance(subject.roles, tuple)

    def test_preserves_order(self) -> None:
        subject = MOD.make_experience_set(self.roles_for(["A", "B", "C"]))
        self.assertEqual(("A", "B", "C"), tuple(r.company for r in subject.roles))

    def test_empty_roles(self) -> None:
        self.assertEqual((), MOD.make_experience_set([]).roles)


# __END__
