#!/usr/bin/env python3
"""Greenhouse auto-fill adapter.

Greenhouse application forms (``boards.greenhouse.io`` and the newer
``job-boards.greenhouse.io``) are a single page: contact basics plus a résumé upload
and custom questions. This adapter fills the contact basics from the active profile
and leaves the résumé upload, custom questions, and submit to the human.

Field selectors are best-effort (stable Greenhouse ids first, with autocomplete/name
fallbacks) and mirrored by the test fixture; confirm against a live posting during
validation. *Flag, don't invent*: a field that isn't present is skipped, never guessed.
"""

import re

from jobjob.autofill.adapters._common import ContactFormAdapter, ContactSpec, split_name
from jobjob.autofill.data import ApplicationData

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


class GreenhouseAdapter(ContactFormAdapter):
    """Fill the contact basics of a Greenhouse application."""

    name = "greenhouse"
    host = re.compile(r"greenhouse\.io", re.IGNORECASE)

    def contact_specs(self, data: ApplicationData) -> list[ContactSpec]:
        first, last = split_name(data.applicant.name)
        return [
            (_FIRST_NAME, first, "First name", True),
            (_LAST_NAME, last, "Last name", True),
            (_EMAIL, data.applicant.email or "", "Email", True),
            (_PHONE, data.applicant.phone or "", "Phone", False),
            (_LINKEDIN, data.applicant.linkedin or "", "LinkedIn", False),
        ]


# __END__
