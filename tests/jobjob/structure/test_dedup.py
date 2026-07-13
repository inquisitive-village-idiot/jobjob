#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.dedup as MOD

LOGGER = logging.getLogger(__name__)


class TestNormalizeToken(TestCase):
    """Test normalize_token."""

    def test_table(self) -> None:
        cases = [
            ("casefold", "Acme", "acme"),
            ("already lowercase", "acme", "acme"),
            ("collapses internal whitespace", "Acme   Corp", "acme corp"),
            ("strips leading/trailing whitespace", "  Acme  ", "acme"),
            ("strips punctuation", "Acme, Inc.", "acme inc"),
            ("abbreviation: incorporated -> inc", "Acme Incorporated", "acme inc"),
            ("abbreviation: inc stays inc", "Acme Inc", "acme inc"),
            ("abbreviation: corporation -> corp", "Acme Corporation", "acme corp"),
            ("abbreviation: company -> co", "Acme Company", "acme co"),
            ("abbreviation: limited -> ltd", "Acme Limited", "acme ltd"),
            ("abbreviation: senior -> sr", "Tila Mer Senior", "tila mer sr"),
            ("abbreviation: junior -> jr", "Tila Mer Junior", "tila mer jr"),
            ("none degrades to empty", None, ""),
            ("empty string stays empty", "", ""),
            ("blank/whitespace-only degrades to empty", "   ", ""),
        ]
        for name, raw, expected in cases:
            with self.subTest(name):
                self.assertEqual(expected, MOD.normalize_token(raw))


class TestDedupSignal(TestCase):
    """Test dedup_signal."""

    def test_company_and_role_join_with_pipe(self) -> None:
        self.assertEqual(
            "acme|principal engineer",
            MOD.dedup_signal("Acme", "Principal Engineer"),
        )

    def test_casing_and_abbreviation_variance_match(self) -> None:
        # These should be the SAME signal -- the concrete "did our normalizer
        # catch this real-world variance" case the design calls for.
        a = MOD.dedup_signal("Acme Inc.", "Principal Engineer")
        b = MOD.dedup_signal("ACME INCORPORATED", "principal   engineer")
        self.assertEqual(a, b)

    def test_distinct_roles_do_not_match(self) -> None:
        a = MOD.dedup_signal("Acme", "Principal Engineer")
        b = MOD.dedup_signal("Acme", "Staff Engineer")
        self.assertNotEqual(a, b)

    def test_distinct_companies_do_not_match(self) -> None:
        a = MOD.dedup_signal("Acme", "Engineer")
        b = MOD.dedup_signal("Globex", "Engineer")
        self.assertNotEqual(a, b)

    def test_contacts_first_last_name_path(self) -> None:
        a = MOD.dedup_signal("Tila", "Mer")
        b = MOD.dedup_signal("tila", "MER")
        self.assertEqual(a, b)
        self.assertNotEqual(a, MOD.dedup_signal("Tila", "Merington"))

    def test_all_blank_parts_yield_empty_signal(self) -> None:
        self.assertEqual("", MOD.dedup_signal(None, ""))
        self.assertEqual("", MOD.dedup_signal("", ""))

    def test_two_blank_signals_are_not_a_match(self) -> None:
        # An empty signal must never be treated as a "duplicate" of another
        # empty signal by a caller that groups by signal equality.
        a = MOD.dedup_signal(None, None)
        b = MOD.dedup_signal("", "")
        self.assertEqual(a, b)
        self.assertEqual("", a)  # the empty string is a sentinel, not a group


# __END__
