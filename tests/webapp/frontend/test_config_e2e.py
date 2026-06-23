#!/usr/bin/env python3
"""End-to-end tests for the Configuration page profile tabs (Batch A #6).

Covers the per-profile tab switcher: App plus one tab per profile, and the
read-only guard on the bundled ``example`` profile (its fields stay disabled and
the Edit toggle is unavailable).
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _open_config(driver, live_app):
    driver.get(live_app + "/#config")
    _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h1[normalize-space()='Configuration']")
        )
    )


def _config_tab(driver, label):
    """Return the config tab button whose visible text equals ``label``."""
    return driver.find_element(
        By.XPATH, f"//nav//button[normalize-space(text())='{label}']"
    )


def test_config_has_app_and_example_tabs(driver, live_app):
    """The config page exposes an App tab and a tab for the bundled example profile."""
    _open_config(driver, live_app)
    assert _config_tab(driver, "App").is_displayed()
    assert _config_tab(driver, "example").is_displayed()


def test_example_profile_is_read_only(driver, live_app):
    """Selecting the read-only example profile disables editing."""
    _open_config(driver, live_app)
    _config_tab(driver, "example").click()

    # The read-only hint appears and the whole-profile Edit toggle is disabled.
    edit = _wait(driver).until(
        EC.presence_of_element_located((By.XPATH, "//button[normalize-space()='Edit']"))
    )
    assert edit.get_attribute("disabled") is not None
    assert "read-only" in driver.find_element(By.TAG_NAME, "body").text


def _sidebar(driver):
    return driver.find_element(
        By.CSS_SELECTOR, "nav[aria-label='Configuration sections']"
    )


def test_config_sidebar_expands_active_tab_subsections(driver, live_app):
    """The left sidebar expands the active tab into its config-schema subsections."""
    _open_config(driver, live_app)
    sidebar = _sidebar(driver)
    # App is active by default; its schema groups (e.g. Google) show as anchors.
    anchor = _wait(driver).until(
        lambda d: _sidebar(d).find_element(
            By.XPATH, ".//button[normalize-space()='Google']"
        )
    )
    assert anchor.is_displayed()
    # Clicking a subsection anchor scrolls to that section's content.
    anchor.click()
    assert "Google" in sidebar.text
