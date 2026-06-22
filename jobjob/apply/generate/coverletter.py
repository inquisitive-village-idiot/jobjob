#!/usr/bin/env python3
"""Step 4: generate the cover-letter body.

NOTE: Reference docs (resume, STAR examples, background) live in the cached
    system context on the query service, so they are not repeated in the prompt.
NOTE: gaps/flags are surfaced in the per-application README (see generate/readme.py),
    not inline in the cover letter.
"""

import json
from collections.abc import Callable, Iterable
from typing import Any

from jobjob.ailib.query import query_ai_service
from jobjob.loader.loadprompt import render_prompt
from jobjob.structure.applicant import Applicant
from jobjob.structure.highlight import Highlight
from jobjob.structure.job_decription import JobDescription


def _passthrough(response: str) -> str:
    """Return the raw text response (cover letters are not JSON)."""
    return response


def _build_prompt(
    job: JobDescription,
    highlights: Iterable[Highlight],
    applicant: Applicant,
) -> str:
    company = job.company_name or "Unknown Company"
    role = job.role_title or "Position"
    texts = [h.text for h in highlights]
    return render_prompt(
        "cover_letter",
        {
            "role": role,
            "company": company,
            "department": job.department or "Not specified",
            "seniority": job.seniority_level or "Not specified",
            "location": list(job.location) or "Not specified",
            "summary": job.summary or "Not available",
            "requirements": ", ".join(list(job.key_requirements)[:5]),
            "responsibilities": ", ".join(list(job.responsibilities)[:5]),
            "highlights_json": json.dumps(texts, indent=2),
            "name": applicant.name,
        },
    )


def _clean_letter(text: str, company: str) -> str:
    """Trim any model preamble before "Dear ..." and resolve company placeholders."""
    lines = text.strip().split("\n")
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("dear"):
            start_idx = i
            break
    cleaned = "\n".join(lines[start_idx:])
    return cleaned.replace("[Company]", company).replace("[COMPANY]", company)


def generate_cover_letter_text(
    job: JobDescription,
    highlights: Iterable[Highlight],
    query_service: Callable[[str], str],
    applicant: Applicant,
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
) -> str:
    """Generate and lightly clean the cover-letter body text.

    Arguments:
        job: The parsed job description.
        highlights: Selected highlights to weave in.
        query_service: Callable that sends a prompt and returns the model text.
        applicant: Applicant identity (used for the closing line).
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        The cleaned cover-letter body.
    """
    prompt = _build_prompt(job, highlights, applicant)
    raw = _query(
        prompt,
        _query_service=query_service,
        _process_response=_passthrough,
        use_cache=use_cache,
    )
    return _clean_letter(raw, job.company_name or "Hiring Manager")


# __END__
