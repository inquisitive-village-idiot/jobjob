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
from jobjob.structure.fit import BAND_MODERATE, BAND_STRONG, BAND_WEAK, Fit, FitCategory
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.normalize import normalize_requirements
from jobjob.structure.skillcloud import get_skill_cloud

MODERATE_GAP_THRESHOLD = 2
# A stretch-gap is outweighed when supporting evidence is this many times larger.
SUPPORT_RATIO = 2

# Role-fit match weights per skills-analysis bucket. PROVISIONAL first-pass
# values -- tune after reviewing real applications. Aspirational gaps and
# unresolvable (non-canonical) skills are excluded from scoring entirely.
MATCH_WEIGHT_CRITICAL_SUPPORTED = 1.0
MATCH_WEIGHT_IMPORTANT_SUPPORTED = 0.75
MATCH_WEIGHT_STRETCH_GAP = 0.4
MATCH_WEIGHT_BLOCKING_GAP = 0.0


def assess_fit(skills: Mapping, logger: logging.Logger | None = None) -> Fit:
    """Derive a qualitative fit band + summary from the skills analysis.

    NOTE: deterministic for now -- the band keys off the critical gaps weighted by
        severity ("blocking" / "stretch" / "aspirational") against the volume of
        supported skills. Aspirational gaps are listed but never drive the band;
        analyses without severity (older cached results) default to "stretch".

    Arguments:
        skills: The skills-analysis mapping (critical_gaps / *_supported).
        logger: Optional logger for injection.
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

    role_categories, role_score, role_note = _score_role_fit(skills, logger=logger)
    pref_categories, pref_score = _parse_preference_fit(skills, logger=logger)
    return Fit(
        band=band,
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        role_fit=role_score,
        preference_fit=pref_score,
        role_fit_categories=role_categories,
        preference_fit_categories=pref_categories,
        role_fit_note=role_note,
    )


def _scoring_items(skills: Mapping) -> list[tuple[str, float]]:
    """Return (skill name, match weight) pairs that participate in role scoring.

    Aspirational gaps are listed in the README but never scored.
    """
    severity_weights = {
        "blocking": MATCH_WEIGHT_BLOCKING_GAP,
        "stretch": MATCH_WEIGHT_STRETCH_GAP,
    }
    items = []
    for entry in skills.get("critical_supported", []):
        if entry.get("skill"):
            items.append((entry["skill"], MATCH_WEIGHT_CRITICAL_SUPPORTED))
    for entry in skills.get("important_supported", []):
        if entry.get("skill"):
            items.append((entry["skill"], MATCH_WEIGHT_IMPORTANT_SUPPORTED))
    for entry in skills.get("critical_gaps", []):
        severity = entry.get("severity", "stretch")
        if entry.get("skill") and severity in severity_weights:
            items.append((entry["skill"], severity_weights[severity]))
    return items


def _score_role_fit(
    skills: Mapping, logger: logging.Logger | None = None
) -> tuple[tuple[FitCategory, ...], Optional[float], str]:
    """Compute deterministic role-fit category scores over the canonical join.

    Each scoring item resolves against the skill cloud; its match weight is
    distributed over the canonical skill's category weights. Category score is
    the weighted mean; the axis score is the mean of defined category scores.
    Unresolvable items are excluded and counted in the coverage note. Band
    derivation is untouched -- this is additive measurement.
    """
    items = _scoring_items(skills)
    if not items:
        return (), None, ""
    try:
        cloud = get_skill_cloud()
    except (OSError, ValueError) as exc:
        _logger = logger or logging.getLogger(__name__)
        _logger.warning("Skill cloud unavailable; role fit skipped: %s", exc)
        return (), None, ""

    weighted: dict[str, float] = {}  # category -> sum(match * weight)
    denominator: dict[str, float] = {}  # category -> sum(weight)
    contributors: dict[str, list[str]] = {}
    excluded = []
    for name, match in items:
        canonical = cloud.resolve(name)
        if canonical is None:
            excluded.append(name)
            continue
        for category, weight in canonical.categories.items():
            weighted[category] = weighted.get(category, 0.0) + match * weight
            denominator[category] = denominator.get(category, 0.0) + weight
            contributors.setdefault(category, []).append(name)

    categories = tuple(
        FitCategory(
            name=category,
            score=round(weighted[category] / denominator[category], 2),
            note=", ".join(dict.fromkeys(contributors[category])),
        )
        for category in sorted(denominator)
        if denominator[category] > 0
    )
    note = (
        f"{len(excluded)} of {len(items)} analyzed skills not in the skill "
        f"cloud (excluded from scores): " + ", ".join(excluded[:6])
        if excluded
        else ""
    )
    if not categories:
        return (), None, note
    score = round(sum(c.score for c in categories) / len(categories), 2)
    return categories, score, note


def _parse_preference_fit(
    skills: Mapping, logger: logging.Logger | None = None
) -> tuple[tuple[FitCategory, ...], Optional[float]]:
    """Parse the model-judged preference-fit block, tolerantly.

    Invalid categories (missing/non-numeric/out-of-range score) are skipped at
    WARNING; an absent block (older cached analyses) yields ((), None).
    """
    raw = skills.get("preference_fit")
    if not isinstance(raw, (list, tuple)):
        return (), None
    _logger = logger or logging.getLogger(__name__)
    categories = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            _logger.warning("Skipping malformed preference-fit category: %r", entry)
            continue
        name = entry.get("name")
        score = entry.get("score")
        if not name or not isinstance(score, (int, float)) or not 0.0 <= score <= 1.0:
            _logger.warning("Skipping invalid preference-fit category: %r", entry)
            continue
        categories.append(
            FitCategory(name=name, score=float(score), note=entry.get("note", ""))
        )
    if not categories:
        return (), None
    score = round(sum(c.score for c in categories) / len(categories), 2)
    return tuple(categories), score


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
    fit = assess_fit(skills, logger=logger)
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
