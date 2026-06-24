#!/usr/bin/env python3
"""Reference end-to-end tests: the app boots and top-level navigation works.

These establish the harness pattern (``live_app`` + ``page`` fixtures from conftest)
that the rest of the frontend e2e suite follows: drive the real UI, then assert on
rendered text/elements with Playwright's auto-waiting ``expect``.
"""

import re

from playwright.sync_api import Page, expect


def _nav_link(page: Page, label: str):
    """Return the top-nav anchor with the given visible text."""
    return page.locator(f"//nav//a[normalize-space(text())='{label}']")


def test_dashboard_loads(page: Page, live_app: str) -> None:
    """The SPA mounts and the Dashboard renders its heading."""
    page.goto(live_app + "/")
    expect(page.locator("//h1[normalize-space()='Dashboard']")).to_be_visible()


def test_nav_shows_core_links(page: Page, live_app: str) -> None:
    """The primary nav exposes the expected destinations."""
    page.goto(live_app + "/")
    expect(page.locator("nav").first).to_be_visible()
    for label in ("Dashboard", "Queue", "Static Content", "Prompts"):
        expect(_nav_link(page, label)).to_be_visible()


def test_navigate_to_prompts_page(page: Page, live_app: str) -> None:
    """Clicking the Prompts nav link loads the prompt editor with its catalog."""
    page.goto(live_app + "/")
    _nav_link(page, "Prompts").click()
    expect(page.locator("//h1[normalize-space()='Prompts']")).to_be_visible()
    # The catalog lists the generation prompts; "Cover letter" is one of them.
    expect(page.locator("body")).to_contain_text("Cover letter")


def test_settings_cog_opens_config(page: Page, live_app: str) -> None:
    """The header cog button navigates to the configuration page."""
    page.goto(live_app + "/")
    page.locator("header button[aria-label='Settings']").click()
    expect(page.locator("//h1[normalize-space()='Configuration']")).to_be_visible()
    expect(page).to_have_url(re.compile(r"#config$"))


def test_footer_reports_issue_link(page: Page, live_app: str) -> None:
    """The footer shows the copyright line and a Report an issue link."""
    page.goto(live_app + "/")
    footer = page.locator("footer")
    expect(footer).to_be_visible()
    expect(footer).to_contain_text("inquisitive-village-idiot")
    expect(
        footer.locator("xpath=.//a[normalize-space()='Report an issue']")
    ).to_have_attribute(
        "href", re.compile(r"github\.com/inquisitive-village-idiot/jobjob/issues$")
    )
