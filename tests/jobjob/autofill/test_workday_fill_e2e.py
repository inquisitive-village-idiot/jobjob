#!/usr/bin/env python3
"""Browser e2e test for the Workday adapter's ``fill`` DOM pass.

Drives ``WorkdayAdapter.fill`` against a local Workday-like HTML fixture (no live
site). Marked ``e2e`` so the default suite skips it; run with ``pytest -m e2e``.
The fixture's ``data-automation-id`` values mirror the adapter exactly.
"""

from contextlib import contextmanager
from pathlib import Path

import pytest

from jobjob.autofill.adapters.workday import WorkdayAdapter
from jobjob.autofill.data import ApplicationData
from jobjob.structure.applicant import Applicant
from jobjob.structure.experience import Role, make_experience_set

# Skip the whole module (and avoid a collection-time ImportError) when the optional
# Playwright extra is not installed. importorskip returns the module on success.
sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

pytestmark = pytest.mark.e2e

_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "workday_application.html"


@contextmanager
def _page():
    """Yield a fresh page loaded with the fixture, tearing the browser down after."""
    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(_FIXTURE.as_uri())
            yield page
        finally:
            browser.close()


def _aid(page, automation_id: str):
    return page.locator(f'[data-automation-id="{automation_id}"]')


def _sample_data() -> ApplicationData:
    roles = [
        Role(
            company="The Lattice Review",
            title="Senior Science Correspondent",
            location="Remote",
            start="2021-04",
            current=True,
            description="- Lead the print science desk.\n- Built a data workflow.",
        ),
        Role(
            company="The Lattice Review",
            title="Science Correspondent",
            location="Boston, MA",
            start="2018-06",
            end="2021-04",
            description="- Covered materials science.",
        ),
        Role(
            company="Meridian Press",
            title="Staff Writer",
            location="Boston, MA",
            start="2015-09",
            end="2018-05",
            description="- Reported on deadline.",
        ),
    ]
    return ApplicationData(
        applicant=Applicant(
            name="Ada B. Lovelace",
            email="ada@example.com",
            phone="555-0100",
        ),
        experience=make_experience_set(roles),
    )


def test_fills_contact_basics():
    with _page() as page:
        WorkdayAdapter().fill(page, _sample_data())
        assert _aid(page, "legalNameSection_firstName").input_value() == "Ada B."
        assert _aid(page, "legalNameSection_lastName").input_value() == "Lovelace"
        assert _aid(page, "email").input_value() == "ada@example.com"
        assert _aid(page, "phone-number").input_value() == "555-0100"


def test_adds_one_entry_per_role():
    with _page() as page:
        WorkdayAdapter().fill(page, _sample_data())
        entries = _aid(page, "workExperienceEntry")
        assert entries.count() == 3


def test_fills_role_fields_and_formats_description():
    with _page() as page:
        WorkdayAdapter().fill(page, _sample_data())
        first = _aid(page, "workExperienceEntry").nth(0)
        assert first.locator('[data-automation-id="jobTitle"]').input_value() == (
            "Senior Science Correspondent"
        )
        assert first.locator('[data-automation-id="company"]').input_value() == (
            "The Lattice Review"
        )
        description = first.locator('[data-automation-id="description"]').input_value()
        assert description == "• Lead the print science desk.\n• Built a data workflow."


def test_checks_currently_work_here_for_current_role():
    with _page() as page:
        WorkdayAdapter().fill(page, _sample_data())
        first = _aid(page, "workExperienceEntry").nth(0)
        assert first.locator('[data-automation-id="currentlyWorkHere"]').is_checked()


def test_flags_date_widgets():
    with _page() as page:
        report = WorkdayAdapter().fill(page, _sample_data())
        labels = {f.label for f in report.flagged}
        assert "Role #1 start date" in labels
        # The current role's end date is suppressed (no value to flag).
        assert "Role #1 end date" not in labels
        assert "Role #2 end date" in labels


def test_flags_unsplittable_name_and_missing_contact():
    data = ApplicationData(applicant=Applicant(name="Cher"))
    with _page() as page:
        report = WorkdayAdapter().fill(page, data)
        assert _aid(page, "legalNameSection_firstName").input_value() == "Cher"
        assert _aid(page, "legalNameSection_lastName").input_value() == ""
        flagged = {f.label for f in report.flagged}
        for label in ("Last name", "Email", "Phone"):
            assert label in flagged


# __END__
