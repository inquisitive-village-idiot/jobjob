#!/usr/bin/env python3
"""ATS assessment: will the generated resume survive the machine screen?

Fit scoring judges the JD against the applicant's full documented experience;
this module judges it against what actually made it into the rendered resume
text. A skill that is well-evidenced but never rendered is a fit strength and
an ATS miss at the same time -- that gap is the actionable signal.

Honesty layer: fix recommendations are bounded to skills that are BOTH
evidenced in the skills analysis AND declared in the user's skills file. The
assessment never suggests adding an unevidenced or undeclared skill, and never
generates resume copy.

All weights, thresholds, and the parseability check set live in this module as
documented constants. PROVISIONAL: calibrate against expert-reviewed ATS
assessments before trusting the absolute numbers.
"""

import dataclasses as dcs
import logging
import re
from collections.abc import Mapping
from typing import Optional

from jobjob.structure.job_decription import JobDescription
from jobjob.structure.skill import SkillSet
from jobjob.structure.skillcloud import (
    NormalizedRequirement,
    get_skill_cloud,
    normalize_requirements,
)

LOGGER = logging.getLogger(__name__)

# Criticality weights per requirement source (mirrors the fit-scoring stance:
# key requirements outweigh listed technical skills). PROVISIONAL.
WEIGHT_KEY_REQUIREMENT = 1.0
WEIGHT_TECHNICAL_SKILL = 0.75

# Section headings ATS parsers commonly recognize (casefolded comparison).
# PROVISIONAL: extend as calibration data comes in.
STANDARD_HEADINGS = frozenset(
    {
        "summary",
        "objective",
        "profile",
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "education",
        "skills",
        "key skills",
        "technical skills",
        "key career highlights",
        "highlights",
        "certifications",
        "projects",
        "publications",
        "awards",
        "contact",
        "references",
    }
)


# Structures
# ======================================================================


@dcs.dataclass(frozen=True)
class AtsCheck:
    """One parseability check result."""

    name: str
    passed: bool
    reason: str = ""


@dcs.dataclass(frozen=True)
class AtsAssessment:
    """The full ATS assessment for one application.

    Attributes:
        skipped: True when no resume document exists (Drive skipped).
        coverage_score: Weighted share of canonical JD skills present in the
            resume text (None when nothing was scorable).
        present / missing_evidenced / missing_unevidenced: Canonical JD skill
            names bucketed by resume-text presence and analysis evidence.
        unmapped: Requirements with no skill-cloud match (listed, unscored).
        recommendations: Evidence-cited fixes (evidenced AND declared only).
        skills_file_candidates: Evidenced but undeclared -- consider adding to
            the skills file. README-only; never fed to generation.
        upskill_targets: Missing and unevidenced -- possible up-skill targets
            for the user. README-only; never fed to generation.
        checks: Parseability check results.
        fit_gaps: Analysis-supported skills absent from the resume text (the
            fit-vs-ATS gap list).
    """

    skipped: bool = False
    coverage_score: Optional[float] = None
    present: tuple[str, ...] = ()
    missing_evidenced: tuple[str, ...] = ()
    missing_unevidenced: tuple[str, ...] = ()
    unmapped: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    skills_file_candidates: tuple[str, ...] = ()
    upskill_targets: tuple[str, ...] = ()
    checks: tuple[AtsCheck, ...] = ()
    fit_gaps: tuple[str, ...] = ()


# Text matching
# ======================================================================


def _term_in_text(term: str, text: str) -> bool:
    """Word-boundary, case-insensitive containment (safe for 'C++' etc.)."""
    if not term:
        return False
    pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _skill_in_text(canonical, text: str) -> bool:
    """True if the canonical skill's name or any alias appears in the text."""
    return any(_term_in_text(t, text) for t in (canonical.name, *canonical.aliases))


# Coverage
# ======================================================================


def _supported_canonical_ids(skills: Mapping, cloud) -> dict[str, str]:
    """Map canonical id -> evidence for analysis-supported skills."""
    supported = {}
    for bucket in ("critical_supported", "important_supported", "strong_supporting"):
        for entry in skills.get(bucket, []):
            name = entry.get("skill")
            if not name:
                continue
            canonical = cloud.resolve(name)
            if canonical is None:
                continue
            evidence = entry.get("evidence") or entry.get("relevance") or ""
            supported.setdefault(canonical.id, evidence)
    return supported


def _weighted_requirements(
    job: JobDescription,
) -> list[tuple[NormalizedRequirement, float]]:
    """Normalize JD requirements + technical skills with criticality weights."""
    proposals = dict(job.canonical_skills or {})
    key = normalize_requirements(
        list(job.key_requirements or []), proposals=proposals
    )
    tech = normalize_requirements(
        list(job.technical_skills or []), proposals=proposals
    )
    return [(r, WEIGHT_KEY_REQUIREMENT) for r in key] + [
        (r, WEIGHT_TECHNICAL_SKILL) for r in tech
    ]


