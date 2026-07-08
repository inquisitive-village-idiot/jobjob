#!/usr/bin/env python3
"""End-to-end tests for the Queue page (executions: run history + scheduling).

Covers: heading; run-history section empty state; scheduled section + button.
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
    _go_to_queue(page, live_app)
    expect(page.locator("//h1[normalize-space()='Queue']")).to_be_visible()


def test_queue_nav_link(page: Page, live_app: str) -> None:
    page.goto(live_app + "/")
    _nav_link(page, "Queue").click()
    expect(page.locator("//h1[normalize-space()='Queue']")).to_be_visible()


def test_run_history_section(page: Page, live_app: str) -> None:
    """The runs section renders — either persisted runs or its empty state."""
    _go_to_queue(page, live_app)
    expect(page.get_by_role("heading", name="Runs", exact=False).first).to_be_visible()
    expect(
        page.locator(
            "//*[contains(normalize-space(text()), 'No runs yet') or "
            "contains(normalize-space(text()), 'Build')]"
        ).first
    ).to_be_visible()


def test_scheduled_section_renders(page: Page, live_app: str) -> None:
    """The Scheduled section renders with its Schedule button."""
    _go_to_queue(page, live_app)
    expect(
        page.get_by_role("heading", name="Scheduled", exact=False).first
    ).to_be_visible()
    expect(page.locator("//button[normalize-space(text())='Schedule']")).to_be_visible()
