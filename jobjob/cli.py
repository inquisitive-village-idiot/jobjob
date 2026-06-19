#!/usr/bin/env python3
"""Shared CLI helpers for the jobjob sub-command entrypoints."""

import logging
from collections.abc import Callable, Iterable
from typing import Any, Optional

from jobjob.config import Settings
from jobjob.loader.auth import get_google_credentials

NAME = "jobjob"


def build_credentials_loader(settings: Settings) -> Callable[[], Any]:
    """Return a zero-arg Google credentials loader bound to the configured paths."""

    def _loader() -> Any:
        return get_google_credentials(
            credentials_file=settings.google.credentials_file,
            token_file=settings.google.token_file,
        )

    return _loader


def configure_logging() -> None:
    """Configure root logging for CLI runs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def run_main(main: Callable[..., int], argv: Optional[Iterable] = None) -> int:
    """Run a CLI ``main``, configuring logging and handling top-level errors.

    Arguments:
        main: A ``main(argv) -> int`` entrypoint.
        argv: Argument vector (defaults to ``sys.argv``).
    Returns:
        The process exit code.
    """
    configure_logging()
    logger = logging.getLogger(NAME)
    try:
        return main(argv)
    except (KeyboardInterrupt, GeneratorExit):
        logger.warning("Interrupted")
        return 1
    except Exception as err:
        logger.exception("Unexpected error: %s", err)
        return 1


# __END__
