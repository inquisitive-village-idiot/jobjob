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
    requirements = ", ".join(list(job.key_requirements)[:5])
    responsibilities = ", ".join(list(job.responsibilities)[:5])
    return (
        f"Write a cover letter for the {role} position at {company}.\n\n"
        f"POSITION DETAILS:\n"
        f"- Role: {role}\n"
        f"- Department: {job.department or 'Not specified'}\n"
        f"- Seniority: {job.seniority_level or 'Not specified'}\n"
        f"- Location: {list(job.location) or 'Not specified'}\n"
        f"- Role summary: {job.summary or 'Not available'}\n"
        f"- Key requirements: {requirements}\n"
        f"- Main responsibilities: {responsibilities}\n\n"
        f"CANDIDATE EXPERIENCE (these highlights appear word-for-word on the "
        f"resume submitted with this letter):\n{json.dumps(texts, indent=2)}\n\n"
        f"THE LETTER MUST NOT REGURGITATE THE RESUME:\n"
        f"- The reader has the resume next to this letter; copying phrases from "
        f"the highlights wastes the page\n"
        f"- Retell one or two highlights as short stories instead: the situation, "
        f"the insight, why it mattered -- in fresh language\n"
        f"- Add what the resume cannot say: a point of view, a lesson learned, "
        f"the reasoning behind the work\n\n"
        f"OPENING:\n"
        f"- Ground the opening in what the job description itself emphasizes: a "
        f"named initiative, the mission of the department, or the specific problem "
        f"this role exists to solve. Name it explicitly.\n"
        f"- You may draw on well-established knowledge of {company}, but never "
        f"invent specifics (initiatives, products, news) you are not sure of.\n"
        f"- The hook must connect that specific to the candidate's experience -- a "
        f"non-obvious connection beats a flattering one.\n\n"
        f"WRITING GUIDELINES:\n"
        "- Write conversationally, as if explaining to a colleague why this role "
        "excites you\n"
        f"- One or two concrete examples are enough; don't list everything\n"
        f"- Make a claim about how the work should be done (a point of view), not "
        f"just a recitation of what was done\n"
        f"- Vary sentence length and structure; read it back for rhythm\n"
        "- Let the letter flow naturally; prioritize readability over hitting "
        "every point\n"
        f"- 300-400 words maximum\n"
        f"- Only use facts from the reference documents in your context\n"
        f"- Avoid em dashes; use commas or semicolons instead\n\n"
        f"BAD PATTERNS TO AVOID:\n"
        f'- "[Gerund phrase]. This is what I did at X, and it\'s what draws me to Y."\n'
        f"- Openers that describe the candidate instead of engaging the company "
        f'("I love...", "I am a...", "As a...")\n'
        f"- Listing multiple achievements in rapid succession without connecting them\n"
        f"- Generic praise of the company without specific insight\n"
        f'- Stock closers ("I\'d welcome the chance to discuss..."); close with '
        f"something specific to this role instead\n"
        f"- Stiff, formal language that sounds like a template\n\n"
        f"FORMAT:\n"
        f'- Start with "Dear {company} Hiring Manager,"\n'
        f'- End with "Sincerely,\\n\\n{applicant.name}"\n'
        f"- Return ONLY the letter body (no header/contact info)"
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
