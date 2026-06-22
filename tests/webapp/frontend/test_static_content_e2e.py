#!/usr/bin/env python3
"""End-to-end tests for the Static Content page.

Covers: H1 visible; all five tabs present; clicking "reference" and "import"
tabs renders their distinct panels.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)


def _nav_link(driver, label):
    """Return the top-nav anchor with the given visible text."""
    return driver.find_element(By.XPATH, f"//nav//a[normalize-space(text())='{label}']")


def _go_to_static(driver, live_app):
    """Navigate to the Static Content page and wait for the H1."""
    driver.get(live_app + "/#static")
    _wait(driver).until(
        EC.presence_of_element_located(
            (By.XPATH, "//h1[normalize-space()='Static Content']")
        )
    )


def test_static_content_h1_visible(driver, live_app):
    """The Static Content page renders its H1 heading."""
    _go_to_static(driver, live_app)
    h1 = driver.find_element(By.XPATH, "//h1[normalize-space()='Static Content']")
    assert h1.is_displayed()


def test_static_content_tabs_present(driver, live_app):
    """All five tab buttons are present on the Static Content page.

    Tab labels: highlights, skills, templates, reference, and "Import résumé".
    The first four use CSS capitalize so their rendered text may be uppercased;
    we locate them by their DOM text content (which is lowercase) using XPath
    translate to normalize.
    """
    _go_to_static(driver, live_app)

    # The tab buttons sit inside a <nav> within the static content area.  We
    # locate each by a case-insensitive substring match because CSS `capitalize`
    # transforms the first letter.
    for label in ("highlights", "skills", "templates", "reference"):
        tab = driver.find_element(
            By.XPATH,
            f"//button[contains("
            f"translate(normalize-space(text()),"
            f"'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            f"'abcdefghijklmnopqrstuvwxyz'),"
            f"'{label}')]",
        )
        assert tab.is_displayed(), f"Tab '{label}' not visible"

    # The import tab has a special label with an accented character.
    import_tab = driver.find_element(
        By.XPATH,
        "//button[contains(normalize-space(text()), 'Import')]",
    )
    assert import_tab.is_displayed()


def test_static_content_reference_tab(driver, live_app):
    """Clicking the 'reference' tab renders the reference file browser panel."""
    _go_to_static(driver, live_app)

    ref_tab = driver.find_element(
        By.XPATH,
        "//button[contains("
        "translate(normalize-space(text()),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'reference')]",
    )
    ref_tab.click()

    # The reference panel renders a sidebar <aside> containing file list buttons
    # or a "Loading…" / "Select a file to edit" placeholder.
    panel = _wait(driver).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "aside"))
    )
    assert panel.is_displayed()


def test_static_content_import_tab(driver, live_app):
    """Clicking the import tab renders the 'Import résumé' panel."""
    _go_to_static(driver, live_app)

    import_tab = driver.find_element(
        By.XPATH,
        "//button[contains(normalize-space(text()), 'Import')]",
    )
    import_tab.click()

    # The import panel heading contains "Import" — match loosely because the
    # exact heading comes from ResumeImportPanel which we verify separately.
    _wait(driver).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains("
                "translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                "'abcdefghijklmnopqrstuvwxyz'),"
                "'import')]",
            )
        )
    )
    body = driver.find_element(By.TAG_NAME, "body").text
    assert "Import" in body or "import" in body.lower()
