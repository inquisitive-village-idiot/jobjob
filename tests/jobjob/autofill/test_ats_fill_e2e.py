#!/usr/bin/env python3
"""Browser e2e for the single-page ATS adapters (Lever/Ashby/Workable/SmartRecruiters).

Each adapter is driven against its local fixture (no live site) and asserted to fill
the contact basics and leave the résumé file input untouched. Marked ``e2e`` so the
default suite skips it; run with ``pytest -m e2e``.
"""

from contextlib import contextmanager
from pathlib import Path

import pytest

from jobjob.autofill.adapters.ashby import AshbyAdapter
from jobjob.autofill.adapters.lever import LeverAdapter
from jobjob.autofill.adapters.smartrecruiters import SmartRecruitersAdapter
from jobjob.autofill.adapters.workable import WorkableAdapter
from jobjob.autofill.data import ApplicationData
from jobjob.structure.applicant import Applicant

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

pytestmark = pytest.mark.e2e

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

_DATA = ApplicationData(
    applicant=Applicant(
        name="Ada B. Lovelace",
        email="ada@example.com",
        phone="555-0100",
        linkedin="linkedin.com/in/adalovelace",
    )
)


@contextmanager
def _page(fixture_name: str):
    with sync_playwright() as play:
        browser = play.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto((_FIXTURES / fixture_name).as_uri())
            yield page
        finally:
            browser.close()


def _value(page, selector: str) -> str:
    return page.locator(selector).input_value()


# Single full-name boards -------------------------------------------------


def test_lever_fills_full_name_and_basics():
    with _page("lever_application.html") as page:
        LeverAdapter().fill(page, _DATA)
        assert _value(page, 'input[name="name"]') == "Ada B. Lovelace"
        assert _value(page, 'input[name="email"]') == "ada@example.com"
        assert _value(page, 'input[name="phone"]') == "555-0100"
        assert _value(page, 'input[name="urls[LinkedIn]"]') == (
            "linkedin.com/in/adalovelace"
        )
        assert _value(page, 'input[name="resume"]') == ""  # untouched


def test_ashby_fills_full_name_and_basics():
    with _page("ashby_application.html") as page:
        AshbyAdapter().fill(page, _DATA)
        assert _value(page, 'input[name="_systemfield_name"]') == "Ada B. Lovelace"
        assert _value(page, 'input[name="_systemfield_email"]') == "ada@example.com"
        assert _value(page, 'input[name="_systemfield_phone"]') == "555-0100"


# First/last-name boards --------------------------------------------------


def test_workable_fills_first_last_and_basics():
    with _page("workable_application.html") as page:
        WorkableAdapter().fill(page, _DATA)
        assert _value(page, 'input[name="firstname"]') == "Ada B."
        assert _value(page, 'input[name="lastname"]') == "Lovelace"
        assert _value(page, 'input[name="email"]') == "ada@example.com"
        assert _value(page, 'input[name="resume"]') == ""  # untouched


def test_smartrecruiters_fills_first_last_and_basics():
    with _page("smartrecruiters_application.html") as page:
        SmartRecruitersAdapter().fill(page, _DATA)
        assert _value(page, "#firstName") == "Ada B."
        assert _value(page, "#lastName") == "Lovelace"
        assert _value(page, "#email") == "ada@example.com"
        assert _value(page, "#phoneNumber") == "555-0100"


# __END__
