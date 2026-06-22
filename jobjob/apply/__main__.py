#!/usr/bin/env python3
"""`jobjob apply` — generate a tailored resume + cover letter for a job description."""

import argparse
import json
import logging
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from jobjob.ailib.client.anthropic import AnthropicAdapter
from jobjob.ailib.query import clear_cache
from jobjob.ailib.session import AIClient
from jobjob.apply.workflow import apply_inputs, run_application_workflow
from jobjob.cli import build_credentials_loader, run_main
from jobjob.config import load_settings

NAME = "jobjob.apply"


def parse_args(argv: Optional[Iterable] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="jobjob apply",
        description="Generate a tailored resume and cover letter for a job description.",
    )
    parser.add_argument(
        "job_description",
        type=Path,
        help=(
            "A job-description PDF, or a directory of mixed inputs. For a "
            "directory, only JDs are processed; other files are skipped."
        ),
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None, help="Output directory."
    )
    parser.add_argument(
        "--skip-drive",
        action="store_true",
        help="Skip all Google Drive/Docs operations (local artifacts only).",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Resume template name to use. If omitted, the archetype is auto-detected.",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable the response cache."
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Purge the response cache before running.",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help=(
            "Re-process a previously generated application: point at the JD copy "
            "inside its output directory; the files in that directory (and the "
            "original Drive folder) are regenerated/updated in place."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _read_folder_id(output_dir: Path) -> Optional[str]:
    """Return the Drive folder id recorded in ``output_dir/summary.json``, if any."""
    summary = Path(output_dir, "summary.json")
    if not summary.is_file():
        return None
    try:
        return json.loads(summary.read_text(encoding="utf-8")).get("folder_id")
    except (ValueError, OSError):
        return None


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

    if args.clear_cache:
        clear_cache()

    client = AIClient(
        AnthropicAdapter(model=settings.model, api_key=settings.anthropic_api_key)
    )

    # Re-process mode: single file — update the files in the JD's own directory
    # and reuse the original Drive folder recorded in its summary.json.
    if args.reprocess:
        output_dir = args.job_description.parent
        reuse_folder_id = _read_folder_id(output_dir)
        _logger.info("Re-processing in place: %s", output_dir)
        run_application_workflow(
            job_description_pdf=args.job_description,
            query_service=client,
            applicant=settings.applicant,
            output_dir=output_dir,
            skip_drive=args.skip_drive,
            use_cache=settings.cache_enabled and not args.no_cache,
            template_id=settings.google.template_id,
            template_name=args.template,
            parent_id=settings.google.applications_folder_id,
            reuse_folder_id=reuse_folder_id,
            industry=settings.industry,
            logger=_logger,
            _credentials_loader=build_credentials_loader(settings),
        )
        return 0

    # Normal mode: a file is processed directly; a directory processes only its
    # JDs and skips the rest (continue-on-error).
    summary = apply_inputs(
        args.job_description,
        query_service=client,
        applicant=settings.applicant,
        output_dir=args.output,
        skip_drive=args.skip_drive,
        use_cache=settings.cache_enabled and not args.no_cache,
        template_id=settings.google.template_id,
        template_name=args.template,
        parent_id=settings.google.applications_folder_id,
        data_dir=settings.data_dir,
        industry=settings.industry,
        logger=_logger,
        _credentials_loader=build_credentials_loader(settings),
    )
    _logger.info(
        "Apply complete: %d processed, %d skipped, %d failed",
        summary["processed"], summary["skipped"], summary["failed"],
    )
    return 1 if summary["failed"] and not summary["processed"] else 0


if __name__ == "__main__":
    sys.exit(run_main(main))


# __END__
