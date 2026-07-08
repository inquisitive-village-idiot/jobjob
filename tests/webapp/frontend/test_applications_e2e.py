#!/usr/bin/env python3
"""End-to-end tests for the Applications page (the unified entity table).

Covers: heading; state filter chips; sort control; the Add-JD panel; Refresh.
"""

from playwright.sync_api import Page, expect


def _open_applications(page: Page, live_app: str) -> None:
    page.goto(live_app + "/#applications")
    expect(page.locator("//h1[normalize-space()='Applications']")).to_be_visible()


def test_state_filter_chips_present(page: Page, live_app: str) -> None:
    """The All chip renders once records load (state is a column, not tabs)."""
    _open_applications(page, live_app)
    expect(
        page.locator("//button[starts-with(normalize-space(text()), 'All')]")
    ).to_be_visible()


def test_sort_control_present(page: Page, live_app: str) -> None:
    """The sort select offers Company / Role fit / ATS coverage."""
    _open_applications(page, live_app)
    select = page.locator("//label[contains(., 'Sort')]//select")
    expect(select).to_be_visible()
    for label in ("Company", "Role fit", "ATS coverage"):
        expect(
            select.locator(f"//option[normalize-space(text())='{label}']")
        ).to_have_count(1)


def test_add_jd_panel_present(page: Page, live_app: str) -> None:
    """The Add-JD capture panel lives on the Applications page."""
    _open_applications(page, live_app)
    expect(
        page.locator("//button[contains(normalize-space(text()), 'Capture & Build')]")
    ).to_be_visible()


def test_refresh_button_present(page: Page, live_app: str) -> None:
    _open_applications(page, live_app)
    expect(page.locator("//button[normalize-space(text())='Refresh']")).to_be_visible()
