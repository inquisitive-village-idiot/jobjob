#!/usr/bin/env python3
"""Generic fallback auto-fill adapter.

The catch-all for any posting no named adapter recognizes. It fills the contact
basics by *heuristic* selectors — autocomplete tokens, input types, and loose
name/id matches — which work on most standards-compliant forms. It deliberately
covers both shapes: separate first/last fields and a single full-name field (the
full-name selectors are exact matches so they never collide with ``firstname`` /
``lastname`` inputs).

``matches`` returns True for any URL, so this adapter MUST be registered LAST in the
registry — every named adapter takes precedence. As always: *flag, don't invent*, and
never touch the résumé upload or submit.
"""

from jobjob.autofill.adapters._common import ContactFormAdapter, ContactSpec, split_name
from jobjob.autofill.data import ApplicationData

_FIRST_NAME = (
    'input[autocomplete="given-name"]',
    'input[name*="first" i]',
    'input[id*="first" i]',
)
_LAST_NAME = (
    'input[autocomplete="family-name"]',
    'input[name*="last" i]',
    'input[id*="last" i]',
)
# Exact matches only, so these never catch a first/last field.
_FULL_NAME = (
    'input[autocomplete="name"]',
    'input[name="name"]',
    'input[id="name"]',
    'input[aria-label="Full name" i]',
    'input[aria-label="Name" i]',
)
_EMAIL = (
    'input[type="email"]',
    'input[autocomplete="email"]',
    'input[name*="email" i]',
)
_PHONE = (
    'input[type="tel"]',
    'input[autocomplete="tel"]',
    'input[name*="phone" i]',
)
_LINKEDIN = ('input[name*="linkedin" i]', 'input[aria-label*="linkedin" i]')


class GenericAdapter(ContactFormAdapter):
    """Best-effort contact fill for any unrecognized application form."""

    name = "generic"

    def matches(self, url: str) -> bool:
        """Match any URL — this is the fallback, so it must be registered LAST."""
        return True

    def contact_specs(self, data: ApplicationData) -> list[ContactSpec]:
        first, last = split_name(data.applicant.name)
        return [
            # first/last (split) and full-name are mutually exclusive on a given
            # form: whichever fields are absent are skipped, never flagged.
            (_FIRST_NAME, first, "First name", True),
            (_LAST_NAME, last, "Last name", True),
            (_FULL_NAME, data.applicant.name or "", "Full name", True),
            (_EMAIL, data.applicant.email or "", "Email", True),
            (_PHONE, data.applicant.phone or "", "Phone", False),
            (_LINKEDIN, data.applicant.linkedin or "", "LinkedIn", False),
        ]


# __END__
