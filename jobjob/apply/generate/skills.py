#!/usr/bin/env python3
"""Step 5: gap analysis of job requirements against documented experience.

NOTE: The resume, STAR examples, highlights, and background live in the cached
    system context on the query service, so they are not repeated in the prompt.
"""

import json
from collections.abc import Callable
from typing import Any

from jobjob.ailib.query import query_ai_service
from jobjob.structure.job_decription import JobDescription


def _build_prompt(job: JobDescription) -> str:
    return (
        "Analyze the job requirements and categorize skills based on my documented "
        "experience (in your context).\n\n"
        f"JOB INFORMATION:\nCompany: {job.company_name}\nRole: {job.role_title}\n\n"
        f"KEY REQUIREMENTS:\n{json.dumps(list(job.key_requirements), indent=2)}\n\n"
        "TECHNICAL SKILLS MENTIONED:\n"
        f"{json.dumps(list(job.technical_skills), indent=2)}\n\n"
        "TASK:\nUsing the resume, STAR examples, highlights, and background in your "
        "context, categorize skills as:\n\n"
        '- "critical_gaps": Skills essential for the role that I lack documented '
        "evidence for\n"
        '- "critical_supported": Essential skills with explicit evidence in my '
        "documentation\n"
        '- "important_supported": Nice-to-have skills with documented evidence\n'
        '- "strong_supporting": Additional relevant skills from my background\n\n'
        "Return JSON with keys critical_gaps, critical_supported, important_supported, "
        "strong_supporting. Each critical_gaps item has "
        "skill/why_critical/mitigation/severity; "
        "supported items have skill/evidence; strong_supporting items have "
        "skill/relevance.\n\n"
        "RULES:\n"
        "1. Only mark a skill as supported if there is EXPLICIT evidence in the "
        "documentation\n"
        "2. Be conservative - if uncertain, put it in critical_gaps\n"
        '3. Extract specific skills, not vague categories (e.g., "Python" not '
        '"programming")\n'
        "4. Include 3-8 items per category (fewer is fine if not applicable)\n"
        "5. For critical_gaps, always include a realistic mitigation strategy\n"
        "6. For critical_gaps, rate severity as one of:\n"
        '   - "blocking": a hard threshold requirement with no adjacent experience; '
        "likely disqualifying on its own\n"
        '   - "stretch": genuinely required, but adjacent/transferable experience '
        "makes it credible to ramp up\n"
        '   - "aspirational": forward-looking or nice-to-have phrased as a '
        "requirement (e.g. emerging-tech familiarity)\n\n"
        "Return ONLY valid JSON."
    )


def analyze_skills(
    job: JobDescription,
    query_service: Callable[[str], str],
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
) -> dict:
    """Categorize role skills against documented experience.

    Arguments:
        job: The parsed job description.
        query_service: Callable that sends a prompt and returns the model text.
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        A dict with critical_gaps / critical_supported / important_supported /
        strong_supporting lists.
    """
    prompt = _build_prompt(job)
    return _query(prompt, _query_service=query_service, use_cache=use_cache)


# __END__
