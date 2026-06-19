#!/usr/bin/env python3
"""Orchestrate the end-to-end application workflow.

Sequential model calls share one cached context prefix (highlights, STARs,
background, cover-letter examples, writing style, and — in Drive mode — the
customized resume). The offline path (``skip_drive=True``) produces local
artifacts and is fully exercised by tests; the Drive path adds Google I/O.

Drive folder per application (``YYYY-MM-DD - Company - Role``) contains exactly:
the README (Google Doc), the JD (``JD_<Company>_<Role>.pdf``), the resume (the
customized Google Doc), and the cover letter (Google Doc).
"""

import dataclasses as dcs
import json
import logging
import shutil
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Optional

from jobjob.ailib.session import AIClient
from jobjob.classify.classify import JD, classify_file
from jobjob.gapi import drive as gdrive
from jobjob.gapi.docs import verify_page_count
from jobjob.gapi.service import build_docs_service, build_drive_service
from jobjob.apply.generate.archetype import select_template
from jobjob.apply.generate.coverletter import generate_cover_letter_text
from jobjob.apply.generate.highlights import select_highlights
from jobjob.apply.generate.parse import parse_job_description
from jobjob.apply.generate.readme import generate_application_readme
from jobjob.apply.generate.resume import tailor_resume
from jobjob.apply.generate.skills import analyze_skills
from jobjob.loader.auth import get_google_credentials
from jobjob.loader.loadcontent import load_highlights, load_templates
from jobjob.loader.loadreference import load_reference_documents
from jobjob.apply.output.cover_letter_docx import create_cover_letter_docx
from jobjob.apply.output.cover_letter_pdf import create_cover_letter_pdf
from jobjob.structure.applicant import Applicant
from jobjob.structure.highlight import Highlight, HighlightSet
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.reference import ReferenceDocs
from jobjob.structure.template import ResumeTemplate

RESUME_NAME = "Resume"
COVER_LETTER_NAME = "CoverLetter"
README_NAME = "README"
SKILLS_NAME = "skills_analysis.json"


def build_cached_context(
    highlight_set: HighlightSet,
    reference: ReferenceDocs,
    resume_text: Optional[str] = None,
) -> str:
    """Assemble the stable, cached system context shared across all calls.

    NOTE: order matters for prompt caching — stable content first; the resume
        (added in Drive mode) goes last as it is the most volatile prefix piece.

    Arguments:
        highlight_set: All available highlights.
        reference: Loaded reference documents.
        resume_text: Customized resume text, if available.
    Returns:
        The cached-context string.
    """
    parts = []
    highlights_text = "\n".join(
        f"- {h.context}: {h.text}" for h in highlight_set.highlights
    )
    parts.append(f"=== AVAILABLE RESUME HIGHLIGHTS ===\n{highlights_text}")
    if reference.background:
        parts.append(f"=== BACKGROUND INFORMATION ===\n{reference.background}")
    if reference.star_examples:
        parts.append(
            f"=== DETAILED EXPERIENCE (STAR FORMAT) ===\n{reference.star_examples}"
        )
    if reference.cover_letter_examples:
        parts.append(
            "=== EXAMPLE COVER LETTERS (FOR TONE AND VOICE) ===\n"
            f"{reference.cover_letter_examples}"
        )
    if reference.writing_style:
        parts.append(
            "=== WRITING STYLE GUIDE ===\n"
            "Follow these guidelines for voice, style, and mechanics:\n\n"
            f"{reference.writing_style}"
        )
    if resume_text:
        parts.append(
            f"=== MY RESUME (CUSTOMIZED FOR THIS ROLE) ===\n{resume_text}"
        )
    return "\n\n".join(parts)


def _write_summary(output_dir: Path, results: dict) -> Path:
    path = Path(output_dir, "summary.json")
    path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    return path


class OverwriteConflict(Exception):
    """A fresh apply would overwrite an existing application folder.

    Raised when processing a new JD whose target ``Company - Role`` folder already
    exists and the caller did not opt into overwriting. The webapp surfaces this so
    the user can relaunch with override (acknowledge) or clear the queued JD.

    Attributes:
        folder_name: The conflicting ``Company - Role`` folder name.
    """

    def __init__(self, folder_name: str) -> None:
        self.folder_name = folder_name
        super().__init__(
            f"An application folder already exists for '{folder_name}'. "
            "Relaunch with override to overwrite, or clear the queued JD."
        )


