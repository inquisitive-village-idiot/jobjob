#!/usr/bin/env python3
"""End-to-end tests for the setup wizard's Profile step (Batch B #2).

The first-run wizard is pre-dismissed by the harness, so these reopen it from the
account menu and drive to the new Profile step (register an existing profile folder /
bootstrap from a résumé).
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _open_wizard(driver, live_app):
    driver.get(live_app + "/")
    # Open the account menu, then "Run setup".
    _wait(driver).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "header button[title='Profile and settings']")
        )
    ).click()
    _wait(driver).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Run setup']")
        )
    ).click()
    _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h2[normalize-space()='Welcome to jobjob']")
        )
    )


def _next(driver):
    _wait(driver).until(
        EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Next']"))
    ).click()


def test_wizard_profile_step_has_register_and_import(driver, live_app):
    """The wizard's Profile step offers both register-existing and résumé bootstrap."""
    _open_wizard(driver, live_app)
    # Steps: Anthropic key -> Google -> Profile -> Your details. Advance twice.
    _next(driver)
    _next(driver)
    body = _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h3[normalize-space()='Use an existing profile folder']")
        )
    )
    assert body.is_displayed()
    assert driver.find_element(
        By.XPATH, "//h3[normalize-space()='Bootstrap from a résumé']"
    ).is_displayed()
