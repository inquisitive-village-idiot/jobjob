#!/usr/bin/env python3
"""Shared adapter helpers.

Most ATS application forms are a single page of contact basics (first/last name,
email, phone, LinkedIn) plus a résumé upload — no structured work-experience fields
(that is Workday's outlier case). So the named adapters reduce to a host match plus a
map of candidate selectors per field, and this module supplies the small DOM helpers
they share: a tolerant "first present selector wins" lookup and a contact-field fill
that records filled vs. flagged. Playwright types are referenced only for type
checking — adapters never import Playwright themselves.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from jobjob.autofill.report import FilledField, FlaggedField

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page


def split_name(full_name: str | None) -> tuple[str, str]:
    """Split a single full-name field into ``(first, last)``.

    Forms that want separate first/last fields get a split on the last run of
    whitespace: ``"Ada B. Lovelace"`` → ``("Ada B.", "Lovelace")``. A single token
    yields ``(token, "")`` and an empty/None name yields ``("", "")`` — callers flag
    the missing last name rather than guessing one.
    """
    name = (full_name or "").strip()
    if not name:
        return ("", "")
    first, _, last = name.rpartition(" ")
    if not first:
        return (last, "")
    return (first.strip(), last.strip())


def find_first(page: "Page", selectors: Sequence[str]) -> "Locator | None":
    """Return the first present field matching any of ``selectors``, else None."""
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count():
            return locator.first
    return None


def fill_contact_field(
    page: "Page",
    selectors: Sequence[str],
    value: str,
    label: str,
    *,
    required: bool,
    filled: list[FilledField],
    flagged: list[FlaggedField],
) -> None:
    """Fill the first present field for ``selectors`` from ``value``.

    Absent fields are skipped silently (not every form has every field). A present
    field with no value is flagged when ``required`` so the human knows to fill it;
    optional empties are skipped. *Flag, don't invent.*
    """
    field = find_first(page, selectors)
    if field is None:
        return
    if not value:
        if required:
            flagged.append(FlaggedField(label, "not set in profile — fill by hand"))
        return
    field.fill(value)
    filled.append(FilledField(label, value))


# __END__
