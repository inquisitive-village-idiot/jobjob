#!/usr/bin/env python3
"""Skill entries and their selection metadata."""

import dataclasses as dcs
from collections.abc import Iterable


@dcs.dataclass(frozen=True)
class Skill:
    """A single skill entry.

    Attributes:
        label: Stable key identifying the skill (e.g. "python").
        text: Display text (e.g. "Python").
        keywords: Keywords used to score relevance against a job description.
        canonical_id: Skill-cloud canonical id (None = non-canonical/free-form).
        categories: The canonical skill's category weights ({} when non-canonical).
    """

    label: str
    text: str
    keywords: tuple[str, ...] = dcs.field(default_factory=tuple)
    canonical_id: str | None = None
    categories: dict[str, float] = dcs.field(default_factory=dict)

    @property
    def canonical(self) -> bool:
        return self.canonical_id is not None


@dcs.dataclass(frozen=True)
class SkillSet:
    """A collection of skills plus selection defaults.

    Attributes:
        skills: All loaded skills.
        default_number: Default count to surface for an application.
    """

    skills: tuple[Skill, ...]
    default_number: int = 12


def make_skill_set(
    skills: Iterable[Skill],
    default_number: int | None = None,
) -> SkillSet:
    """Build a SkillSet from an iterable of skills.

    NOTE: the selection default lives only on ``SkillSet``; passing None keeps
        that field's default (declared in one place).

    Arguments:
        skills: The skills.
        default_number: Override for the default selection count.
    Returns:
        A SkillSet.
    """
    kwargs = {} if default_number is None else {"default_number": default_number}
    return SkillSet(skills=tuple(skills), **kwargs)


# __END__
