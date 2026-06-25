#!/usr/bin/env python3
"""End-to-end tests for the Prompts page.

Covers: H1 visible; catalog lists generation prompts; clicking a prompt shows a
non-empty textarea and the "Default" badge.
"""

from playwright.sync_api import Page, expect


def _go_to_prompts(page: Page, live_app: str) -> None:
    """Navigate to the Prompts page and wait for the H1."""
    page.goto(live_app + "/#prompts")
    expect(page.locator("//h1[normalize-space()='Prompts']")).to_be_visible()


def test_prompts_h1_visible(page: Page, live_app: str) -> None:
    """The Prompts page renders its H1 heading."""
    _go_to_prompts(page, live_app)
    expect(page.locator("//h1[normalize-space()='Prompts']")).to_be_visible()


def test_prompts_catalog_generation_titles(page: Page, live_app: str) -> None:
    """The sidebar catalog lists at least the expected generation prompt titles."""
    _go_to_prompts(page, live_app)
    # Wait for the prompt list to load (the 'Generation' group heading appears).
    expect(page.get_by_text("Generation", exact=False).first).to_be_visible()
    body = page.locator("body")
    for title in ("Resume objective", "Cover letter", "Skills gap analysis"):
        expect(body).to_contain_text(title)


def test_prompts_select_cover_letter_shows_textarea_and_badge(
    page: Page, live_app: str
) -> None:
    """Clicking 'Cover letter' shows a non-empty textarea and Default badge."""
    _go_to_prompts(page, live_app)
    page.locator("//button[.//span[normalize-space(text())='Cover letter']]").click()

    # A textarea must appear and be non-empty.
    textarea = page.locator("textarea").first
    expect(textarea).to_be_visible()
    assert textarea.input_value() != ""

    # The "Default" badge (or "Customized") must be visible next to the prompt title.
    badge = page.locator(
        "//*[normalize-space(text())='Default' "
        "or normalize-space(text())='Customized']"
    )
    expect(badge.first).to_be_visible()
