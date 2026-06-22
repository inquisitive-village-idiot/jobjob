#!/usr/bin/env python3
"""Catalog of user-editable prompt templates.

The prompts editor (webapp) exposes these to users for per-profile customization. Only
prompts that are actually wired into a workflow are listed — an unused bundled template
would let a user "edit" a prompt that never takes effect. Placeholders are not declared
here; they are derived from the live template text (``string.Template`` identifiers) so
the catalog cannot drift from the prompt files.
"""

from dataclasses import dataclass

GENERATION = "generation"
EXTRACTION = "extraction"


@dataclass(frozen=True)
class PromptInfo:
    """Metadata for one editable prompt template.

    Arguments:
        stem: Template stem (file ``<stem>.txt`` in the prompt dir).
        title: Human-readable label for the editor.
        kind: ``generation`` (shapes resume/cover-letter/skills output) or
            ``extraction`` (parses an input document into structured fields).
        description: One-line summary of what the prompt does.
    """

    stem: str
    title: str
    kind: str
    description: str


# Order is the display order in the editor: generation prompts (the ones that shape the
# applicant-facing output) first, then extraction prompts.
PROMPT_CATALOG: tuple[PromptInfo, ...] = (
    PromptInfo(
        "resume_objective",
        "Resume objective",
        GENERATION,
        "Rewrites the resume objective for the target role and company.",
    ),
    PromptInfo(
        "cover_letter",
        "Cover letter",
        GENERATION,
        "Generates the cover-letter body in the applicant's voice.",
    ),
    PromptInfo(
        "skills_analysis",
        "Skills gap analysis",
        GENERATION,
        "Categorizes role requirements against documented experience.",
    ),
    PromptInfo(
        "job_description",
        "Job description parse",
        EXTRACTION,
        "Extracts structured fields from a job posting.",
    ),
    PromptInfo(
        "linkedin_profile",
        "LinkedIn profile parse",
        EXTRACTION,
        "Extracts structured fields from a LinkedIn profile (enrich flow).",
    ),
    PromptInfo(
        "resume_import",
        "Résumé import",
        EXTRACTION,
        "Extracts reusable highlights, skills, and objective from an uploaded résumé.",
    ),
)

CATALOG_BY_STEM: dict[str, PromptInfo] = {p.stem: p for p in PROMPT_CATALOG}


# __END__
