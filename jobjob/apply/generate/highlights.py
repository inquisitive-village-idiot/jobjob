#!/usr/bin/env python3
"""Step 2: select the most relevant credential highlights for a role."""

import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Optional

from jobjob.ailib.query import query_ai_service
from jobjob.structure.highlight import Highlight, HighlightSet
from jobjob.structure.job_decription import JobDescription

CANDIDATE_POOL = 10


def score_highlights(
    job: JobDescription,
    highlights: Iterable[Highlight],
) -> Mapping[str, int]:
    """Score highlights by counting keyword hits against the job's text.

    Arguments:
        job: The parsed job description.
        highlights: Highlights to score.
    Returns:
        Mapping of highlight context -> keyword-match count.
    """
    job_text = " ".join(
        [
            job.role_title,
            *job.key_requirements,
            *job.technical_skills,
            *job.keywords,
            *job.responsibilities,
        ]
    ).lower()
    return {
        h.context: sum(1 for kw in h.keywords if kw.lower() in job_text)
        for h in highlights
    }


def _build_prompt(
    job: JobDescription,
    candidates: Mapping[str, Highlight],
    num: int,
    highlight_set: HighlightSet,
) -> str:
    options = {ctx: h.text for ctx, h in candidates.items()}
    return (
        f"Given this job information:\n"
        f"Company: {job.company_name}\n"
        f"Role: {job.role_title}\n"
        f"Key Requirements: {list(job.key_requirements)}\n"
        f"Technical Skills: {list(job.technical_skills)}\n\n"
        f"Select the {num} most relevant highlights from these options:\n\n"
        f"{json.dumps(options, indent=2)}\n\n"
        f"CONSTRAINTS:\n"
        f"- Select exactly {num} highlights\n"
        f"- Total character count should be between {highlight_set.min_characters} "
        f"and {highlight_set.max_characters} characters\n"
        f"- Prioritize highlights that directly address the job requirements\n\n"
        f"Return a JSON array of exactly {num} highlight keys.\n"
        f"Order them by relevance (most relevant first).\n"
        f"Return ONLY the JSON array, no other text."
    )


def select_highlights(
    job: JobDescription,
    highlight_set: HighlightSet,
    query_service: Callable[[str], str],
    num: Optional[int] = None,
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
) -> tuple[Highlight, ...]:
    """Select the ``num`` most relevant enabled highlights for the role.

    Keyword-scores the enabled highlights, asks the model to refine the top
    candidates, then back-fills by score if the model under-returns.

    Arguments:
        job: The parsed job description.
        highlight_set: The loaded highlights and selection defaults.
        query_service: Callable that sends a prompt and returns the model text.
        num: How many to select. Defaults to ``highlight_set.default_number``.
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        The selected highlights, most relevant first.
    """
    num = num or highlight_set.default_number
    enabled = highlight_set.enabled()
    by_context = {h.context: h for h in enabled}

    scores = score_highlights(job, enabled)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    candidates = {ctx: by_context[ctx] for ctx, _ in ranked[:CANDIDATE_POOL]}

    prompt = _build_prompt(job, candidates, num, highlight_set)
    selected_keys = _query(prompt, _query_service=query_service, use_cache=use_cache)

    selected: list[Highlight] = []
    for key in selected_keys:
        highlight = by_context.get(key)
        if highlight is not None and highlight not in selected:
            selected.append(highlight)

    # NOTE: back-fill by score when the model returns too few valid keys.
    for ctx, _ in ranked:
        if len(selected) >= num:
            break
        highlight = by_context[ctx]
        if highlight not in selected:
            selected.append(highlight)

    return tuple(selected[:num])


# __END__
