#!/usr/bin/env python3
"""Workday auto-fill adapter.

Workday exposes stable ``data-automation-id`` attributes, which is why it is the
first target. This adapter fills the two pages that cost the most by hand:

* **My Information** — contact basics (name split into first/last, email, phone).
* **Work Experience** — one repeating entry per :class:`Role`, with the bullet
  description rendered into the textarea pre-formatted so the user never reformats
  pasted résumé text.

Out of scope (left for the human, by design): account creation, multi-step wizard
navigation, custom date / typeahead widgets, screening questions, and the final
submit. Anything this adapter cannot map confidently is *flagged, not invented*.

NOTE: the ``data-automation-id`` values below are jobjob's best-effort mapping of
    Workday's DOM. They are mirrored exactly by the test fixture; the live selectors
    must be confirmed on a real posting during validation, and adjusted here if a
    tenant differs.
"""

import logging
import re
from typing import TYPE_CHECKING

from jobjob.autofill.adapters._common import split_name
from jobjob.autofill.data import ApplicationData
from jobjob.autofill.report import (
    FilledField,
    FillReport,
    FlaggedField,
    make_fill_report,
)
from jobjob.structure.experience import Role

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

# Re-exported from _common so existing references (and tests) keep resolving here.
__all__ = ["WorkdayAdapter", "split_name", "format_description"]

NAME = "jobjob.autofill.workday"

# Workday is served from *.myworkdayjobs.com (candidate-facing) or *.workday.com.
_WORKDAY_HOST = re.compile(r"(myworkdayjobs\.com|\.workday\.com)", re.IGNORECASE)

# Automation ids for the "My Information" contact fields.
_AID_FIRST_NAME = "legalNameSection_firstName"
_AID_LAST_NAME = "legalNameSection_lastName"
_AID_EMAIL = "email"
_AID_PHONE = "phone-number"

# Automation ids for the repeating "Work Experience" section.
_AID_WORK_ENTRY = "workExperienceEntry"
_AID_WORK_ADD = "workExperienceAdd"
_AID_JOB_TITLE = "jobTitle"
_AID_COMPANY = "company"
_AID_LOCATION = "location"
_AID_CURRENT = "currentlyWorkHere"
_AID_DESCRIPTION = "description"
_AID_START_DATE = "startDate"
_AID_END_DATE = "endDate"

_BULLET = "• "


def format_description(role: Role) -> str:
    """Render a role's description as a clean bullet block for a Workday textarea.

    Each bullet becomes a ``• ``-prefixed line. A description with no bullet lines
    falls back to its stripped raw text, so we never drop content we cannot parse.
    """
    bullets = role.bullets()
    if bullets:
        return "\n".join(f"{_BULLET}{bullet}" for bullet in bullets)
    return role.description.strip()


