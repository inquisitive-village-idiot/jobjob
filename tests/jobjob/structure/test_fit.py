#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.fit as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestFit(ThisTestCase):
    """Test Fit dataclass."""

    def test_required_fields(self) -> None:
        fit = MOD.Fit(band=MOD.BAND_STRONG, summary="Great match")
        self.assertEqual(MOD.BAND_STRONG, fit.band)
        self.assertEqual("Great match", fit.summary)

    def test_optional_strengths_and_weaknesses_default_empty(self) -> None:
        fit = MOD.Fit(band=MOD.BAND_MODERATE, summary="Decent")
        self.assertEqual((), fit.strengths)
        self.assertEqual((), fit.weaknesses)

    def test_optional_fit_scores_default_none(self) -> None:
        fit = MOD.Fit(band=MOD.BAND_WEAK, summary="Weak")
        self.assertIsNone(fit.role_fit)
        self.assertIsNone(fit.preference_fit)

    def test_stores_strengths_and_weaknesses(self) -> None:
        fit = MOD.Fit(
            band=MOD.BAND_STRONG,
            summary="Good",
            strengths=("writing", "python"),
            weaknesses=("frontend",),
        )
        self.assertEqual(("writing", "python"), fit.strengths)
        self.assertEqual(("frontend",), fit.weaknesses)

    def test_stores_fit_scores(self) -> None:
        fit = MOD.Fit(
            band=MOD.BAND_MODERATE,
            summary="Good",
            role_fit=0.8,
            preference_fit=0.6,
        )
        self.assertAlmostEqual(0.8, fit.role_fit)
        self.assertAlmostEqual(0.6, fit.preference_fit)

    def test_frozen(self) -> None:
        fit = MOD.Fit(band=MOD.BAND_STRONG, summary="X")
        with self.assertRaises((AttributeError, TypeError)):
            fit.band = MOD.BAND_WEAK  # type: ignore[misc]

    def test_band_constants(self) -> None:
        self.assertEqual("Strong", MOD.BAND_STRONG)
        self.assertEqual("Moderate", MOD.BAND_MODERATE)
        self.assertEqual("Weak", MOD.BAND_WEAK)


# __END__