def assess_ats(
    document: Optional[Mapping],
    job: JobDescription,
    skills: Mapping,
    skill_set: Optional[SkillSet] = None,
) -> AtsAssessment:
    """Assess the rendered resume document against the JD's canonical skills.

    Arguments:
        document: The updated resume document (Google Docs JSON), or None when
            Drive was skipped.
        job: The parsed job description.
        skills: The skills-analysis mapping.
        skill_set: The loaded profile skills (declared-skill allowlist for
            recommendations). None degrades to no recommendations.
    Returns:
        An AtsAssessment. Deterministic for fixed inputs and cloud version.
    """
    if document is None:
        return AtsAssessment(skipped=True)
    try:
        cloud = get_skill_cloud()
    except (OSError, ValueError) as exc:
        LOGGER.warning("Skill cloud unavailable; ATS assessment skipped: %s", exc)
        return AtsAssessment(skipped=True)

    # Local import avoids a hard dependency for offline/test paths.
    from jobjob.gapi.docs import extract_doc_text

    text = extract_doc_text(document.get("body", {}).get("content", []))
    supported = _supported_canonical_ids(skills, cloud)
    declared = {
        s.canonical_id for s in (skill_set.skills if skill_set else ()) if s.canonical
    }

    present, missing_evidenced, missing_unevidenced, unmapped = [], [], [], []
    recommendations, candidates, upskill = [], [], []
    hit_weight = total_weight = 0.0
    seen_ids: set[str] = set()
    for requirement, weight in _weighted_requirements(job):
        if requirement.unmapped:
            unmapped.append(requirement.text)
            continue
        canonical_id = requirement.canonical_id
        if canonical_id in seen_ids:
            continue  # the same canonical skill may back several requirements
        seen_ids.add(canonical_id)
        canonical = cloud.skills[canonical_id]
        total_weight += weight
        if _skill_in_text(canonical, text):
            present.append(canonical.name)
            hit_weight += weight
            continue
        if canonical_id in supported:
            missing_evidenced.append(canonical.name)
            evidence = supported[canonical_id]
            if canonical_id in declared:
                cite = f" (evidence: {evidence})" if evidence else ""
                recommendations.append(
                    f"{canonical.name} is supported by your documentation{cite} "
                    "but absent from the resume text."
                )
            else:
                candidates.append(canonical.name)
        else:
            missing_unevidenced.append(canonical.name)
            upskill.append(canonical.name)

    # Fit-vs-ATS gaps: everything the analysis supports that the resume never
    # says -- including skills the JD didn't canonically require.
    fit_gaps = tuple(
        cloud.skills[cid].name
        for cid in supported
        if not _skill_in_text(cloud.skills[cid], text)
    )

    score = round(hit_weight / total_weight, 2) if total_weight else None
    return AtsAssessment(
        skipped=False,
        coverage_score=score,
        present=tuple(present),
        missing_evidenced=tuple(missing_evidenced),
        missing_unevidenced=tuple(missing_unevidenced),
        unmapped=tuple(unmapped),
        recommendations=tuple(recommendations),
        skills_file_candidates=tuple(candidates),
        upskill_targets=tuple(upskill),
        checks=run_parseability_checks(document),
        fit_gaps=fit_gaps,
    )


# Parseability
# ======================================================================


def run_parseability_checks(document: Mapping) -> tuple[AtsCheck, ...]:
    """Run the named structural checks over a Google Docs JSON document.

    Each check returns pass/warn with a one-line reason. Template-dominated:
    results are stable across applications sharing a template, but running per
    application is cheap and catches template edits.
    """
    content = document.get("body", {}).get("content", [])
    checks = []

    tables = [e for e in content if "table" in e]
    checks.append(
        AtsCheck(
            name="content-in-tables",
            passed=not tables,
            reason=(
                f"{len(tables)} table(s) in the body; many ATS parsers drop "
                "table cells."
                if tables
                else ""
            ),
        )
    )

    headings = []
    for element in content:
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
        if style.startswith("HEADING"):
            heading_text = "".join(
                run.get("textRun", {}).get("content", "")
                for run in paragraph.get("elements", [])
            ).strip()
            if heading_text:
                headings.append(heading_text)
    unrecognized = [h for h in headings if h.casefold() not in STANDARD_HEADINGS]
    checks.append(
        AtsCheck(
            name="nonstandard-headings",
            passed=not unrecognized,
            reason=(
                "Headings ATS parsers may not recognize: "
                + ", ".join(unrecognized[:5])
                if unrecognized
                else ""
            ),
        )
    )

    has_objects = bool(document.get("inlineObjects")) or bool(
        document.get("positionedObjects")
    )
    checks.append(
        AtsCheck(
            name="images-or-text-boxes",
            passed=not has_objects,
            reason=(
                "Images or positioned objects present; content inside them is "
                "invisible to ATS parsers."
                if has_objects
                else ""
            ),
        )
    )

    multi_column = any(
        len(
            e.get("sectionBreak", {})
            .get("sectionStyle", {})
            .get("columnProperties", [])
        )
        > 1
        for e in content
    )
    checks.append(
        AtsCheck(
            name="multi-column-layout",
            passed=not multi_column,
            reason=(
                "Multi-column section detected; column order confuses many "
                "ATS parsers."
                if multi_column
                else ""
            ),
        )
    )

    return tuple(checks)


# __END__