class WorkdayAdapter:
    """Fill a Workday application from structured profile data."""

    name = "workday"

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(NAME)

    def matches(self, url: str) -> bool:
        """Return True if ``url`` is hosted on a Workday domain."""
        return bool(_WORKDAY_HOST.search(url or ""))

    def fill(self, page: "Page", data: ApplicationData) -> FillReport:
        """Fill the visible Workday fields and report what was/was not handled."""
        filled: list[FilledField] = []
        flagged: list[FlaggedField] = []
        self._fill_my_information(page, data, filled, flagged)
        self._fill_work_experience(page, data, filled, flagged)
        report = make_fill_report(self.name, filled, flagged)
        self._logger.info(
            "Workday fill: %d filled, %d flagged", len(filled), len(flagged)
        )
        return report

    # -- My Information ----------------------------------------------------

    def _fill_my_information(
        self,
        page: "Page",
        data: ApplicationData,
        filled: list[FilledField],
        flagged: list[FlaggedField],
    ) -> None:
        """Fill the contact basics if the My Information fields are on the page."""
        first, last = split_name(data.applicant.name)
        contact = [
            # (automation_id, label, value)
            (_AID_FIRST_NAME, "First name", first),
            (_AID_LAST_NAME, "Last name", last),
            (_AID_EMAIL, "Email", data.applicant.email or ""),
            (_AID_PHONE, "Phone", data.applicant.phone or ""),
        ]
        for automation_id, label, value in contact:
            field = self._field(page, automation_id)
            if field is None:
                continue  # Not on this page (e.g. a later wizard step).
            if not value:
                flagged.append(FlaggedField(label, "not set in profile — fill by hand"))
                continue
            field.fill(value)
            filled.append(FilledField(label, value))

    # -- Work Experience ---------------------------------------------------

    def _fill_work_experience(
        self,
        page: "Page",
        data: ApplicationData,
        filled: list[FilledField],
        flagged: list[FlaggedField],
    ) -> None:
        """Fill one repeating entry per role from the experience set."""
        roles = data.experience.roles
        if not roles:
            return  # EARLY EXIT: nothing to add.
        entries = page.locator(f'[data-automation-id="{_AID_WORK_ENTRY}"]')
        if entries.count() == 0:
            return  # EARLY EXIT: not the work-experience page.

        add_button = self._field(page, _AID_WORK_ADD)
        for index, role in enumerate(roles):
            # Reveal an entry for this role, adding one when the form is short.
            while entries.count() <= index:
                if add_button is None:
                    flagged.append(
                        FlaggedField(
                            f"Work experience #{index + 1} ({role.company})",
                            "no 'Add' control found — add this entry by hand",
                        )
                    )
                    break
                add_button.click()
            if entries.count() <= index:
                continue
            self._fill_role_entry(entries.nth(index), role, index, filled, flagged)

    def _fill_role_entry(
        self,
        entry: "Locator",
        role: Role,
        index: int,
        filled: list[FilledField],
        flagged: list[FlaggedField],
    ) -> None:
        """Fill one work-experience entry (scoped to its panel)."""
        prefix = f"Role #{index + 1}"
        text_fields = [
            # (automation_id, label, value, required)
            (_AID_JOB_TITLE, f"{prefix} title", role.title, True),
            (_AID_COMPANY, f"{prefix} company", role.company, True),
            (_AID_LOCATION, f"{prefix} location", role.location, False),
            (_AID_DESCRIPTION, f"{prefix} description", format_description(role), True),
        ]
        for automation_id, label, value, required in text_fields:
            field = self._scoped_field(entry, automation_id)
            if field is None:
                continue
            if not value:
                if required:
                    flagged.append(FlaggedField(label, "no value in profile"))
                continue
            field.fill(value)
            filled.append(FilledField(label, value))

        if role.current:
            checkbox = self._scoped_field(entry, _AID_CURRENT)
            if checkbox is not None:
                checkbox.check()
                filled.append(FilledField(f"{prefix} currently work here", "yes"))

        # Dates are custom Workday widgets — flag, do not guess at the interaction.
        for automation_id, label, value in (
            (_AID_START_DATE, f"{prefix} start date", role.start),
            (_AID_END_DATE, f"{prefix} end date", "" if role.current else role.end),
        ):
            if value and self._scoped_field(entry, automation_id) is not None:
                flagged.append(
                    FlaggedField(label, f"set to {value} (custom date widget)")
                )

    # -- Locator helpers ---------------------------------------------------

    def _field(self, page: "Page", automation_id: str) -> "Locator | None":
        """Return the first matching field on the page, or None if absent."""
        locator = page.locator(f'[data-automation-id="{automation_id}"]')
        return locator.first if locator.count() else None

    def _scoped_field(self, entry: "Locator", automation_id: str) -> "Locator | None":
        """Return the first matching field within an entry, or None if absent."""
        locator = entry.locator(f'[data-automation-id="{automation_id}"]')
        return locator.first if locator.count() else None


# __END__