def run_application_workflow(
    job_description_pdf: Path,
    *,
    query_service: AIClient,
    applicant: Applicant,
    output_dir: Optional[Path] = None,
    skip_drive: bool = False,
    highlight_set: Optional[HighlightSet] = None,
    reference: Optional[ReferenceDocs] = None,
    use_cache: bool = True,
    template_id: Optional[str] = None,
    template_name: Optional[str] = None,
    parent_id: Optional[str] = None,
    reuse_folder_id: Optional[str] = None,
    allow_overwrite: bool = False,
    logger: logging.Logger | None = None,
    _credentials_loader: Callable[..., Any] = get_google_credentials,
    _drive_builder: Callable[..., Any] = build_drive_service,
    _docs_builder: Callable[..., Any] = build_docs_service,
) -> dict:
    """Run the full application workflow and return a results dict.

    Arguments:
        job_description_pdf: Path to the job-description PDF.
        query_service: AIClient (callable + cached context + usage).
        applicant: Applicant identity (for cover-letter headers).
        output_dir: Local output directory. Defaults to a temp directory.
        skip_drive: If True, skip all Google Drive/Docs operations.
        highlight_set: Highlights. Loaded from static content if None.
        reference: Reference docs. Loaded from static reference if None.
        use_cache: Whether the model calls consult/populate the response cache.
        template_id: Fallback resume-template Google Doc id when no templates.toml.
        template_name: Explicit template name; if None the archetype is auto-detected.
        parent_id: Applications-root folder id (Drive mode).
        reuse_folder_id: Existing Drive folder id to update in place (re-process mode).
        logger: Optional logger for injection.
        _credentials_loader: Injection point for Google credentials (testing).
        _drive_builder: Injection point for the Drive service builder (testing).
        _docs_builder: Injection point for the Docs service builder (testing).
    Returns:
        A dict of produced paths/ids, job info, and token usage.
    """
    _logger = logger or logging.getLogger(__name__)
    results: dict = {}

    # Step 1: parse JD (no cached context yet).
    _logger.info("Parsing job description: %s", job_description_pdf)
    job = parse_job_description(
        Path(job_description_pdf), query_service, use_cache=use_cache
    )
    results["job_info"] = dcs.asdict(job)
    _logger.info("Parsed: %s / %s", job.company_name, job.role_title)

    output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="job_app_"))
    output_dir.mkdir(parents=True, exist_ok=True)
    results["output_dir"] = str(output_dir)

    highlight_set = highlight_set or load_highlights()
    reference = reference or load_reference_documents()
    context = build_cached_context(highlight_set, reference)
    query_service.set_cached_context(context)
    _logger.info("Cached context: %d characters", len(context))

    # Step 2: select highlights.
    selected = select_highlights(job, highlight_set, query_service, use_cache=use_cache)
    results["highlights"] = [h.context for h in selected]
    _logger.info("Selected %d highlights", len(selected))

    resume_text = None
    drive_service = None
    folder_id = None
    if not skip_drive:
        template = _select_resume_template(
            job, query_service, template_id, template_name, use_cache
        )
        results["template"] = template.name
        _logger.info("Selected resume template: %s", template.name)
        resume_text, drive_service, folder_id = _run_drive_resume_steps(
            job=job,
            output_dir=output_dir,
            query_service=query_service,
            highlight_set=highlight_set,
            reference=reference,
            template=template,
            selected_highlights=selected,
            parent_id=parent_id,
            reuse_folder_id=reuse_folder_id,
            allow_overwrite=allow_overwrite,
            use_cache=use_cache,
            results=results,
            logger=_logger,
            _credentials_loader=_credentials_loader,
            _drive_builder=_drive_builder,
            _docs_builder=_docs_builder,
        )

    # Step 3: cover letter (text + PDF + DOCX).
    letter = generate_cover_letter_text(
        job, selected, query_service, applicant, use_cache=use_cache
    )
    pdf_path = create_cover_letter_pdf(
        letter, Path(output_dir, f"{COVER_LETTER_NAME}.pdf"),
        role_title=job.role_title, company_name=job.company_name, applicant=applicant,
    )
    docx_path = create_cover_letter_docx(
        letter, Path(output_dir, f"{COVER_LETTER_NAME}.docx"),
        role_title=job.role_title, company_name=job.company_name, applicant=applicant,
    )
    results["cover_letter_pdf"] = str(pdf_path)
    results["cover_letter_docx"] = str(docx_path)

    # Step 4: skills analysis (folded into the README, kept locally as data).
    skills = analyze_skills(job, query_service, use_cache=use_cache)
    skills_path = Path(output_dir, SKILLS_NAME)
    skills_path.write_text(json.dumps(skills, indent=2), encoding="utf-8")
    results["skills_analysis"] = str(skills_path)

    # Step 5: README (summary + folded skills + fit).
    readme_path = generate_application_readme(
        job, skills, Path(output_dir, f"{README_NAME}.docx"),
        issues=results.get("issues"),
        template_name=results.get("template"),
        template_archetype=results.get("template_archetype"),
        resume_changes=results.get("resume_changes"),
    )
    results["readme"] = str(readme_path)

    # Copy the JD into the output directory as JD_<Company>_<Role>.pdf (PascalCase).
    jd_name = f"JD_{gdrive.pascal_case(job.company_name)}_{gdrive.pascal_case(job.role_title)}"
    jd_copy = Path(output_dir, f"{jd_name}.pdf")
    # NOTE: in re-process mode the input IS this file; don't copy it onto itself.
    if Path(job_description_pdf).resolve() != jd_copy.resolve():
        shutil.copy2(job_description_pdf, jd_copy)
    results["job_description_pdf"] = str(jd_copy)

    if not skip_drive:
        _upload_outputs(
            drive_service=drive_service,
            folder_id=folder_id,
            readme_path=readme_path,
            jd_copy=jd_copy,
            cover_letter_docx=docx_path,
            logger=_logger,
        )

    usage = getattr(query_service, "usage", None)
    if usage is not None:
        results["token_usage"] = dcs.asdict(usage)
        _logger.info("%s", usage.summary())

    _write_summary(output_dir, results)
    return results


