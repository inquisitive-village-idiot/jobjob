#!/usr/bin/env python3
"""Fit assessment of a candidate against a role."""

import dataclasses as dcs
from typing import Optional

# Qualitative bands (sufficient for now).
BAND_STRONG = "Strong"
BAND_MODERATE = "Moderate"
BAND_WEAK = "Weak"


@dcs.dataclass(frozen=True)
class FitCategory:
    """One scored category on a fit axis.

    Attributes:
        name: Category name (role axis: skill-cloud vocabulary; preference
            axis: model-chosen label).
        score: Category score in [0.0, 1.0].
        note: One-line justification. Role-axis notes list the contributing
            skills; preference-axis notes carry the model's reasoning.
    """

    name: str
    score: float
    note: str = ""


@dcs.dataclass(frozen=True)
class Fit:
    """A two-axis fit assessment.

    The qualitative band is derived deterministically from the skills analysis.
    The quantitative axes are additive: role fit is computed in code over the
    canonical skill join (measurement); preference fit is model-judged against
    the background document (assessment). Either may be None (older cached
    analyses, insufficient canonical coverage) -- consumers render what exists.

    Attributes:
        band: Qualitative band (Strong / Moderate / Weak).
        summary: A brief one-line summary of strengths and gaps.
        strengths: Supported skills, for the side-by-side fit table.
        weaknesses: Critical gaps, for the side-by-side fit table.
        role_fit: Mean of role-fit category scores (None = not computable).
        preference_fit: Mean of preference-fit category scores (None = absent).
        role_fit_categories: Deterministic per-category role-fit scores.
        preference_fit_categories: Model-judged preference-fit categories.
        role_fit_note: Coverage note (e.g. requirements excluded as
            unmapped/non-canonical); empty when full coverage.
    """

    band: str
    summary: str
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    role_fit: Optional[float] = None
    preference_fit: Optional[float] = None
    role_fit_categories: tuple[FitCategory, ...] = ()
    preference_fit_categories: tuple[FitCategory, ...] = ()
    role_fit_note: str = ""


# __END__
