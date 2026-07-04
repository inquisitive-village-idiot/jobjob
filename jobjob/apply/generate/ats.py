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
from typing import Optional, get_origin

from jobjob.apply.generate.ats_checks import AtsCheck, run_parseability_checks
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.normalize import NormalizedRequirement, normalize_requirements
from jobjob.structure.skill import SkillSet
from jobjob.structure.skillcloud import get_skill_cloud

# Criticality weights per requirement source (mirrors the fit-scoring stance:
# key requirements outweigh listed technical skills). PROVISIONAL.
WEIGHT_KEY_REQUIREMENT = 1.0
WEIGHT_TECHNICAL_SKILL = 0.75


# Structures
# ======================================================================


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


# Mutable working counterpart of AtsAssessment, generated from the frozen type
# so the data contract is defined once: tuple fields become lists (buildable
# in place), everything else keeps its defined type; the weight accumulators
# are working-state extras. Frozen back via _freeze at the assess_ats boundary.
_CoverageBuckets = dcs.make_dataclass(
    "_CoverageBuckets",
    [
        *(
            (
                (f.name, list, dcs.field(default_factory=list))
                if get_origin(f.type) is tuple
                else (f.name, f.type, f.default)
            )
            for f in dcs.fields(AtsAssessment)
        ),
        ("hit_weight", float, 0.0),
        ("total_weight", float, 0.0),
    ],
)
_CoverageBuckets.__doc__ = (
    "Mutable working counterpart of AtsAssessment (tuple fields as lists), "
    "plus coverage-weight accumulators."
)


def _freeze(buckets) -> AtsAssessment:
    """Freeze a _CoverageBuckets into the public AtsAssessment.

    NOTE: ``dcs.asdict`` is close but wrong here: it recurses into nested
        dataclasses (AtsCheck would arrive as plain dicts) and it carries the
        working-only weight accumulators. Mapping AtsAssessment's own fields
        keeps types intact and drops the extras.
    """
    values = {}
    for field in dcs.fields(AtsAssessment):
        value = getattr(buckets, field.name)
        values[field.name] = tuple(value) if isinstance(value, list) else value
    return AtsAssessment(**values)


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
    key = normalize_requirements(list(job.key_requirements or []), proposals=proposals)
    tech = normalize_requirements(list(job.technical_skills or []), proposals=proposals)
    return [(r, WEIGHT_KEY_REQUIREMENT) for r in key] + [
        (r, WEIGHT_TECHNICAL_SKILL) for r in tech
    ]


def assess_ats(
    document: Optional[Mapping],
    job: JobDescription,
    skills: Mapping,
    skill_set: Optional[SkillSet] = None,
    logger: logging.Logger | None = None,
) -> AtsAssessment:
    """Assess the rendered resume document against the JD's canonical skills.

    Arguments:
        document: The updated resume document (Google Docs JSON), or None when
            Drive was skipped.
        job: The parsed job description.
        skills: The skills-analysis mapping.
        skill_set: The loaded profile skills (declared-skill allowlist for
            recommendations). None degrades to no recommendations.
        logger: Optional logger for injection.
    Returns:
        An AtsAssessment. Deterministic for fixed inputs and cloud version.
    """
    if document is None:
        return AtsAssessment(skipped=True)
    try:
        cloud = get_skill_cloud()
    except (OSError, ValueError) as exc:
        _logger = logger or logging.getLogger(__name__)
        _logger.warning("Skill cloud unavailable; ATS assessment skipped: %s", exc)
        return AtsAssessment(skipped=True)

    # Local import avoids a hard dependency for offline/test paths.
    from jobjob.gapi.docs import extract_doc_text

    text = extract_doc_text(document.get("body", {}).get("content", []))
    supported = _supported_canonical_ids(skills, cloud)
    declared = {
        s.canonical_id for s in (skill_set.skills if skill_set else ()) if s.canonical
    }

    buckets = _classify_coverage(
        job=job, text=text, cloud=cloud, supported=supported, declared=declared
    )

    buckets.coverage_score = (
        round(buckets.hit_weight / buckets.total_weight, 2)
        if buckets.total_weight
        else None
    )
    buckets.checks.extend(run_parseability_checks(document))
    return _freeze(buckets)


def _classify_coverage(
    *,
    job: JobDescription,
    text: str,
    cloud,
    supported: Mapping,
    declared: set,
) -> "_CoverageBuckets":
    """Bucket each canonical JD requirement by resume presence and evidence.

    Recommendations require the skill to be both evidenced (``supported``) and
    declared in the user's skills file (``declared``) -- the honesty layer.
    Evidenced-but-undeclared skills become skills-file candidates; unevidenced
    ones become up-skill targets. Duplicate canonical ids (the same skill
    backing several requirements) are counted once. Fit-vs-ATS gaps are
    everything the analysis supports that the resume never says -- including
    skills the JD didn't canonically require.
    """
    buckets = _CoverageBuckets()
    buckets.fit_gaps.extend(
        cloud.skills[cid].name
        for cid in supported
        if not _skill_in_text(cloud.skills[cid], text)
    )
    seen_ids: set[str] = set()
    for requirement, weight in _weighted_requirements(job):
        if requirement.unmapped:
            buckets.unmapped.append(requirement.text)
            continue
        canonical_id = requirement.canonical_id
        if canonical_id in seen_ids:
            continue  # the same canonical skill may back several requirements
        seen_ids.add(canonical_id)
        canonical = cloud.skills[canonical_id]
        buckets.total_weight += weight
        if _skill_in_text(canonical, text):
            buckets.present.append(canonical.name)
            buckets.hit_weight += weight
            continue
        if canonical_id in supported:
            buckets.missing_evidenced.append(canonical.name)
            evidence = supported[canonical_id]
            if canonical_id in declared:
                cite = f" (evidence: {evidence})" if evidence else ""
                buckets.recommendations.append(
                    f"{canonical.name} is supported by your documentation{cite} "
                    "but absent from the resume text."
                )
            else:
                buckets.skills_file_candidates.append(canonical.name)
        else:
            buckets.missing_unevidenced.append(canonical.name)
            buckets.upskill_targets.append(canonical.name)
    return buckets


# __END__
