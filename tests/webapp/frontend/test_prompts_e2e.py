#!/usr/bin/env python3
"""End-to-end tests for the Prompts page.

Covers: H1 visible; catalog lists generation prompts; clicking a prompt shows a
non-empty textarea and the "Default" badge.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _nav_link(driver, label):
    """Return the top-nav anchor with the given visible text."""
    return driver.find_element(By.XPATH, f"//nav//a[normalize-space(text())='{label}']")


def _go_to_prompts(driver, live_app):
    """Navigate to the Prompts page and wait for the H1."""
    driver.get(live_app + "/#prompts")
    _wait(driver).until(
        EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Prompts']"))
    )


def test_prompts_h1_visible(driver, live_app):
    """The Prompts page renders its H1 heading."""
    _go_to_prompts(driver, live_app)
    h1 = driver.find_element(By.XPATH, "//h1[normalize-space()='Prompts']")
    assert h1.is_displayed()


def test_prompts_catalog_generation_titles(driver, live_app):
    """The sidebar catalog lists at least the expected generation prompt titles."""
    _go_to_prompts(driver, live_app)

    # Wait for the prompt list to load (the sidebar 'Generation' group heading appears).
    _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains("
                "translate(normalize-space(text()),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),"
                "'generation')]",
            )
        )
    )

    body = driver.find_element(By.TAG_NAME, "body").text
    for title in ("Resume objective", "Cover letter", "Skills gap analysis"):
        assert title in body, f"Expected prompt title '{title}' in catalog"


def test_prompts_select_cover_letter_shows_textarea_and_badge(driver, live_app):
    """Clicking 'Cover letter' shows a non-empty textarea and Default badge."""
    _go_to_prompts(driver, live_app)

    # Wait for prompts to load then click 'Cover letter'.
    cover_letter_btn = _wait(driver).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[.//span[normalize-space(text())='Cover letter']]")
        )
    )
    cover_letter_btn.click()

    # A textarea must appear and be non-empty.
    textarea = _wait(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "textarea"))
    )
    assert textarea.is_displayed()
    assert textarea.get_attribute("value") or textarea.text

    # The "Default" badge (or "Customized") must be visible next to the prompt title.
    badge = _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[normalize-space(text())='Default' "
                "or normalize-space(text())='Customized']",
            )
        )
    )
    assert badge.is_displayed()
