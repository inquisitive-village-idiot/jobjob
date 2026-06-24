#!/usr/bin/env python3
"""`jobjob enrich` — import a LinkedIn profile screenshot into the contacts sheet."""

import argparse
import logging
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from jobjob.ailib.client.anthropic import AnthropicAdapter
from jobjob.ailib.session import AIClient
from jobjob.cli import build_credentials_loader, run_main
from jobjob.config import load_settings
from jobjob.enrich.workflow import enrich_inputs
from jobjob.gapi.sheets import DEFAULT_SHEET_NAME

NAME = "jobjob.enrich"


def parse_args(argv: Optional[Iterable] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="jobjob enrich",
        description="Import LinkedIn profile screenshots into the contacts sheet.",
    )
    parser.add_argument(
        "profile",
        type=Path,
        help=(
            "A profile screenshot, or a directory of mixed inputs. For a "
            "directory, only LinkedIn profiles are processed; other files are skipped."
        ),
    )
    parser.add_argument(
        "--sheet-id",
        default=None,
        help="Spreadsheet id (overrides ENRICHMENT_OUTPUT_SHEET_ID).",
    )
    parser.add_argument(
        "--sheet-name", default=DEFAULT_SHEET_NAME, help="Worksheet tab name."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Parse without writing to the sheet."
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable the response cache."
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable] = None, logger: logging.Logger | None = None) -> int:
    """Entry point for the enrich sub-command."""
    _logger = logger or logging.getLogger(NAME)
    args = parse_args(argv)
    settings = load_settings()

    client = AIClient(
        AnthropicAdapter(
            model=settings.model,
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
        )
    )
    summary = enrich_inputs(
        args.profile,
        query_service=client,
        spreadsheet_id=args.sheet_id or settings.enrichment_output_sheet_id,
        sheet_name=args.sheet_name,
        use_cache=settings.cache_enabled and not args.no_cache,
        dry_run=args.dry_run,
        data_dir=settings.enrichment_input_dir,
        logger=_logger,
        _credentials_loader=build_credentials_loader(settings),
    )
    _logger.info(
        "Enrich complete: %d processed, %d skipped, %d failed",
        summary["processed"],
        summary["skipped"],
        summary["failed"],
    )
    # Non-zero exit if everything that was eligible failed.
    return 1 if summary["failed"] and not summary["processed"] else 0


if __name__ == "__main__":
    sys.exit(run_main(main))


# __END__