def _select_resume_template(
    job: JobDescription,
    query_service: AIClient,
    template_id: Optional[str],
    template_name: Optional[str],
    use_cache: bool,
) -> ResumeTemplate:
    """Select the resume template, raising if none is configured."""
    template_set = load_templates(fallback_doc_id=template_id)
    template = select_template(
        job, template_set, query_service, name=template_name, use_cache=use_cache
    )
    if template is None:
        raise ValueError(
            "No resume template configured. Add static/content/templates.toml or "
            "set RESUME_TEMPLATE_ID."
        )
    return template


def _run_drive_resume_steps(
    job: JobDescription,
    output_dir: Path,
    query_service: AIClient,
    highlight_set: HighlightSet,
    reference: ReferenceDocs,
    template: ResumeTemplate,
    selected_highlights: Iterable[Highlight],
    parent_id: Optional[str],
    reuse_folder_id: Optional[str],
    allow_overwrite: bool,
    use_cache: bool,
    results: dict,
    logger: logging.Logger,
    _credentials_loader: Callable[..., Any],
    _drive_builder: Callable[..., Any],
    _docs_builder: Callable[..., Any],
) -> tuple[Optional[str], Any, Optional[str]]:
    """Authenticate, find/create the folder, copy and tailor the resume template.

    Returns:
        ``(resume_text, drive_service, folder_id)`` for downstream uploads.
    """
    logger.info("Authenticating with Google")
    creds = _credentials_loader()
    drive_service = _drive_builder(creds)
    docs_service = _docs_builder(creds)

    if reuse_folder_id:
        folder_id = reuse_folder_id
        logger.info("Reusing existing Drive folder: %s", folder_id)
    else:
        # A fresh apply must not silently overwrite an existing application. Reuse
        # (reprocess) goes through reuse_folder_id; an explicit override opts in.
        if not allow_overwrite:
            existing = gdrive.find_application_folder(
                drive_service, job.company_name, job.role_title, parent_id=parent_id
            )
            if existing:
                raise OverwriteConflict(
                    gdrive.application_folder_name(job.company_name, job.role_title)
                )
        folder_id = gdrive.create_application_folder(
            drive_service, job.company_name, job.role_title, parent_id=parent_id,
            logger=logger,
        )
    results["folder_id"] = folder_id

    resume_id = gdrive.copy_resume_template(
        drive_service, folder_id, template.doc_id, name=RESUME_NAME, logger=logger
    )
    results["resume_id"] = resume_id
    results["template_archetype"] = template.archetype

    # Tailor the copied template to the role: rewrite the objective and replace the
    # Key Career Highlights within their configured sections, recording each edit for
    # the application summary and any skipped sections as issues for the README.
    resume_text, results["resume_changes"], resume_issues = tailor_resume(
        docs_service,
        resume_id,
        job,
        selected_highlights,
        query_service,
        sections=template.sections,
        use_cache=use_cache,
        logger=logger,
    )
    if resume_issues:
        results.setdefault("issues", []).extend(resume_issues)

    # Refresh the cached context to include the tailored resume for later calls.
    query_service.set_cached_context(
        build_cached_context(highlight_set, reference, resume_text=resume_text)
    )

    # Quality guard: the resume should fit one page-budget (default 3). Records the
    # result and logs a warning when exceeded so it can be caught before sending.
    results["resume_within_page_limit"] = verify_page_count(
        docs_service, resume_id, logger=logger
    )

    # NOTE: export a local PDF copy of the resume; the Drive artifact is the Doc.
    resume_pdf = gdrive.export_doc_as_pdf(
        drive_service, resume_id, Path(output_dir, f"{RESUME_NAME}.pdf"), logger=logger
    )
    results["resume_pdf"] = str(resume_pdf)
    return resume_text, drive_service, folder_id


