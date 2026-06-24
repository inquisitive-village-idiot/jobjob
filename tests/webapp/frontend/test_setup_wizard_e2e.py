#!/usr/bin/env python3
"""End-to-end tests for the setup wizard's Profile step (Batch B #2).

The first-run wizard is pre-dismissed by the harness, so these reopen it from the
account menu and drive to the new Profile step (register an existing profile folder /
bootstrap from a résumé).
"""

from playwright.sync_api import Page, expect


def _open_wizard(page: Page, live_app: str) -> None:
    page.goto(live_app + "/")
    # Open the account menu, then "Run setup".
    page.locator("header button[title='Profile and settings']").click()
    page.locator("//button[normalize-space()='Run setup']").click()
    expect(page.locator("//h2[normalize-space()='Welcome to jobjob']")).to_be_visible()


def _next(page: Page) -> None:
    page.locator("//button[normalize-space()='Next']").click()


def test_wizard_profile_step_has_register_and_import(page: Page, live_app: str) -> None:
    """The wizard's Profile step offers both register-existing and résumé bootstrap."""
    _open_wizard(page, live_app)
    # Steps: Anthropic key -> Google -> Profile -> Your details. Advance twice.
    _next(page)
    _next(page)
    expect(
        page.locator("//h3[normalize-space()='Use an existing profile folder']")
    ).to_be_visible()
    expect(
        page.locator("//h3[normalize-space()='Bootstrap from a résumé']")
    ).to_be_visible()
