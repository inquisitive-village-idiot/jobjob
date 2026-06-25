#!/usr/bin/env python3
"""End-to-end tests for the Queue page.

Covers: heading renders; empty-state text for each section is visible.
"""

from playwright.sync_api import Page, expect


def _nav_link(page: Page, label: str):
    """Return the top-nav anchor with the given visible text."""
    return page.locator(f"//nav//a[normalize-space(text())='{label}']")


def _go_to_queue(page: Page, live_app: str) -> None:
    """Navigate to the Queue page and wait for the H1."""
    page.goto(live_app + "/#queue")
    expect(page.locator("//h1[normalize-space()='Queue']")).to_be_visible()


def test_queue_h1_visible(page: Page, live_app: str) -> None:
    """The Queue page renders its H1 heading."""
    _go_to_queue(page, live_app)
    expect(page.locator("//h1[normalize-space()='Queue']")).to_be_visible()


def test_queue_nav_link(page: Page, live_app: str) -> None:
    """Clicking the Queue nav link navigates to the Queue page."""
    page.goto(live_app + "/")
    _nav_link(page, "Queue").click()
    expect(page.locator("//h1[normalize-space()='Queue']")).to_be_visible()


def test_queue_empty_state_apply_section(page: Page, live_app: str) -> None:
    """With no queued JDs the Apply section shows its empty-state message."""
    _go_to_queue(page, live_app)
    # Either queue items or the empty-state text appears once queue data loads.
    expect(
        page.locator(
            "//*[contains(normalize-space(text()), 'No pending JDs') or "
            "contains(normalize-space(text()), 'data/jobs')]"
        ).first
    ).to_be_visible()


def test_queue_scheduled_section_renders(page: Page, live_app: str) -> None:
    """The Queued/Scheduled section renders (heading present, empty-state or items)."""
    _go_to_queue(page, live_app)
    # The scheduled section h2 has 'Queued' in it (uppercased via CSS).
    expect(
        page.get_by_role("heading", name="Queued", exact=False).first
    ).to_be_visible()
    # After data loads, either items or "No scheduled jobs running." appears.
    expect(
        page.locator(
            "//*[contains(normalize-space(text()), 'No scheduled jobs') or "
            "contains(normalize-space(text()), 'Schedule')]"
        ).first
    ).to_be_visible()
