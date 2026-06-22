#!/usr/bin/env python3
"""Step 5: gap analysis of job requirements against documented experience.

NOTE: The resume, STAR examples, highlights, and background live in the cached
    system context on the query service, so they are not repeated in the prompt.
"""

import json
from collections.abc import Callable
from typing import Any

from jobjob.ailib.query import query_ai_service
from jobjob.loader.loadprompt import render_prompt
from jobjob.structure.job_decription import JobDescription


def _build_prompt(job: JobDescription) -> str:
    return render_prompt(
        "skills_analysis",
        {
            "company_name": job.company_name,
            "role_title": job.role_title,
            "key_requirements": json.dumps(list(job.key_requirements), indent=2),
            "technical_skills": json.dumps(list(job.technical_skills), indent=2),
        },
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
