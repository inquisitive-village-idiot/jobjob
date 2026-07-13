#!/usr/bin/env python3
"""End-to-end tests for the Contacts page (the enrich domain as entities).

Covers: heading; pending and contacts sections render their empty states.
"""

from playwright.sync_api import Page, expect


def _go_to_contacts(page: Page, live_app: str) -> None:
    page.goto(live_app + "/#contacts")
    expect(page.locator("//h1[normalize-space()='Contacts']")).to_be_visible()


def test_contacts_h1_visible(page: Page, live_app: str) -> None:
    _go_to_contacts(page, live_app)
    expect(page.locator("//h1[normalize-space()='Contacts']")).to_be_visible()


def test_pending_section_renders(page: Page, live_app: str) -> None:
    _go_to_contacts(page, live_app)
    expect(
        page.get_by_role("heading", name="Pending", exact=False).first
    ).to_be_visible()
    expect(
        page.locator(
            "//*[contains(normalize-space(text()), 'No pending profiles') or "
            "contains(normalize-space(text()), 'data/profiles')]"
        ).first
    ).to_be_visible()


def test_contacts_section_renders(page: Page, live_app: str) -> None:
    _go_to_contacts(page, live_app)
    expect(
        page.locator(
            "//*[contains(normalize-space(text()), 'No enriched contacts') or "
            "contains(normalize-space(text()), 'Person')]"
        ).first
    ).to_be_visible()
