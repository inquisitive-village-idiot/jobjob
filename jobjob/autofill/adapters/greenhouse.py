#!/usr/bin/env python3
"""Greenhouse auto-fill adapter.

Greenhouse application forms (``boards.greenhouse.io`` and the newer
``job-boards.greenhouse.io``) are a single page: contact basics plus a résumé
upload and custom questions. This adapter fills the contact basics from the active
profile and leaves the résumé upload, custom questions, and submit to the human.

Field selectors are best-effort (stable Greenhouse ids first, with autocomplete/name
fallbacks) and mirrored by the test fixture; confirm against a live posting during
validation. *Flag, don't invent*: a field that isn't present is skipped, never guessed.
"""

import logging
import re
from typing import TYPE_CHECKING

from jobjob.autofill.adapters._common import fill_contact_field, split_name
from jobjob.autofill.data import ApplicationData
from jobjob.autofill.report import (
    FilledField,
    FillReport,
    FlaggedField,
    make_fill_report,
)

if TYPE_CHECKING:
    from playwright.sync_api import Page

NAME = "jobjob.autofill.greenhouse"

_GREENHOUSE_HOST = re.compile(r"greenhouse\.io", re.IGNORECASE)

# Candidate selectors per field, most specific (Greenhouse ids) first.
_FIRST_NAME = (
    "#first_name",
    'input[autocomplete="given-name"]',
    'input[name*="first" i]',
)
_LAST_NAME = (
    "#last_name",
    'input[autocomplete="family-name"]',
    'input[name*="last" i]',
)
_EMAIL = ("#email", 'input[type="email"]', 'input[autocomplete="email"]')
_PHONE = ("#phone", 'input[type="tel"]', 'input[autocomplete="tel"]')
_LINKEDIN = ('input[name*="linkedin" i]', 'input[aria-label*="linkedin" i]')


class GreenhouseAdapter:
    """Fill the contact basics of a Greenhouse application."""

    name = "greenhouse"

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(NAME)

    def matches(self, url: str) -> bool:
        """Return True if ``url`` is hosted on Greenhouse."""
        return bool(_GREENHOUSE_HOST.search(url or ""))

    def fill(self, page: "Page", data: ApplicationData) -> FillReport:
        """Fill the visible contact fields and report what was/was not handled."""
        filled: list[FilledField] = []
        flagged: list[FlaggedField] = []
        first, last = split_name(data.applicant.name)
        specs = [
            # (selectors, value, label, required)
            (_FIRST_NAME, first, "First name", True),
            (_LAST_NAME, last, "Last name", True),
            (_EMAIL, data.applicant.email or "", "Email", True),
            (_PHONE, data.applicant.phone or "", "Phone", False),
            (_LINKEDIN, data.applicant.linkedin or "", "LinkedIn", False),
        ]
        for selectors, value, label, required in specs:
            fill_contact_field(
                page,
                selectors,
                value,
                label,
                required=required,
                filled=filled,
                flagged=flagged,
            )
        report = make_fill_report(self.name, filled, flagged)
        self._logger.info(
            "Greenhouse fill: %d filled, %d flagged", len(filled), len(flagged)
        )
        return report


# __END__
