#!/usr/bin/env python3
"""Reference end-to-end tests: the app boots and top-level navigation works.

These establish the harness pattern (``live_app`` + ``driver`` fixtures from conftest)
that the rest of the frontend e2e suite follows: drive the real UI, then assert on
rendered text/elements with explicit waits.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _nav_link(driver, label):
    """Return the top-nav anchor with the given visible text."""
    return driver.find_element(By.XPATH, f"//nav//a[normalize-space(text())='{label}']")


def test_dashboard_loads(driver, live_app):
    """The SPA mounts and the Dashboard renders its heading."""
    driver.get(live_app + "/")
    heading = _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h1[normalize-space()='Dashboard']")
        )
    )
    assert heading.is_displayed()


def test_nav_shows_core_links(driver, live_app):
    """The primary nav exposes the expected destinations."""
    driver.get(live_app + "/")
    _wait(driver).until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav")))
    for label in ("Dashboard", "Queue", "Static Content", "Prompts"):
        assert _nav_link(driver, label).is_displayed()


def test_navigate_to_prompts_page(driver, live_app):
    """Clicking the Prompts nav link loads the prompt editor with its catalog."""
    driver.get(live_app + "/")
    _wait(driver).until(EC.presence_of_element_located((By.CSS_SELECTOR, "nav")))
    _nav_link(driver, "Prompts").click()

    _wait(driver).until(
        EC.presence_of_element_located((By.XPATH, "//h1[normalize-space()='Prompts']"))
    )
    # The catalog lists the generation prompts; "Cover letter" is one of them.
    body = driver.find_element(By.TAG_NAME, "body").text
    assert "Cover letter" in body
