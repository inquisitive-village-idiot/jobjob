#!/usr/bin/env python3
"""Build the per-application README (summary doc).

The README replaces the old "gap flags at the top of the cover letter": it
summarizes the role and folds in the skills analysis plus a fit assessment, so
Lets you triage an application at a glance.
"""

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Optional

from jobjob.apply.output.readme_docx import create_readme_docx
from jobjob.structure.fit import BAND_MODERATE, BAND_STRONG, BAND_WEAK, Fit
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.normalize import normalize_requirements

MODERATE_GAP_THRESHOLD = 2
# A stretch-gap is outweighed when supporting evidence is this many times larger.
SUPPORT_RATIO = 2


def assess_fit(skills: Mapping) -> Fit:
    """Derive a qualitative fit band + summary from the skills analysis.

    NOTE: deterministic for now -- the band keys off the critical gaps weighted by
        severity ("blocking" / "stretch" / "aspirational") against the volume of
        supported skills. Aspirational gaps are listed but never drive the band;
        analyses without severity (older cached results) default to "stretch".

    Arguments:
        skills: The skills-analysis mapping (critical_gaps / *_supported).
    Returns:
        A Fit.
    """
    gaps = list(skills.get("critical_gaps", []))
    supported = list(skills.get("critical_supported", [])) + list(
        skills.get("important_supported", [])
    )

    blocking = [g for g in gaps if g.get("severity", "stretch") == "blocking"]
    stretch = [g for g in gaps if g.get("severity", "stretch") == "stretch"]

    if blocking:
        band = BAND_WEAK
    elif not stretch:
        band = BAND_STRONG
    elif len(stretch) <= MODERATE_GAP_THRESHOLD or len(
        supported
    ) >= SUPPORT_RATIO * len(stretch):
        band = BAND_MODERATE
    else:
        band = BAND_WEAK

    strengths = tuple(s.get("skill", "") for s in supported if s.get("skill"))
    weaknesses = tuple(
        g["skill"]
        + (" (aspirational)" if g.get("severity", "stretch") == "aspirational" else "")
        for g in gaps
        if g.get("skill")
    )
    parts = []
    if strengths:
        parts.append("Strengths: " + ", ".join(strengths[:5]))
    if weaknesses:
        parts.append("Gaps: " + ", ".join(weaknesses[:5]))
    summary = "; ".join(parts) or "No skills assessment available."
    return Fit(band=band, summary=summary, strengths=strengths, weaknesses=weaknesses)


def generate_application_readme(
    job: JobDescription,
    skills: Mapping,
    output_path: Path,
    issues: Optional[Iterable[str]] = None,
    template_name: Optional[str] = None,
    template_archetype: Optional[str] = None,
    resume_changes: Optional[Iterable[str]] = None,
    logger: logging.Logger | None = None,
) -> Path:
    """Assess fit and render the application README to ``output_path`` (DOCX).

    Arguments:
        job: The parsed job description.
        skills: The skills-analysis mapping (folded into the README).
        output_path: Destination DOCX path.
        issues: Processing/content issues to surface (script errors, ambiguities).
        template_name: Resume template used (None when Drive was skipped).
        template_archetype: Human-readable archetype of the template.
        resume_changes: Edits applied to the template (empty = used as-is).
        logger: Optional logger for injection.
    Returns:
        The output path.
    """
    issues = list(issues) if issues is not None else []
    fit = assess_fit(skills)
    unmapped = _unmapped_requirements(job, logger=logger)
    return create_readme_docx(
        output_path=output_path,
        job=job,
        skills=skills,
        fit=fit,
        issues=issues,
        template_name=template_name,
        template_archetype=template_archetype,
        resume_changes=resume_changes,
        unmapped=unmapped,
    )


def _unmapped_requirements(
    job: JobDescription, logger: logging.Logger | None = None
) -> list[str]:
    """Return JD requirements/skills that resolve to no skill-cloud entry.

    NOTE: Surfacing only — a gap or a taxonomy hole, never bridged. Cloud load
        failures degrade to an empty list (the README simply omits the section).
    """
    texts = list(job.key_requirements or []) + list(job.technical_skills or [])
    try:
        normalized = normalize_requirements(
            texts, proposals=dict(job.canonical_skills or {})
        )
    except (OSError, ValueError) as exc:
        # NOTE: logger instantiated only on this conditional path (injection
        #   pattern -- see project review guidance).
        _logger = logger or logging.getLogger(__name__)
        _logger.warning("Skill cloud unavailable; skipping normalization: %s", exc)
        return []
    return [n.text for n in normalized if n.unmapped]


# __END__
