#!/usr/bin/env python3
"""Normalize JD requirement strings onto canonical skill-cloud skills.

Resolution is exact-match only (model proposal first, then the literal JD
phrasing); anything else stays UNMAPPED with its original text -- a gap or a
taxonomy hole is surfaced, never bridged to a near match.
"""

import dataclasses as dcs
from typing import Optional

from jobjob.structure.skillcloud import SkillCloud, get_skill_cloud


@dcs.dataclass(frozen=True)
class NormalizedRequirement:
    """A JD requirement resolved against the skill cloud.

    Attributes:
        text: The original JD phrasing (always preserved).
        canonical_id: The resolved canonical skill id, or None when UNMAPPED.
        categories: The canonical skill's category weights ({} when UNMAPPED).
    """

    text: str
    canonical_id: Optional[str] = None
    categories: dict[str, float] = dcs.field(default_factory=dict)

    @property
    def unmapped(self) -> bool:
        return self.canonical_id is None


def normalize_requirements(
    requirements: "list[str] | tuple[str, ...]",
    proposals: Optional[dict] = None,
    cloud: Optional[SkillCloud] = None,
) -> tuple[NormalizedRequirement, ...]:
    """Resolve JD requirement strings to canonical skills.

    Arguments:
        requirements: JD requirement/skill strings (original phrasing).
        proposals: Model-proposed canonical names keyed by requirement text
            (``JobDescription.canonical_skills``); may be None/empty for older
            cached parses.
        cloud: The skill cloud (defaults to the packaged cloud).
    Returns:
        One NormalizedRequirement per input, in order.
    """
    cloud = cloud if cloud is not None else get_skill_cloud()
    proposals = dict(proposals) if proposals else {}
    results = []
    for text in requirements:
        if not text:
            continue
        skill = cloud.resolve(proposals.get(text, "")) or cloud.resolve(text)
        if skill is None:
            results.append(NormalizedRequirement(text=text))
        else:
            results.append(
                NormalizedRequirement(
                    text=text,
                    canonical_id=skill.id,
                    categories=dict(skill.categories),
                )
            )
    return tuple(results)


# __END__
