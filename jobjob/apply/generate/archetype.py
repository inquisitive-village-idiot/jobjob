#!/usr/bin/env python3
"""Select the resume template (archetype) for a role.

Uses an explicit name when given, otherwise asks the model to classify the job
description against the configured archetypes. Detection only needs the job
description and the template descriptions, so it can run before the resume is set
on the cached context.
"""

import json
from collections.abc import Callable
from typing import Any, Optional

from jobjob.ailib.query import query_ai_service
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.template import ResumeTemplate, TemplateSet


def _build_prompt(job: JobDescription, template_set: TemplateSet) -> str:
    options = {t.name: (t.description or t.archetype) for t in template_set.templates}
    return (
        "Choose the single best resume archetype for this job.\n\n"
        f"Company: {job.company_name}\n"
        f"Role: {job.role_title}\n"
        f"Seniority: {job.seniority_level}\n"
        f"Summary: {job.summary}\n"
        f"Key requirements: {list(job.key_requirements)}\n\n"
        f"ARCHETYPES (name: description):\n{json.dumps(options, indent=2)}\n\n"
        'Return JSON: {"template": "<archetype name>"} using exactly one of the '
        "names above. Return ONLY the JSON."
    )


def detect_archetype(
    job: JobDescription,
    template_set: TemplateSet,
    query_service: Callable[[str], str],
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
) -> Optional[str]:
    """Return the model-selected template name, or None if undetermined.

    NOTE: short-circuits without an API call when there are 0 or 1 templates.

    Arguments:
        job: The parsed job description.
        template_set: The available templates.
        query_service: Callable that sends a prompt and returns the model text.
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        The chosen template name, or None.
    """
    templates = template_set.templates
    if len(templates) <= 1:
        return templates[0].name if templates else None  # EARLY EXIT: no choice.

    prompt = _build_prompt(job, template_set)
    data = _query(prompt, _query_service=query_service, use_cache=use_cache)
    return data.get("template") if isinstance(data, dict) else None


def select_template(
    job: JobDescription,
    template_set: TemplateSet,
    query_service: Callable[[str], str],
    name: Optional[str] = None,
    use_cache: bool = True,
    _query: Callable[..., Any] = query_ai_service,
) -> Optional[ResumeTemplate]:
    """Select a resume template by explicit name, else auto-detect the archetype.

    Arguments:
        job: The parsed job description.
        template_set: The available templates.
        query_service: Callable that sends a prompt and returns the model text.
        name: Explicit template name. When given, it is required to exist.
        use_cache: Whether to consult/populate the response cache.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        The selected template, or None if none are configured.
    Raises:
        KeyError: If ``name`` is given but unknown.
    """
    if name:
        return template_set.require(name)  # EARLY EXIT: explicit selection.

    chosen = detect_archetype(
        job, template_set, query_service, use_cache=use_cache, _query=_query
    )
    # NOTE: fall back to the default when the model returns nothing usable.
    if chosen:
        template = template_set.by_name(chosen)
        if template is not None:
            return template
    return template_set.default_template()


# __END__
