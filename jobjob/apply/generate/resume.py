#!/usr/bin/env python3
"""Tailor the copied resume Google Doc to a role.

Edits are **section-anchored**: each editable region is located by its heading (from
the template's section config) and its text is replaced within that section by index
range — not by document-wide keyword replacement. The objective is rewritten by the
model; the Key Career Highlights bullets are replaced with the selected credential
highlights verbatim (bullet formatting is retained). A configured section that cannot
be found is skipped and recorded as an issue (surfaced in the application README).

NOTE: the Docs I/O (find the section, build delete/insert requests) is the thin,
    separately-tested ``gapi.docs`` layer; this module owns the content strategy.
"""

import json
import logging
from collections.abc import Callable, Iterable
from typing import Any, Optional

from jobjob.ailib.query import query_ai_service
from jobjob.gapi.docs import (
    find_section,
    get_document,
    get_document_text,
    paragraph_text,
    replace_paragraph_text_requests,
)
from jobjob.structure.highlight import Highlight
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.template import (
    SECTION_HIGHLIGHTS,
    SECTION_OBJECTIVE,
    ResumeSection,
)

ROLE_PLACEHOLDER = "PLACEHOLDER"
_TRUNCATE = 60


def _truncate(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _TRUNCATE else text[: _TRUNCATE - 1] + "…"


def _build_objective_prompt(
    job: JobDescription, current_objective: str, industry: Optional[str] = None
) -> str:
    # When the profile declares its field, anchor "describe the company accurately"
    # to that domain; otherwise keep a neutral rule with no baked-in example.
    if industry and industry.strip():
        accuracy_rule = (
            "2. Describe the company accurately for its actual industry "
            f"({industry.strip()}); do not mislabel it as a different kind of "
            "company\n"
        )
    else:
        accuracy_rule = (
            "2. Describe the company accurately; do not mislabel the kind of "
            "company it is\n"
        )
    return (
        "Rewrite the OBJECTIVE statement of a resume for a specific role.\n\n"
        f"TARGET ROLE: {job.role_title} at {job.company_name}\n\n"
        f"KEY JOB REQUIREMENTS:\n{json.dumps(list(job.key_requirements), indent=2)}\n\n"
        f"CURRENT OBJECTIVE:\n{current_objective}\n\n"
        "RULES:\n"
        "1. Rewrite the objective for THIS role and company: name the company and use "
        "a natural form of the role title — expand or drop internal "
        "abbreviations/jargon (e.g. org-unit codes) that an outside reader would not "
        "use\n"
        f"{accuracy_rule}"
        "3. Keep it to 1-2 sentences, and preserve any existing relocation sentence "
        "verbatim\n"
        "4. Do not invent facts; only use the current objective and job information "
        "provided\n\n"
        'Return ONLY valid JSON: {"objective": "the rewritten objective text"}'
    )


def tailor_resume(
    docs_service: Any,
    doc_id: str,
    job: JobDescription,
    selected_highlights: Iterable[Highlight],
    query_service: Callable[[str], str],
    sections: Iterable[ResumeSection] = (),
    use_cache: bool = True,
    industry: Optional[str] = None,
    logger: logging.Logger | None = None,
    _query: Callable[..., Any] = query_ai_service,
) -> tuple[str, list[str], list[str]]:
    """Apply role-specific, section-anchored edits to the resume doc.

    Locates each configured section by heading and replaces its text in place: the
    objective is rewritten by the model; the highlights bullets are replaced with the
    selected highlight texts verbatim (retaining bullet formatting). Finally the
    ``PLACEHOLDER`` role token is swapped for the role title. Sections that cannot be
    found are skipped and reported.

    Arguments:
        docs_service: Google Docs service client.
        doc_id: The copied resume document id.
        job: The parsed job description.
        selected_highlights: Highlights chosen for this role (most relevant first).
        query_service: Callable that sends a prompt and returns the model text.
        sections: Editable sections (heading + kind) from the template config.
        use_cache: Whether the model call consults/populates the response cache.
        industry: Optional domain/industry context for the active profile, passed to
            the objective prompt so the company is described accurately.
        logger: Optional logger for injection.
        _query: Injection point for ``query_ai_service`` (testing).
    Returns:
        ``(updated_resume_text, changes, issues)`` — ``changes`` is a human-readable
        list of edits applied; ``issues`` lists sections skipped or problems found,
        surfaced in the application README.
    """
    _logger = logger or logging.getLogger(__name__)
    document = get_document(docs_service, doc_id)
    content = document.get("body", {}).get("content", [])
    highlight_texts = [h.text for h in selected_highlights]

    changes: list[str] = []
    issues: list[str] = []
    # Each entry: (anchor_start_index, [requests]). Applied high-index-first so edits
    # do not shift the indices of lower-index edits in the same batchUpdate.
    index_ops: list[tuple[int, list[dict]]] = []

    for section in sections:
        found = find_section(content, section.heading)
        if found is None:
            msg = f"Resume section “{section.heading}” not found; left unchanged."
            _logger.warning(msg)
            issues.append(msg)
            continue
        _, body = found
        if section.section == SECTION_OBJECTIVE:
            _tailor_objective(
                body, job, query_service, use_cache, index_ops, changes, issues,
                industry=industry, _query=_query, logger=_logger,
            )
        elif section.section == SECTION_HIGHLIGHTS:
            _tailor_highlights(body, highlight_texts, index_ops, changes, issues)
        else:
            issues.append(f"Unknown resume section kind “{section.section}”; skipped.")

    # Assemble: index-based edits first (descending anchor), then the role-token swap
    # (text-based, so it must run after all index math).
    requests: list[dict] = []
    for _, reqs in sorted(index_ops, key=lambda op: op[0], reverse=True):
        requests.extend(reqs)
    role = job.role_title or "Target Role"
    requests.append(
        {
            "replaceAllText": {
                "containsText": {"text": ROLE_PLACEHOLDER, "matchCase": True},
                "replaceText": role,
            }
        }
    )
    changes.append(f"Set role title to “{role}”.")

    if requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()
    _logger.info(
        "Tailored resume: %d request(s), %d issue(s)", len(requests), len(issues)
    )
    return get_document_text(docs_service, doc_id), changes, issues


def _tailor_objective(
    body: list[dict],
    job: JobDescription,
    query_service: Callable[[str], str],
    use_cache: bool,
    index_ops: list[tuple[int, list[dict]]],
    changes: list[str],
    issues: list[str],
    *,
    industry: Optional[str] = None,
    _query: Callable[..., Any],
    logger: logging.Logger,
) -> None:
    """Rewrite the objective paragraph (the first body paragraph of the section)."""
    if not body:
        issues.append("Objective section has no body paragraph; left unchanged.")
        return
    target = body[0]
    current = paragraph_text(target).strip()
    edits = _query(
        _build_objective_prompt(job, current, industry),
        _query_service=query_service,
        use_cache=use_cache,
    )
    new_obj = edits.get("objective") if isinstance(edits, dict) else None
    if not new_obj:
        issues.append("Objective rewrite produced no text; left unchanged.")
        return
    reqs = replace_paragraph_text_requests(target, new_obj)
    if reqs:
        index_ops.append((target["startIndex"], reqs))
        changes.append(f"Objective: “{_truncate(current)}” → “{_truncate(new_obj)}”")


def _tailor_highlights(
    body: list[dict],
    highlight_texts: list[str],
    index_ops: list[tuple[int, list[dict]]],
    changes: list[str],
    issues: list[str],
) -> None:
    """Replace the bullet paragraphs with the selected highlights, retaining bullets.

    Replaces in place up to the smaller count; appends extra bullets inside the
    existing list (so they inherit the list/bullet style) or deletes surplus ones.
    """
    if not body:
        issues.append("Highlights section has no bullets; left unchanged.")
        return
    n = min(len(body), len(highlight_texts))
    for i in range(n):
        reqs = replace_paragraph_text_requests(body[i], highlight_texts[i])
        if reqs:
            index_ops.append((body[i]["startIndex"], reqs))
    changes.append(f"Replaced {n} highlight bullet(s).")

    if len(highlight_texts) > len(body):
        extras = highlight_texts[len(body):]
        # Insert just before the last bullet's terminating newline so the new
        # paragraphs land inside the list and inherit its bullet style.
        anchor = body[-1]["endIndex"] - 1
        text = "".join("\n" + t for t in extras)
        index_ops.append(
            (anchor, [{"insertText": {"location": {"index": anchor}, "text": text}}])
        )
        changes.append(f"Added {len(extras)} highlight bullet(s).")
    elif len(highlight_texts) < len(body):
        surplus = body[len(highlight_texts):]
        start, end = surplus[0]["startIndex"], surplus[-1]["endIndex"]
        index_ops.append(
            (start, [{"deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}}])
        )
        changes.append(f"Removed {len(surplus)} highlight bullet(s).")


# __END__
