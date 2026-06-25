#!/usr/bin/env python3
"""Ashby auto-fill adapter.

Ashby postings (``jobs.ashbyhq.com``) render a single-page React form. The built-in
fields use ``_systemfield_*`` names with a single full-name field; aria-label and
autocomplete fallbacks cover tenant variation. Best-effort selectors mirrored by the
fixture; résumé upload, custom questions, and submit are left to the human.
"""

import re

from jobjob.autofill.adapters._common import ContactFormAdapter, ContactSpec
from jobjob.autofill.data import ApplicationData

_NAME = (
    'input[name="_systemfield_name"]',
    'input[aria-label="Name" i]',
    'input[autocomplete="name"]',
)
_EMAIL = (
    'input[name="_systemfield_email"]',
    'input[type="email"]',
    'input[autocomplete="email"]',
)
_PHONE = (
    'input[name="_systemfield_phone"]',
    'input[type="tel"]',
    'input[autocomplete="tel"]',
)
_LINKEDIN = ('input[name*="linkedin" i]', 'input[aria-label*="linkedin" i]')


class AshbyAdapter(ContactFormAdapter):
    """Fill the contact basics of an Ashby application (single full-name field)."""

    name = "ashby"
    host = re.compile(r"ashbyhq\.com", re.IGNORECASE)

    def contact_specs(self, data: ApplicationData) -> list[ContactSpec]:
        return [
            (_NAME, data.applicant.name or "", "Full name", True),
            (_EMAIL, data.applicant.email or "", "Email", True),
            (_PHONE, data.applicant.phone or "", "Phone", False),
            (_LINKEDIN, data.applicant.linkedin or "", "LinkedIn", False),
        ]


# __END__
