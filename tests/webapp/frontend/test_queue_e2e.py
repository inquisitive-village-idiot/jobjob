#!/usr/bin/env python3
"""End-to-end tests for the Queue page.

Covers: heading renders; empty-state text for each section is visible.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _nav_link(driver, label):
    """Return the top-nav anchor with the given visible text."""
    return driver.find_element(By.XPATH, f"//nav//a[normalize-space(text())='{label}']")


def _go_to_queue(driver, live_app):
    """Navigate to the Queue page and wait for the H1."""
    driver.get(live_app + "/#queue")
    _wait(driver).until(
        EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Queue']"))
    )


def test_queue_h1_visible(driver, live_app):
    """The Queue page renders its H1 heading."""
    _go_to_queue(driver, live_app)
    h1 = driver.find_element(By.XPATH, "//h1[normalize-space()='Queue']")
    assert h1.is_displayed()


def test_queue_nav_link(driver, live_app):
    """Clicking the Queue nav link navigates to the Queue page."""
    driver.get(live_app + "/")
    _wait(driver).until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav")))
    _nav_link(driver, "Queue").click()

    h1 = _wait(driver).until(
        EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Queue']"))
    )
    assert h1.is_displayed()


def test_queue_empty_state_apply_section(driver, live_app):
    """With no queued JDs the Apply section shows its empty-state message."""
    _go_to_queue(driver, live_app)

    # Wait for queue data to load — either queue items or the empty-state text.
    _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains(normalize-space(text()), 'No pending JDs') or "
                "contains(normalize-space(text()), 'data/jobs')]",
            )
        )
    )

    body = driver.find_element(By.TAG_NAME, "body").text
    assert "No pending JDs" in body or "data/jobs" in body


def test_queue_scheduled_section_renders(driver, live_app):
    """The Queued/Scheduled section renders (heading present, empty-state or items)."""
    _go_to_queue(driver, live_app)

    # The scheduled section h2 has 'Queued' in it (uppercased via CSS).
    heading = _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//h2[contains("
                "translate(normalize-space(text()),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),"
                "'queued')]",
            )
        )
    )
    assert heading.is_displayed()

    # After data loads, either items or "No scheduled jobs running." appears.
    _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains(normalize-space(text()), 'No scheduled jobs') or "
                "contains(normalize-space(text()), 'Schedule')]",
            )
        )
    )
