#!/usr/bin/env python3
"""`jobjob apply` — assisted Playwright auto-fill of a job application.

Opens the posting in a real browser, fills the fields it can map from the active
profile (contact basics + work history), and hands the open window back to you to
finish account creation, custom widgets, screening questions, and the submit.
"""

import argparse
import logging
from collections.abc import Iterable
from typing import Optional

from jobjob.autofill.data import ApplicationData
from jobjob.autofill.runner import (
    NoAdapterError,
    PlaywrightUnavailableError,
    run_autofill,
)
from jobjob.cli import run_main
from jobjob.config import load_settings
from jobjob.loader.loadcontent import load_experience

NAME = "jobjob.autofill"


def parse_args(argv: Optional[Iterable] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="jobjob apply",
        description=(
            "Assisted auto-fill of a job application in a real browser. "
            "Fills what it can confidently map, flags the rest, and never submits."
        ),
    )
    parser.add_argument(
        "url",
        help="The job-posting / application URL (Workday postings supported).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a visible window (testing/debug only).",
    )
    parser.add_argument(
        "--assisted-detached",
        action="store_true",
        help=(
            "Force the non-TTY 'wait for window close' mode instead of the "
            "input()-based prompt, regardless of stdin. Used by the webapp when "
            "it launches this as a detached background process; auto-selected "
            "anyway when stdin is not a TTY."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable] = None, logger: logging.Logger | None = None) -> int:
    """Entry point. Builds Settings once and injects concrete values downstream.

    Arguments:
        argv: Argument vector (defaults to sys.argv).
        logger: Optional logger for injection.
    Returns:
        0 on success, non-zero on error.
    """
    _logger = logger or logging.getLogger(NAME)
    args = parse_args(argv)
    settings = load_settings()

    data = ApplicationData(
        applicant=settings.applicant,
        experience=load_experience(),
    )

    try:
        run_autofill(
            args.url,
            data,
            headless=args.headless,
            logger=_logger,
            # None ⇒ auto-detect from stdin (see run_autofill); the flag forces
            # the non-TTY window-close wait even if stdin happens to be a TTY.
            assisted_detached=True if args.assisted_detached else None,
        )
    except NoAdapterError as err:
        _logger.error("%s", err)
        return 2
    except PlaywrightUnavailableError as err:
        _logger.error("%s", err)
        return 1
    return 0


def console_main() -> int:
    """Console-script entry point: run ``main`` with logging + error handling."""
    return run_main(main)


if __name__ == "__main__":
    import sys

    sys.exit(run_main(main))


# __END__
