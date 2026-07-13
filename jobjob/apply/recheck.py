#!/usr/bin/env python3
"""`jobjob ats` — re-assess a processed application's resume, standalone.

Rebuilds the ATS assessment from the artifacts the apply workflow already
saved (``summary.json``, ``skills_analysis.json``) plus one Google Docs read
of the current resume — so the edit-resume/re-check iteration loop costs zero
Anthropic calls. Drive-skipped applications report a skipped assessment.
"""

import argparse
import dataclasses as dcs
import json
import logging
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Optional

from jobjob.apply.generate.ats import AtsAssessment, assess_ats
from jobjob.cli import build_credentials_loader, run_main
from jobjob.config import load_settings
from jobjob.gapi.docs import get_document
from jobjob.gapi.service import build_docs_service
from jobjob.loader.auth import get_google_credentials
from jobjob.loader.loadcontent import load_skills
from jobjob.structure.build import from_mapping
from jobjob.structure.job_decription import JobDescription

NAME = "jobjob.apply.recheck"

SUMMARY_NAME = "summary.json"
SKILLS_NAME = "skills_analysis.json"


# Artifact loading
# ======================================================================


def load_saved_application(output_dir: Path) -> tuple[JobDescription, dict, str]:
    """Load the saved apply artifacts needed for a reassessment.

    Arguments:
        output_dir: A processed application's output directory.
    Returns:
        ``(job, skills, resume_id)``; ``resume_id`` is "" when Drive was
        skipped for the original run.
    Raises:
        FileNotFoundError naming the missing artifact.
        ValueError if ``summary.json`` lacks ``job_info``.
    """
    output_dir = Path(output_dir).expanduser().resolve()
    summary_path = Path(output_dir, SUMMARY_NAME)
    skills_path = Path(output_dir, SKILLS_NAME)
    for path in (summary_path, skills_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing application artifact: {path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    job_info = summary.get("job_info")
    if not isinstance(job_info, dict):
        raise ValueError(f"No job_info in {summary_path}")

    job = from_mapping(JobDescription, job_info)
    skills = json.loads(skills_path.read_text(encoding="utf-8"))
    return job, skills, str(summary.get("resume_id") or "")


# Reassessment
# ======================================================================


def reassess_application(
    output_dir: Path,
    *,
    docs_service: Any = None,
    credentials_loader: Optional[Callable[[], Any]] = None,
    logger: logging.Logger | None = None,
) -> AtsAssessment:
    """Re-run the ATS assessment for a processed application.

    Zero Anthropic calls: every input comes from the saved artifacts; the only
    I/O beyond the output directory is one Docs read of the current resume.

    Arguments:
        output_dir: A processed application's output directory.
        docs_service: Injected Google Docs service (testing); built lazily
            from ``credentials_loader`` when omitted.
        credentials_loader: Zero-arg Google credentials loader; defaults to
            the standard credential paths.
        logger: Optional logger for injection.
    Returns:
        The AtsAssessment (skipped when the original run skipped Drive).
    """
    job, skills, resume_id = load_saved_application(output_dir)
    if not resume_id:
        # Drive-skipped application: nothing was rendered, nothing to fetch.
        return AtsAssessment(skipped=True)

    if docs_service is None:
        loader = credentials_loader or get_google_credentials
        docs_service = build_docs_service(loader())
    document = get_document(docs_service, resume_id)

    try:
        skill_set = load_skills(logger=logger)
    except (OSError, ValueError) as exc:
        _logger = logger or logging.getLogger(__name__)
        _logger.warning("Skills file unavailable for ATS re-check: %s", exc)
        skill_set = None
    return assess_ats(document, job, skills, skill_set=skill_set, logger=logger)


# Report rendering
# ======================================================================


def _section(title: str, items: Iterable[str]) -> list[str]:
    items = list(items)
    if not items:
        return []
    return [f"{title}:", *(f"  - {item}" for item in items), ""]


def render_ats_report(assessment: AtsAssessment) -> str:
    """Render the assessment as a plain-text report."""
    if assessment.skipped:
        return (
            "ATS assessment skipped — no resume document was generated for "
            "this application (Drive skipped)."
        )

    score = assessment.coverage_score
    lines = [
        f"Keyword coverage: {'—' if score is None else f'{score:.2f}'}",
        "",
        *_section("Present in resume", assessment.present),
        *_section("Missing (evidenced)", assessment.missing_evidenced),
        *_section("Missing (unevidenced)", assessment.missing_unevidenced),
        *_section("Unmapped requirements", assessment.unmapped),
        *_section("Recommendations", assessment.recommendations),
        *_section(
            "Skills-file candidates (evidenced, not in your skills file)",
            assessment.skills_file_candidates,
        ),
        *_section(
            "Up-skill targets (not for the resume or cover letter)",
            assessment.upskill_targets,
        ),
        *_section("Fit vs. ATS gaps (supported but not rendered)", assessment.fit_gaps),
    ]
    warnings = [f"{c.name}: {c.reason}" for c in assessment.checks if not c.passed]
    lines.extend(
        _section("Parseability warnings", warnings)
        if warnings
        else ["Parseability: all checks passed.", ""]
    )
    return "\n".join(lines).rstrip() + "\n"


# CLI
# ======================================================================


def parse_args(argv: Optional[Iterable] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="jobjob ats",
        description=(
            "Re-assess a processed application's resume against its JD "
            "(keyword coverage + parseability) from saved artifacts. "
            "No AI calls; one Google Docs read."
        ),
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="A processed application's output directory (contains summary.json).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable] = None) -> int:
    """CLI entrypoint for ``jobjob ats``."""

    def _run(args_iterable: Optional[Iterable]) -> int:
        args = parse_args(args_iterable)
        settings = load_settings()
        assessment = reassess_application(
            args.output_dir,
            credentials_loader=build_credentials_loader(settings),
        )
        print(render_ats_report(assessment))
        return 0

    return run_main(_run, argv)


# Serialization (webapp)
# ======================================================================


def assessment_as_dict(assessment: AtsAssessment) -> dict:
    """JSON-ready dict of the assessment.

    NOTE: ``dcs.asdict`` is correct HERE (unlike the internal freeze path):
        the endpoint wants nested dataclasses (AtsCheck) flattened to dicts.
    """
    return dcs.asdict(assessment)


# __END__
