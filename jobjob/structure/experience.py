#!/usr/bin/env python3
"""Structured work history: roles and the company-adjacency grouping used to fill
ATS application forms and render a résumé.

One ``Role`` maps to one ATS "Work Experience" entry (title + company + dates +
description). Several roles at the same employer are stored as separate ``Role``
entries — that is exactly how an ATS wants them — and ``ExperienceSet.grouped``
reconstructs the "one company, several roles" view for a résumé by grouping
*consecutive* same-company roles, so a promotion groups while a later re-hire stays
separate.
"""

import dataclasses as dcs
from collections.abc import Iterable

# Bullet markers stripped when parsing a description into discrete lines.
_MARKERS = ("- ", "* ", "• ", "-", "*", "•")


def _strip_marker(line: str) -> str:
    """Return ``line`` with a single leading bullet marker (and indent) removed."""
    stripped = line.lstrip()
    for marker in _MARKERS:
        if stripped.startswith(marker):
            return stripped[len(marker) :].strip()
    return stripped


@dcs.dataclass(frozen=True)
class Role:
    """A single work-experience entry (one ATS "Work Experience" row).

    Attributes:
        company: Employer name.
        title: Role / job title.
        location: Work location (city or "Remote"); empty if unspecified.
        start: Start date, ``YYYY-MM`` or ``YYYY``; empty if unspecified.
        end: End date, ``YYYY-MM`` or ``YYYY``; empty when ``current``.
        current: True if this is an ongoing role (maps to the ATS "I currently
            work here" checkbox); ``end`` is ignored when True.
        description: Accomplishments, canonically one bullet per line.
    """

    company: str
    title: str
    location: str = ""
    start: str = ""
    end: str = ""
    current: bool = False
    description: str = ""

    def bullets(self) -> tuple[str, ...]:
        """Return the description as discrete bullet strings (markers stripped).

        Blank lines are dropped. This is the rendering primitive an ATS adapter
        formats into the destination field (e.g. a plain-text textarea), so the
        user never re-formats pasted résumé text.
        """
        lines = (_strip_marker(ln) for ln in self.description.splitlines())
        return tuple(ln for ln in lines if ln)


@dcs.dataclass(frozen=True)
class CompanyBlock:
    """Consecutive roles at one employer (adjacency-grouped for résumé rendering).

    Attributes:
        company: The shared employer name.
        roles: The consecutive roles, in their stored order.
    """

    company: str
    roles: tuple[Role, ...]


@dcs.dataclass(frozen=True)
class ExperienceSet:
    """An ordered work history.

    Attributes:
        roles: All roles, in stored (typically reverse-chronological) order.
    """

    roles: tuple[Role, ...] = dcs.field(default_factory=tuple)

    def grouped(self) -> tuple[CompanyBlock, ...]:
        """Group *consecutive* same-company roles into ``CompanyBlock``s.

        Grouping is by adjacency, not by company name, so a promotion within an
        employer groups under one block while leaving and rejoining that employer
        later yields two separate blocks.
        """
        blocks: list[CompanyBlock] = []
        for role in self.roles:
            if blocks and blocks[-1].company == role.company:
                last = blocks[-1]
                blocks[-1] = CompanyBlock(last.company, last.roles + (role,))
            else:
                blocks.append(CompanyBlock(role.company, (role,)))
        return tuple(blocks)


def make_experience_set(roles: Iterable[Role]) -> ExperienceSet:
    """Build an ExperienceSet from an iterable of roles (order preserved)."""
    return ExperienceSet(roles=tuple(roles))


# __END__
