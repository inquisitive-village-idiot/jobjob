#!/usr/bin/env python3
"""Fit assessment of a candidate against a role."""

import dataclasses as dcs
from typing import Optional

# Qualitative bands (sufficient for now).
BAND_STRONG = "Strong"
BAND_MODERATE = "Moderate"
BAND_WEAK = "Weak"


@dcs.dataclass(frozen=True)
class Fit:
    """A fit assessment.

    NOTE: for now this is a qualitative band + a brief summary derived from the
        skills analysis. The richer quantitative breakdown is future work.
    TODO: add a quantitative two-axis fit -- (1) fit for the role and (2) fit for
        what the applicant is looking for -- each broken into categories with a brief
        description and score.

    Attributes:
        band: Qualitative band (Strong / Moderate / Weak).
        summary: A brief one-line summary of strengths and gaps.
        strengths: Supported skills, for the side-by-side fit table.
        weaknesses: Critical gaps, for the side-by-side fit table.
        role_fit: Placeholder for the quantitative role-fit score (TODO).
        preference_fit: Placeholder for the quantitative target-fit score (TODO).
    """

    band: str
    summary: str
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    role_fit: Optional[float] = None
    preference_fit: Optional[float] = None


# __END__