def _upload_outputs(
    drive_service: Any,
    folder_id: Optional[str],
    readme_path: Path,
    jd_copy: Path,
    cover_letter_docx: Path,
    logger: logging.Logger,
) -> None:
    """Upload the README, JD, and cover letter to the application's Drive folder.

    NOTE: the resume Google Doc is already in the folder (the template copy), so
        the four folder artifacts are README + JD + resume + cover letter.
    """
    if drive_service is None or folder_id is None:
        return  # EARLY EXIT: nothing to upload.

    gdrive.upload_docx_as_google_doc(
        drive_service, readme_path, folder_id, README_NAME, logger=logger
    )
    gdrive.upload_file(drive_service, jd_copy, folder_id, jd_copy.name, logger=logger)
    gdrive.upload_docx_as_google_doc(
        drive_service, cover_letter_docx, folder_id, COVER_LETTER_NAME, logger=logger
    )


def move_completed_jd(
    src: Path,
    data_dir: Path,
    folder_name: str,
    logger: logging.Logger | None = None,
) -> Path:
    """Move a processed JD into ``<data_dir>/completed/jobs/<folder_name><ext>``.

    Called on a successful application so the JD leaves the input area — the same
    behavior for the CLI and the webapp. Renamed to match the Drive folder.

    Arguments:
        src: The processed job-description file.
        data_dir: Root holding ``jobs/``/``completed/``.
        folder_name: Drive application folder name (``YYYY-MM-DD - Company - Role``).
        logger: Optional logger for injection.
    Returns:
        The new path.
    """
    _logger = logger or logging.getLogger(__name__)
    src = Path(src)
    dest_dir = Path(data_dir) / "completed" / "jobs"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{folder_name}{src.suffix}"
    src.rename(dest)
    _logger.info("Moved JD to completed: %s", dest)
    return dest


