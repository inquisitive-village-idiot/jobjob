#!/usr/bin/env python3
"""Workable auto-fill adapter.

Workable postings (``apply.workable.com`` and ``*.workable.com``) use a single-page
form with separate first/last name fields keyed by ``firstname``/``lastname`` (plus
``email``/``phone``). Best-effort selectors mirrored by the fixture; résumé upload,
custom questions, and submit are left to the human.
"""

import re

from jobjob.autofill.adapters._common import ContactFormAdapter, ContactSpec, split_name
from jobjob.autofill.data import ApplicationData

_FIRST_NAME = (
    'input[name="firstname"]',
    "#firstname",
    'input[autocomplete="given-name"]',
)
_LAST_NAME = (
    'input[name="lastname"]',
    "#lastname",
    'input[autocomplete="family-name"]',
)
_EMAIL = ('input[name="email"]', 'input[type="email"]', 'input[autocomplete="email"]')
_PHONE = ('input[name="phone"]', 'input[type="tel"]', 'input[autocomplete="tel"]')
_LINKEDIN = ('input[name*="linkedin" i]', 'input[aria-label*="linkedin" i]')


class WorkableAdapter(ContactFormAdapter):
    """Fill the contact basics of a Workable application."""

    name = "workable"
    host = re.compile(r"workable\.com", re.IGNORECASE)

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
