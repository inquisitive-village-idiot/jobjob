#!/usr/bin/env python3
"""Browser e2e for the generic fallback adapter's ``fill`` DOM pass.

Drives ``GenericAdapter.fill`` against a plain heuristic form (first/last via
autocomplete) and against the Lever fixture (a single full-name field), proving both
form shapes are handled. Marked ``e2e``; run with ``pytest -m e2e``. No live site.
"""

from contextlib import contextmanager
from pathlib import Path

import pytest

from jobjob.autofill.adapters.generic import GenericAdapter
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


def test_fills_first_last_form_by_heuristics():
    with _page("generic_application.html") as page:
        GenericAdapter().fill(page, _DATA)
        assert _value(page, 'input[autocomplete="given-name"]') == "Ada B."
        assert _value(page, 'input[autocomplete="family-name"]') == "Lovelace"
        assert _value(page, 'input[type="email"]') == "ada@example.com"
        assert _value(page, 'input[type="tel"]') == "555-0100"
        assert _value(page, 'input[name="cv"]') == ""  # résumé untouched


def test_fills_single_full_name_form():
    # The Lever fixture has one name="name" field; the generic full-name selectors
    # (exact match) fill it without colliding with any first/last field.
    with _page("lever_application.html") as page:
        report = GenericAdapter().fill(page, _DATA)
        assert _value(page, 'input[name="name"]') == "Ada B. Lovelace"
        # No first/last fields on this form -> they are skipped, not flagged.
        flagged = {f.label for f in report.flagged}
        assert "First name" not in flagged
        assert "Last name" not in flagged


# __END__
