#!/usr/bin/env python3
"""End-to-end tests for the Dashboard page.

Covers: Applications/Profiles tab toggle changes the visible section heading;
"Refresh" button is present.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _nav_link(driver, label):
    """Return the top-nav anchor with the given visible text."""
    return driver.find_element(By.XPATH, f"//nav//a[normalize-space(text())='{label}']")


def test_dashboard_applications_tab_heading(driver, live_app):
    """Applications tab (default) shows the 'Completed Applications' heading."""
    driver.get(live_app + "/")
    # Wait for h1 Dashboard to confirm the page is loaded.
    _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h1[normalize-space()='Dashboard']")
        )
    )

    # The default tab is Applications; the h2 heading is uppercased via CSS so we
    # match case-insensitively with translate().
    heading = _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//h2[contains("
                "translate(normalize-space(text()),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),"
                "'completed applications')]",
            )
        )
    )
    assert heading.is_displayed()


def test_dashboard_profiles_tab_heading(driver, live_app):
    """Clicking the Profiles tab shows the 'Completed Profiles' section heading."""
    driver.get(live_app + "/")
    _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h1[normalize-space()='Dashboard']")
        )
    )

    # Click the Profiles tab button (its text is exactly 'Profiles').
    profiles_tab = _wait(driver).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space(text())='Profiles']")
        )
    )
    profiles_tab.click()

    # After switching, the h2 for profiles section should appear.
    heading = _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//h2[contains("
                "translate(normalize-space(text()),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),"
                "'completed profiles')]",
            )
        )
    )
    assert heading.is_displayed()


def test_dashboard_refresh_button_present(driver, live_app):
    """The Dashboard page has a visible 'Refresh' button."""
    driver.get(live_app + "/")
    _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h1[normalize-space()='Dashboard']")
        )
    )

    refresh = _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//button[normalize-space(text())='Refresh']")
        )
    )
    assert refresh.is_displayed()
