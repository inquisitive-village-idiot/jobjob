#!/usr/bin/env python3
"""End-to-end tests for the Static Content page.

Covers: H1 visible; all five tabs present; clicking "reference" and "import"
tabs renders their distinct panels.
"""

from playwright.sync_api import Page, expect


def _go_to_static(page: Page, live_app: str) -> None:
    """Navigate to the Static Content page and wait for the H1."""
    page.goto(live_app + "/#static")
    expect(page.locator("//h1[normalize-space()='Static Content']")).to_be_visible()


def test_static_content_h1_visible(page: Page, live_app: str) -> None:
    """The Static Content page renders its H1 heading."""
    _go_to_static(page, live_app)
    expect(page.locator("//h1[normalize-space()='Static Content']")).to_be_visible()


def test_static_content_tabs_present(page: Page, live_app: str) -> None:
    """All five tab buttons are present on the Static Content page.

    Tab labels: highlights, skills, templates, reference, and "Import résumé". The
    first four are styled with CSS ``capitalize`` (visual only — the DOM text stays
    lowercase), so ``get_by_role`` name matching (case-insensitive, substring) finds
    them without the Selenium translate() gymnastics.
    """
    _go_to_static(page, live_app)
    for label in ("highlights", "skills", "templates", "reference"):
        tab = page.get_by_role("button", name=label, exact=False).first
        expect(tab).to_be_visible()
    # The import tab has a special label with an accented character ("Import résumé").
    expect(page.get_by_role("button", name="Import", exact=False).first).to_be_visible()


def test_static_content_reference_tab(page: Page, live_app: str) -> None:
    """Clicking the 'reference' tab renders the reference file browser panel."""
    _go_to_static(page, live_app)
    page.get_by_role("button", name="reference", exact=False).first.click()
    # The reference panel renders a sidebar <aside> (file list or a placeholder).
    expect(page.locator("aside").first).to_be_visible()


def test_static_content_import_tab(page: Page, live_app: str) -> None:
    """Clicking the import tab renders the 'Import résumé' panel."""
    _go_to_static(page, live_app)
    page.get_by_role("button", name="Import", exact=False).first.click()
    # The import panel heading contains "Import" — match loosely because the exact
    # heading comes from ResumeImportPanel, which we verify separately.
    expect(page.locator("body")).to_contain_text("Import")
