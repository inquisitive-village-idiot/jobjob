#!/usr/bin/env python3
"""Browser e2e for the Greenhouse adapter's ``fill`` DOM pass.

Drives ``GreenhouseAdapter.fill`` against a local Greenhouse-like fixture (no live
site). Marked ``e2e`` so the default suite skips it; run with ``pytest -m e2e``.
"""

from contextlib import contextmanager
from pathlib import Path

import pytest

from jobjob.autofill.adapters.greenhouse import GreenhouseAdapter
from jobjob.autofill.data import ApplicationData
from jobjob.structure.applicant import Applicant

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

pytestmark = pytest.mark.e2e

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "greenhouse_application.html"
)


@contextmanager
def _page():
    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(_FIXTURE.as_uri())
            yield page
        finally:
            browser.close()


def _value(page, selector: str) -> str:
    return page.locator(selector).input_value()


def _data(**kwargs) -> ApplicationData:
    base = dict(
        name="Ada B. Lovelace",
        email="ada@example.com",
        phone="555-0100",
        linkedin="linkedin.com/in/adalovelace",
    )
    base.update(kwargs)
    return ApplicationData(applicant=Applicant(**base))


def test_fills_contact_basics():
    with _page() as page:
        GreenhouseAdapter().fill(page, _data())
        assert _value(page, "#first_name") == "Ada B."
        assert _value(page, "#last_name") == "Lovelace"
        assert _value(page, "#email") == "ada@example.com"
        assert _value(page, "#phone") == "555-0100"
        assert (
            _value(page, 'input[name*="linkedin" i]') == "linkedin.com/in/adalovelace"
        )


def test_leaves_resume_upload_alone():
    with _page() as page:
        GreenhouseAdapter().fill(page, _data())
        # The file input must not be touched (no value set/cleared).
        assert _value(page, "#resume") == ""


def test_flags_missing_required_contact():
    with _page() as page:
        report = GreenhouseAdapter().fill(page, _data(name="Cher", email=None))
        flagged = {f.label for f in report.flagged}
        assert "Last name" in flagged  # single-word name -> no last
        assert "Email" in flagged
        # Phone is optional: present field, value supplied -> filled, not flagged.
        assert "Phone" not in flagged


# __END__
