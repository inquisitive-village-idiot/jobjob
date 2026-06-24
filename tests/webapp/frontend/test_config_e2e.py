#!/usr/bin/env python3
"""End-to-end tests for the Configuration page.

Covers the restructured Settings page: a left nav of App / Profiles / About, with
profiles shown as tabs in the main body (active first) plus a "＋" tab to add one,
the whole-profile Edit toggle co-located with the fields, the read-only guard on the
bundled ``example`` profile, and the Update panel living under About.
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


def _nav_button(driver, label):
    """Return a left-nav section button (App / Profiles / About)."""
    return driver.find_element(
        By.XPATH,
        "//nav[@aria-label='Configuration sections']"
        f"//button[normalize-space(text())='{label}']",
    )


def _sidebar(driver):
    return driver.find_element(
        By.CSS_SELECTOR, "nav[aria-label='Configuration sections']"
    )


def _open_profiles(driver):
    """Switch to the Profiles section and wait for the profile tab list."""
    _nav_button(driver, "Profiles").click()
    return _wait(driver).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div[role='tablist'][aria-label='Profiles']")
        )
    )


def _profile_tab(driver, label):
    """Return the body profile tab whose visible text equals ``label``."""
    return driver.find_element(
        By.XPATH,
        "//div[@role='tablist'][@aria-label='Profiles']"
        f"//button[normalize-space(text())='{label}']",
    )


def test_config_nav_has_three_sections(driver, live_app):
    """The left nav exposes App, Profiles, and About."""
    _open_config(driver, live_app)
    for label in ("App", "Profiles", "About"):
        assert _nav_button(driver, label).is_displayed()


def test_profiles_section_shows_tabs_and_add(driver, live_app):
    """Profiles render as body tabs (incl. the example) plus an add (＋) tab."""
    _open_config(driver, live_app)
    _open_profiles(driver)
    assert _profile_tab(driver, "example").is_displayed()
    add = driver.find_element(
        By.XPATH,
        "//div[@role='tablist'][@aria-label='Profiles']"
        "//button[@aria-label='Add a profile']",
    )
    assert add.is_displayed()


def test_example_profile_is_read_only(driver, live_app):
    """Selecting the read-only example profile disables editing."""
    _open_config(driver, live_app)
    _open_profiles(driver)
    _profile_tab(driver, "example").click()

    # The whole-profile Edit toggle is present (beside the fields) but disabled.
    edit = _wait(driver).until(
        lambda d: d.find_element(By.XPATH, "//button[normalize-space()='Edit']")
    )
    _wait(driver).until(lambda d: edit.get_attribute("disabled") is not None)
    assert "read-only" in driver.find_element(By.TAG_NAME, "body").text


def test_app_sidebar_expands_subsections(driver, live_app):
    """The App section expands into its config-schema subsections in the sidebar."""
    _open_config(driver, live_app)
    # App is the default section; its schema groups (e.g. Google) show as anchors.
    anchor = _wait(driver).until(
        lambda d: _sidebar(d).find_element(
            By.XPATH, ".//button[normalize-space()='Google']"
        )
    )
    assert anchor.is_displayed()
    anchor.click()
    assert "Google" in _sidebar(driver).text


def test_profile_tab_shows_location_and_dir_pills(driver, live_app):
    """Selecting a profile shows its location and resource-dir file-count pills."""
    _open_config(driver, live_app)
    _open_profiles(driver)
    _profile_tab(driver, "example").click()
    panel = _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h3[normalize-space()='Location & directories']")
        )
    )
    assert panel.is_displayed()
    # The "Directories" config group renders below once the profile schema loads.
    _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[normalize-space(text())='Directories']")
        )
    )
    # The example profile ships content/ and reference/ dirs, shown as pills.
    body = driver.find_element(By.TAG_NAME, "body").text
    assert "content" in body and "reference" in body
    assert "Directories" in body


def test_add_profile_tab_opens_form(driver, live_app):
    """The ＋ tab opens the create / duplicate / register add-profile form."""
    _open_config(driver, live_app)
    _open_profiles(driver)
    driver.find_element(
        By.XPATH,
        "//div[@role='tablist'][@aria-label='Profiles']"
        "//button[@aria-label='Add a profile']",
    ).click()
    # The register action and the name field are part of the add form.
    register = _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//button[normalize-space()='Register folder']")
        )
    )
    assert register.is_displayed()
    assert "New profile name" in driver.find_element(By.TAG_NAME, "body").text


def test_about_section_shows_updates_and_issue_link(driver, live_app):
    """The About section hosts the Update panel and a Report-an-issue link."""
    _open_config(driver, live_app)
    _nav_button(driver, "About").click()
    _wait(driver).until(
        EC.presence_of_element_located((By.XPATH, "//h2[normalize-space()='Updates']"))
    )
    issue = driver.find_element(By.XPATH, "//a[normalize-space()='Report an issue']")
    assert issue.get_attribute("href").startswith("https://github.com/")
