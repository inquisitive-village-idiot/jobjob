#!/usr/bin/env python3
"""Drive an assisted auto-fill session in a real browser.

Launches a headed, *persistent-context* Chromium (so a Workday login/session
survives between runs), navigates to the posting, picks the matching adapter, fills
what it can, prints the report, then hands the open window to the person to finish
account creation, custom widgets, screening questions, and the submit.

Playwright is an optional runtime extra (``jobjob[autofill]``); it is imported lazily
so the rest of jobjob works without a browser installed.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

from jobjob.autofill.adapters import select_adapter
from jobjob.autofill.data import ApplicationData
from jobjob.autofill.report import FillReport

NAME = "jobjob.autofill.runner"

_INSTALL_HINT = (
    "Playwright is required for auto-fill. Install it with:\n"
    "    pip install 'jobjob[autofill]'\n"
    "    playwright install chromium"
)


class PlaywrightUnavailableError(RuntimeError):
    """Raised when Playwright (the optional autofill extra) is not installed."""


class NoAdapterError(RuntimeError):
    """Raised when no adapter recognizes the target URL's ATS."""


def _browser_data_dir() -> Path:
    """Return the persistent Chromium profile directory (created on demand)."""
    path = Path(user_data_dir("jobjob", "jobjob")) / "autofill-chromium"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _prompt_to_close(report: FillReport) -> None:
    """Block until the human finishes in the browser and presses Enter."""
    input(
        "\nFinish and review the application in the browser, "
        "then press Enter here to close… "
    )


def run_autofill(
    url: str,
    data: ApplicationData,
    *,
    headless: bool = False,
    logger: Optional[logging.Logger] = None,
    wait_for_human: Callable[[FillReport], None] = _prompt_to_close,
) -> FillReport:
    """Open ``url``, fill it with the matching adapter, and pause for the human.

    Arguments:
        url: The job-posting / application URL.
        data: Structured applicant + experience payload to fill from.
        headless: Run without a visible window (testing/debug only; an assisted
            session is normally headed).
        logger: Optional logger for injection.
        wait_for_human: Callable invoked after filling to block until the person
            has finished; injectable so callers/tests can override the prompt.
    Returns:
        The adapter's FillReport.
    Raises:
        NoAdapterError: If no adapter recognizes ``url``.
        PlaywrightUnavailableError: If Playwright is not installed.
    """
    _logger = logger or logging.getLogger(NAME)

    adapter = select_adapter(url)
    if adapter is None:
        raise NoAdapterError(
            f"No auto-fill adapter recognizes this URL: {url}. "
            "Workday postings (*.myworkdayjobs.com) are currently supported."
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as err:  # noqa: F841 - re-raised with a hint
        raise PlaywrightUnavailableError(_INSTALL_HINT) from err

    _logger.info("Opening %s with the %s adapter", url, adapter.name)
    with sync_playwright() as play:
        context = play.chromium.launch_persistent_context(
            str(_browser_data_dir()),
            headless=headless,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url)
            report = adapter.fill(page, data)
            print(report.render())
            wait_for_human(report)
        finally:
            context.close()
    return report


# __END__