def apply_inputs(
    input_path: Path,
    query_service: AIClient,
    applicant: Applicant,
    output_dir: Optional[Path] = None,
    skip_drive: bool = False,
    use_cache: bool = True,
    template_id: Optional[str] = None,
    template_name: Optional[str] = None,
    parent_id: Optional[str] = None,
    data_dir: Optional[Path] = None,
    allow_overwrite: bool = False,
    logger: logging.Logger | None = None,
    _credentials_loader: Callable[..., Any] = get_google_credentials,
    _classify: Callable[..., str] = classify_file,
) -> dict:
    """Run the application workflow for every JD at ``input_path`` (file or dir).

    A single file is processed directly. For a directory, each entry is classified
    and **only job descriptions are processed**; non-JD files (LinkedIn profiles,
    anything unsupported) are skipped with a log line — apply's half of the shared
    single-input-directory. Processing continues past a per-file error.

    Each JD in a directory gets its own ``output_dir/<jd-stem>`` subdirectory, since
    ``run_application_workflow`` writes local artifacts flat into ``output_dir``
    (the per-application folder is created in Drive, not locally) and would
    otherwise clobber the previous JD's files.

    Arguments:
        input_path: A job-description PDF, or a directory of mixed inputs.
        query_service: AIClient driving the workflow (and classifying ambiguous files).
        applicant: Applicant identity.
        output_dir: Local output root. Per-JD subdirs are created under it in dir mode.
        skip_drive: Skip Google Drive/Docs operations.
        use_cache: Whether model calls consult/populate the response cache.
        template_id: Resume-template Google Doc id.
        template_name: Force a resume template (else auto-detected).
        parent_id: Applications-root Drive folder id.
        data_dir: Root holding ``completed/``; when set (and not ``skip_drive``), a
            successfully-applied JD is moved into ``<data_dir>/completed/jobs/``.
        logger: Optional logger for injection.
        _credentials_loader: Injection point for Google credentials (testing).
        _classify: Injection point for the file classifier (testing).
    Returns:
        Summary dict: ``{processed, skipped, failed, items: [{name, status, ...}]}``.
    Raises:
        FileNotFoundError: If ``input_path`` does not exist.
    """
    _logger = logger or logging.getLogger(__name__)
    input_path = Path(input_path)
    if input_path.is_file():
        files = [input_path]
    elif input_path.is_dir():
        files = sorted(f for f in input_path.iterdir() if f.is_file())
    else:
        raise FileNotFoundError(str(input_path))

    is_dir = input_path.is_dir()
    summary: dict = {"processed": 0, "skipped": 0, "failed": 0, "items": []}
    for f in files:
        if is_dir:
            kind = _classify(f, query_service=query_service, use_cache=use_cache, logger=_logger)
            if kind != JD:
                _logger.info("Skipping non-JD (%s): %s", kind, f.name)
                summary["skipped"] += 1
                summary["items"].append(
                    {"name": f.name, "path": str(f), "status": "skipped", "kind": kind}
                )
                continue

        # Give each JD its own subdir so flat artifact writes don't collide.
        out = Path(output_dir, f.stem) if (is_dir and output_dir) else output_dir
        try:
            result = run_application_workflow(
                f,
                query_service=query_service,
                applicant=applicant,
                output_dir=out,
                skip_drive=skip_drive,
                use_cache=use_cache,
                template_id=template_id,
                template_name=template_name,
                parent_id=parent_id,
                allow_overwrite=allow_overwrite,
                logger=_logger,
                _credentials_loader=_credentials_loader,
            )
            # On a real (Drive) completion, move the JD out of the input area into
            # completed/ — identical for CLI and webapp.
            job_info = result.get("job_info") if isinstance(result, dict) else None
            if data_dir is not None and not skip_drive and job_info:
                folder_name = gdrive.application_folder_name(
                    job_info.get("company_name", "Unknown"),
                    job_info.get("role_title", "Unknown"),
                )
                try:
                    move_completed_jd(f, data_dir, folder_name, logger=_logger)
                except OSError as exc:
                    _logger.warning("Could not move JD to completed: %s", exc)
            summary["processed"] += 1
            summary["items"].append(
                {"name": f.name, "path": str(f), "status": "ok", "result": result}
            )
        except OverwriteConflict as exc:
            _logger.warning("Overwrite conflict for %s: %s", f.name, exc)
            summary["failed"] += 1
            summary["items"].append(
                {
                    "name": f.name,
                    "path": str(f),
                    "status": "error",
                    "error": str(exc),
                    "overwrite_conflict": True,
                    "folder_name": exc.folder_name,
                }
            )
        except Exception as exc:  # noqa: BLE001 — continue-on-error is intentional.
            _logger.error("Failed to apply %s: %s", f.name, exc)
            summary["failed"] += 1
            summary["items"].append(
                {"name": f.name, "path": str(f), "status": "error", "error": str(exc)}
            )

    return summary


# __END__
