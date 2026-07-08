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
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from platformdirs import user_data_dir

from jobjob.autofill.adapters import select_adapter
from jobjob.autofill.data import ApplicationData
from jobjob.autofill.report import FillReport

NAME = "jobjob.autofill.runner"

# Machine marker printed to stdout on the detached (non-TTY) path, right after
# the fill report, to signal "the fill pass is done" to a parent process capturing
# stdout — decoupling job-completion detection from the report's human-readable
# wording. Never printed on the interactive TTY path.
FILL_COMPLETE_SENTINEL = "__JOBJOB_AUTOFILL_FILL_COMPLETE__"

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


def wait_for_window_close(
    context, *, poll_interval: float = 0.5
) -> Callable[[FillReport], None]:
    """Build a ``wait_for_human`` that blocks until the human closes the window.

    Non-TTY analog of :func:`_prompt_to_close`: there is no console to prompt on
    (e.g. this runner was launched as a detached subprocess by the webapp), so
    instead of blocking on ``input()`` it polls the persistent context's open
    pages and returns once none remain — the human closing the browser window is
    what signals "done" instead of pressing Enter.

    Arguments:
        context: The Playwright persistent browser context to watch.
        poll_interval: Seconds between polls of ``context.pages``.
    Returns:
        A callable matching the ``wait_for_human`` signature (``FillReport`` ->
        ``None``); the report argument is unused (the signal is the window, not
        the report).
    """

    def _wait(report: FillReport) -> None:  # noqa: ARG001 - signature parity
        while True:
            try:
                if not context.pages:
                    return
            except Exception:
                # The context is already torn down — nothing left to wait on.
                return
            time.sleep(poll_interval)

    return _wait


def run_autofill(
    url: str,
    data: ApplicationData,
    *,
    headless: bool = False,
    logger: Optional[logging.Logger] = None,
    wait_for_human: Optional[Callable[[FillReport], None]] = None,
    assisted_detached: Optional[bool] = None,
) -> FillReport:
    """Open ``url``, fill it with the matching adapter, and pause for the human.

    Arguments:
        url: The job-posting / application URL.
        data: Structured applicant + experience payload to fill from.
        headless: Run without a visible window (testing/debug only; an assisted
            session is normally headed).
        logger: Optional logger for injection.
        wait_for_human: Callable invoked after filling to block until the person
            has finished; injectable so callers/tests can override the wait
            strategy entirely. When ``None`` (the default), the strategy is
            selected automatically: :func:`_prompt_to_close` (``input()``) on a
            TTY, else :func:`wait_for_window_close` bound to the freshly opened
            context — see ``assisted_detached``.
        assisted_detached: Forces the non-TTY "wait for window close" mode when
            ``True``, or the TTY prompt when ``False``, regardless of
            ``sys.stdin.isatty()``. ``None`` (the default) auto-detects from the
            actual stdin. Ignored when ``wait_for_human`` is given explicitly.
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
            # Flush explicitly: stdout to a pipe (the webapp's detached subprocess
            # launch) is block-buffered by default, and nothing else touches stdout
            # before wait_for_human in the non-TTY path (no input() to force a
            # flush) — the caller capturing this report depends on it landing
            # promptly. See design.md ("the job is marked complete once the fill
            # report is captured").
            print(report.render())
            sys.stdout.flush()
            wait = wait_for_human
            detached = wait is None and (
                assisted_detached
                if assisted_detached is not None
                else not sys.stdin.isatty()
            )
            if wait is None:
                wait = wait_for_window_close(context) if detached else _prompt_to_close
            if detached:
                # Machine marker for a parent capturing stdout (the webapp's
                # detached launch): "fill done" independent of the report wording.
                # TTY runs skip it — a human reading the terminal doesn't want it.
                print(FILL_COMPLETE_SENTINEL, flush=True)
            wait(report)
        finally:
            try:
                context.close()
            except Exception:
                # Idempotent: the human closing the last window may already have
                # torn the context down (wait_for_window_close returns right
                # after that happens).
                _logger.debug("context.close() raised (already closed?)", exc_info=True)
    return report


# __END__
