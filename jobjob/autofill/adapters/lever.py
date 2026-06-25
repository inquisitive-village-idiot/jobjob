#!/usr/bin/env python3
"""Lever auto-fill adapter.

Lever postings (``jobs.lever.co``) use a single-page form whose fields are keyed by
``name`` (``name``, ``email``, ``phone``, ``urls[LinkedIn]``). Notably Lever has ONE
full-name field rather than separate first/last, so the full applicant name is filled
verbatim. Best-effort selectors mirrored by the fixture; résumé upload, custom
questions, and submit are left to the human.
"""

import re

from jobjob.autofill.adapters._common import ContactFormAdapter, ContactSpec
from jobjob.autofill.data import ApplicationData

_NAME = ('input[name="name"]', 'input[autocomplete="name"]', 'input[name*="name" i]')
_EMAIL = ('input[name="email"]', 'input[type="email"]', 'input[autocomplete="email"]')
_PHONE = ('input[name="phone"]', 'input[type="tel"]', 'input[autocomplete="tel"]')
_LINKEDIN = ('input[name="urls[LinkedIn]"]', 'input[name*="linkedin" i]')


class LeverAdapter(ContactFormAdapter):
    """Fill the contact basics of a Lever application (single full-name field)."""

    name = "lever"
    host = re.compile(r"lever\.co", re.IGNORECASE)

    def contact_specs(self, data: ApplicationData) -> list[ContactSpec]:
        return [
            (_NAME, data.applicant.name or "", "Full name", True),
            (_EMAIL, data.applicant.email or "", "Email", True),
            (_PHONE, data.applicant.phone or "", "Phone", False),
            (_LINKEDIN, data.applicant.linkedin or "", "LinkedIn", False),
        ]


# __END__
