#!/usr/bin/env python3
"""End-to-end tests for the Profiles page (registry + content editors).

Covers: H1; registry section; all five editor tabs; reference and import panels.
"""

from playwright.sync_api import Page, expect


def _go_to_profiles(page: Page, live_app: str) -> None:
    """Navigate to the Profiles page and wait for the H1."""
    page.goto(live_app + "/#profiles")
    expect(page.locator("//h1[normalize-space()='Profiles']")).to_be_visible()


def test_profiles_h1_visible(page: Page, live_app: str) -> None:
    _go_to_profiles(page, live_app)
    expect(page.locator("//h1[normalize-space()='Profiles']")).to_be_visible()


def test_legacy_static_hash_falls_back(page: Page, live_app: str) -> None:
    """Pre-restructure bookmarks (#static) land on the Profiles page."""
    page.goto(live_app + "/#static")
    expect(page.locator("//h1[normalize-space()='Profiles']")).to_be_visible()


def test_registry_section_present(page: Page, live_app: str) -> None:
    """The registry header renders with a link to Settings for management."""
    _go_to_profiles(page, live_app)
    expect(page.get_by_role("heading", name="Registry", exact=False)).to_be_visible()
    expect(
        page.locator("//a[contains(normalize-space(text()), 'Manage profiles')]")
    ).to_be_visible()


def test_content_editor_tabs_present(page: Page, live_app: str) -> None:
    """All five editor tab buttons are present (absorbed Static Content).

    Tab labels: highlights, skills, templates, reference, and "Import résumé". The
    first four are styled with CSS ``capitalize`` (visual only — the DOM text stays
    lowercase), so ``get_by_role`` name matching (case-insensitive, substring) finds
    them without the Selenium translate() gymnastics.
    """
    _go_to_profiles(page, live_app)
    for label in ("highlights", "skills", "templates", "reference"):
        tab = page.get_by_role("button", name=label, exact=False).first
        expect(tab).to_be_visible()
    expect(page.get_by_role("button", name="Import", exact=False).first).to_be_visible()


def test_reference_tab(page: Page, live_app: str) -> None:
    """Clicking the 'reference' tab renders the reference file browser panel."""
    _go_to_profiles(page, live_app)
    page.get_by_role("button", name="reference", exact=False).first.click()
    expect(page.locator("aside").first).to_be_visible()


def test_import_tab(page: Page, live_app: str) -> None:
    """Clicking the import tab renders the 'Import résumé' panel."""
    _go_to_profiles(page, live_app)
    page.get_by_role("button", name="Import", exact=False).first.click()
    expect(page.locator("body")).to_contain_text("Import")
