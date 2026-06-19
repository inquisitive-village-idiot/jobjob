#!/usr/bin/env python3
"""`jobjob auth` — authorize Google access and write the token file.

Run after first-time setup, or after the OAuth scopes change (which requires a
fresh consent). ``--force`` ignores any existing token and re-runs the consent
flow. The resulting credentials are always written back to the token file, so a
plain refresh is persisted too.
"""

import argparse
import logging
import sys
from collections.abc import Iterable
from typing import Optional

from jobjob.cli import run_main
from jobjob.config import load_settings
from jobjob.loader.auth import (
    ENV_GOOGLE_TOKEN_FILE,
    GOOGLE_API_SCOPES,
    get_google_credentials,
    save_pickled_token,
)

NAME = "jobjob.auth"


def parse_args(argv: Optional[Iterable] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="jobjob auth",
        description="Authorize Google access and write the token file.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Ignore any existing token and run the consent flow. Use after the "
            "OAuth scopes change, since the cached token is unaware of new scopes."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable] = None, logger: logging.Logger | None = None) -> int:
    """Authorize Google and persist the token.

    Arguments:
        argv: Argument vector (defaults to sys.argv).
        logger: Optional logger for injection.
    Returns:
        0 on success; 2 if no token path is configured.
    """
    _logger = logger or logging.getLogger(NAME)
    args = parse_args(argv)
    settings = load_settings()

    token_file = settings.google.token_file
    if token_file is None:
        _logger.error("No token path configured (set %s).", ENV_GOOGLE_TOKEN_FILE)
        return 2

    creds = get_google_credentials(
        credentials_file=settings.google.credentials_file,
        token_file=token_file,
        force_reauth=args.force,
    )
    # Persist explicitly so a refresh (which get_google_credentials does not
    # write back) is saved, not just the full-flow path.
    save_pickled_token(creds, token_file)
    _logger.info("Authorized Google access; token written to %s", token_file)
    _logger.info("Granted scopes: %s", ", ".join(GOOGLE_API_SCOPES))
    return 0


if __name__ == "__main__":
    sys.exit(run_main(main))


# __END__
