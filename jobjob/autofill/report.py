#!/usr/bin/env python3
"""The result of an auto-fill pass: what got filled, and what was left for a human.

The guiding rule is *flag, don't invent*. When an adapter cannot confidently map a
value to a field (a custom date widget, a screening question, a name it could not
split) it records a ``FlaggedField`` instead of guessing, so the human knows exactly
what still needs their attention before submitting.
"""

import dataclasses as dcs
from collections.abc import Iterable


@dcs.dataclass(frozen=True)
class FilledField:
    """A field the adapter populated.

    Attributes:
        label: Human-facing field name (e.g. "First name").
        value: The value written into the field.
    """

    label: str
    value: str


@dcs.dataclass(frozen=True)
class FlaggedField:
    """A field the adapter deliberately left for the human to handle.

    Attributes:
        label: Human-facing field name (e.g. "Start date").
        reason: Why it was left (e.g. "custom date widget — fill by hand").
    """

    label: str
    reason: str


@dcs.dataclass(frozen=True)
class FillReport:
    """Outcome of one adapter ``fill`` pass.

    Attributes:
        adapter: Name of the adapter that produced this report (e.g. "workday").
        filled: Fields that were populated, in fill order.
        flagged: Fields left for the human, in encounter order.
    """

    adapter: str = ""
    filled: tuple[FilledField, ...] = dcs.field(default_factory=tuple)
    flagged: tuple[FlaggedField, ...] = dcs.field(default_factory=tuple)

    def render(self) -> str:
        """Return a human-readable summary for the terminal."""
        lines = [f"Auto-fill report ({self.adapter or 'unknown'}):"]
        lines.append(f"  filled {len(self.filled)} field(s):")
        for field in self.filled:
            lines.append(f"    ✓ {field.label}: {field.value}")
        if self.flagged:
            lines.append(f"  flagged {len(self.flagged)} field(s) for you:")
            for field in self.flagged:
                lines.append(f"    ⚠ {field.label} — {field.reason}")
        return "\n".join(lines)


def make_fill_report(
    adapter: str,
    filled: Iterable[FilledField] = (),
    flagged: Iterable[FlaggedField] = (),
) -> FillReport:
    """Build a FillReport from iterables of filled and flagged fields."""
    return FillReport(
        adapter=adapter,
        filled=tuple(filled),
        flagged=tuple(flagged),
    )


# __END__
