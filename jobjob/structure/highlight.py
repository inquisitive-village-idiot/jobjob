#!/usr/bin/env python3
"""Credential highlight blocks and their selection metadata."""

import dataclasses as dcs
from collections.abc import Iterable, Mapping


@dcs.dataclass(frozen=True)
class Highlight:
    """A single pre-written credential block.

    Attributes:
        context: Stable key identifying the block (e.g. "fda_class3").
        text: The block prose.
        keywords: Keywords used to score relevance against a job description.
        enabled: Whether the block is eligible for selection.
        topic: Single-word grouping for the UI (e.g. Collaboration, Communication,
            Creativity, Leadership, Teamwork, Technical). Empty string if ungrouped.
    """

    context: str
    text: str
    keywords: tuple[str, ...] = dcs.field(default_factory=tuple)
    enabled: bool = True
    topic: str = ""


@dcs.dataclass(frozen=True)
class HighlightSet:
    """A collection of highlights plus selection defaults.

    Attributes:
        highlights: All loaded highlights (enabled and disabled).
        default_number: Default count to select for an application.
        max_characters: Upper bound on total selected character count.
        min_characters: Lower bound on total selected character count.
    """

    highlights: tuple[Highlight, ...]
    default_number: int = 6
    max_characters: int = 900
    min_characters: int = 600

    def enabled(self) -> tuple[Highlight, ...]:
        """Return only the enabled highlights."""
        return tuple(x for x in self.highlights if x.enabled)

    def by_context(self) -> Mapping[str, Highlight]:
        """Return a mapping of context key to highlight (all, including disabled)."""
        return {x.context: x for x in self.highlights}


def make_highlight_set(
    highlights: Iterable[Highlight],
    default_number: int | None = None,
    max_characters: int | None = None,
    min_characters: int | None = None,
) -> HighlightSet:
    """Build a HighlightSet from an iterable of highlights.

    NOTE: selection defaults live only on ``HighlightSet``; passing None for any
        keeps that field's default (so the value is declared in exactly one place).

    Arguments:
        highlights: The highlights.
        default_number: Override for the default selection count.
        max_characters: Override for the max total character count.
        min_characters: Override for the min total character count.
    Returns:
        A HighlightSet.
    """
    overrides = {
        "default_number": default_number,
        "max_characters": max_characters,
        "min_characters": min_characters,
    }
    kwargs = {key: value for key, value in overrides.items() if value is not None}
    return HighlightSet(highlights=tuple(highlights), **kwargs)


# __END__
