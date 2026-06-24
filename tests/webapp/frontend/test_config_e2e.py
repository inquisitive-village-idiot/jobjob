#!/usr/bin/env python3
"""End-to-end tests for the Configuration page.

Covers the restructured Settings page: a left nav of App / Profiles / About, with
profiles shown as tabs in the main body (active first) plus a "＋" tab to add one,
the whole-profile Edit toggle co-located with the fields, the read-only guard on the
bundled ``example`` profile, and the Update panel living under About.
"""

import re

from playwright.sync_api import Page, expect


def _open_config(page: Page, live_app: str) -> None:
    page.goto(live_app + "/#config")
    expect(page.locator("//h1[normalize-space()='Configuration']")).to_be_visible()


def _nav_button(page: Page, label: str):
    """Return a left-nav section button (App / Profiles / About)."""
    return page.locator(
        "//nav[@aria-label='Configuration sections']"
        f"//button[normalize-space(text())='{label}']"
    )


def _sidebar(page: Page):
    return page.locator("nav[aria-label='Configuration sections']")


def _open_profiles(page: Page):
    """Switch to the Profiles section and wait for the profile tab list."""
    _nav_button(page, "Profiles").click()
    tablist = page.locator("div[role='tablist'][aria-label='Profiles']")
    expect(tablist).to_be_visible()
    return tablist


def _profile_tab(page: Page, label: str):
    """Return the body profile tab whose visible text equals ``label``."""
    return page.locator(
        "//div[@role='tablist'][@aria-label='Profiles']"
        f"//button[normalize-space(text())='{label}']"
    )


def test_config_nav_has_three_sections(page: Page, live_app: str) -> None:
    """The left nav exposes App, Profiles, and About."""
    _open_config(page, live_app)
    for label in ("App", "Profiles", "About"):
        expect(_nav_button(page, label)).to_be_visible()


def test_profiles_section_shows_tabs_and_add(page: Page, live_app: str) -> None:
    """Profiles render as body tabs (incl. the example) plus an add (＋) tab."""
    _open_config(page, live_app)
    _open_profiles(page)
    expect(_profile_tab(page, "example")).to_be_visible()
    add = page.locator(
        "//div[@role='tablist'][@aria-label='Profiles']"
        "//button[@aria-label='Add a profile']"
    )
    expect(add).to_be_visible()


def test_example_profile_is_read_only(page: Page, live_app: str) -> None:
    """Selecting the read-only example profile disables editing."""
    _open_config(page, live_app)
    _open_profiles(page)
    _profile_tab(page, "example").click()

    # The whole-profile Edit toggle (beside the fields) is present but disabled.
    # to_be_disabled auto-waits and re-evaluates, so the async re-render can't hand
    # back a stale reference the way Selenium's find_elements could.
    disabled_edit = page.locator("//button[normalize-space()='Edit' and @disabled]")
    expect(disabled_edit.first).to_be_visible()
    expect(page.locator("body")).to_contain_text("read-only")


def test_app_sidebar_expands_subsections(page: Page, live_app: str) -> None:
    """The App section expands into its config-schema subsections in the sidebar."""
    _open_config(page, live_app)
    # App is the default section; its schema groups (e.g. Google) show as anchors.
    anchor = _sidebar(page).locator("xpath=.//button[normalize-space()='Google']")
    expect(anchor).to_be_visible()
    anchor.click()
    expect(_sidebar(page)).to_contain_text("Google")


def test_profile_tab_shows_location_and_dir_pills(page: Page, live_app: str) -> None:
    """Selecting a profile shows its location and resource-dir file-count pills."""
    _open_config(page, live_app)
    _open_profiles(page)
    _profile_tab(page, "example").click()
    expect(
        page.locator("//h3[normalize-space()='Location & directories']")
    ).to_be_visible()
    # The example profile ships content/ and reference/ dirs, shown as pills.
    body = page.locator("body")
    expect(body).to_contain_text("content")
    expect(body).to_contain_text("reference")


def test_add_profile_tab_opens_form(page: Page, live_app: str) -> None:
    """The ＋ tab opens the create / duplicate / register add-profile form."""
    _open_config(page, live_app)
    _open_profiles(page)
    page.locator(
        "//div[@role='tablist'][@aria-label='Profiles']"
        "//button[@aria-label='Add a profile']"
    ).click()
    # The register action and the name field are part of the add form.
    expect(
        page.locator("//button[normalize-space()='Register folder']")
    ).to_be_visible()
    expect(page.locator("body")).to_contain_text("New profile name")


def test_about_section_shows_updates_and_issue_link(page: Page, live_app: str) -> None:
    """The About section hosts the Update panel and a Report-an-issue link."""
    _open_config(page, live_app)
    _nav_button(page, "About").click()
    expect(page.locator("//h2[normalize-space()='Updates']")).to_be_visible()
    # Scope to the main content (the footer has its own issue link, covered by the
    # navigation suite) so the locator is unambiguous under Playwright strict mode.
    expect(
        page.get_by_role("main").get_by_role("link", name="Report an issue")
    ).to_have_attribute("href", re.compile(r"^https://github\.com/"))
