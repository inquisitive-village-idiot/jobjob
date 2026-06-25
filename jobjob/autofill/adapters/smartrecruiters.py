#!/usr/bin/env python3
"""SmartRecruiters auto-fill adapter.

SmartRecruiters postings (``jobs.smartrecruiters.com``) use a single-page form with
separate first/last name fields keyed by ``firstName``/``lastName`` (plus ``email``
and ``phoneNumber``). Best-effort selectors mirrored by the fixture; résumé upload,
custom questions, and submit are left to the human.
"""

import re

from jobjob.autofill.adapters._common import ContactFormAdapter, ContactSpec, split_name
from jobjob.autofill.data import ApplicationData

_FIRST_NAME = (
    "#firstName",
    'input[name="firstName"]',
    'input[autocomplete="given-name"]',
)
_LAST_NAME = (
    "#lastName",
    'input[name="lastName"]',
    'input[autocomplete="family-name"]',
)
_EMAIL = ("#email", 'input[name="email"]', 'input[type="email"]')
_PHONE = ("#phoneNumber", 'input[name="phoneNumber"]', 'input[type="tel"]')
_LINKEDIN = ('input[name*="linkedin" i]', 'input[aria-label*="linkedin" i]')


class SmartRecruitersAdapter(ContactFormAdapter):
    """Fill the contact basics of a SmartRecruiters application."""

    name = "smartrecruiters"
    host = re.compile(r"smartrecruiters\.com", re.IGNORECASE)

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
