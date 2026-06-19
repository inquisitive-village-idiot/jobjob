#!/usr/bin/env python3
"""Applicant identity used in cover-letter headers.

NOTE: values come from runtime config (config/.env via jobjob.config), not from
    defaults defined here. This is a pure data structure.
"""

import dataclasses as dcs


@dcs.dataclass(frozen=True)
class Applicant:
    """Applicant contact details for document headers.

    Attributes:
        name: Full name (with credentials).
        phone: Contact phone.
        email: Contact email.
        linkedin: LinkedIn URL.
    """

    name: str | None = None
    phone: str | None = None
    email: str | None = None
    linkedin: str | None = None

    def contact_line(self) -> str:
        """Return the ``phone | email | linkedin`` header, omitting unset parts."""
        return " | ".join(part for part in (self.phone, self.email, self.linkedin) if part)


# __END__
