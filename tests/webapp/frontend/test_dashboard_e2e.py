#!/usr/bin/env python3
"""End-to-end tests for the Dashboard page.

Covers: Applications/Profiles tab toggle changes the visible section heading;
"Refresh" button is present.
"""

from playwright.sync_api import Page, expect


def _open_dashboard(page: Page, live_app: str) -> None:
    page.goto(live_app + "/")
    expect(page.locator("//h1[normalize-space()='Dashboard']")).to_be_visible()


def test_dashboard_applications_tab_heading(page: Page, live_app: str) -> None:
    """Applications tab (default) shows the 'Completed Applications' heading."""
    _open_dashboard(page, live_app)
    # The h2 heading is uppercased via CSS; get_by_role name matching is
    # case-insensitive, so no translate() gymnastics are needed.
    expect(
        page.get_by_role("heading", name="Completed Applications", exact=False)
    ).to_be_visible()


def test_dashboard_profiles_tab_heading(page: Page, live_app: str) -> None:
    """Clicking the Profiles tab shows the 'Completed Profiles' section heading."""
    _open_dashboard(page, live_app)
    page.locator("//button[normalize-space(text())='Profiles']").click()
    expect(
        page.get_by_role("heading", name="Completed Profiles", exact=False)
    ).to_be_visible()


def test_dashboard_refresh_button_present(page: Page, live_app: str) -> None:
    """The Dashboard page has a visible 'Refresh' button."""
    _open_dashboard(page, live_app)
    expect(page.locator("//button[normalize-space(text())='Refresh']")).to_be_visible()
