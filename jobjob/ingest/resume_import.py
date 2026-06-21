#!/usr/bin/env python3
"""Extract reusable jobjob content (highlights, skills, background) from a resume.

Reuses the document text loaders and the AI query layer, but — unlike the JD parser —
returns a richer nested draft (lists of highlights/skills) rather than a flat dataclass,
so it builds the draft from the model's JSON itself instead of ``from_mapping``.
"""

import dataclasses as dcs
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from jobjob.ailib.query import query_ai_service
from jobjob.loader.loadreference import load_reference_documents
from jobjob.loader.loadstatic import read_document
from jobjob.loader.location import get_prompt_path
from jobjob.structure.highlight import Highlight
from jobjob.structure.skill import Skill

BACKGROUND_MODES = ("conservative", "fuller")
SAVE_MODES = ("replace", "append")

# Pre-compiled pattern for slugifying labels/contexts into snake_case identifiers.
_SLUG_RE = re.compile(r"[^a-z0-9]+")

_CONSERVATIVE_GUIDANCE = (
    "A concise professional-background narrative (two to four sentences) summarizing the "
    "candidate's career, drawn strictly from the resume. Stay factual and conservative; "
    "do not embellish or infer beyond what is written."
)
_FULLER_GUIDANCE = (
    "A fuller professional-background narrative (one to two short paragraphs) summarizing "
    "the candidate's career arc and strengths, drawn from the resume. You may connect "
    "themes and articulate strengths in the candidate's voice, but never invent employers, "
    "titles, dates, metrics, or credentials."
)


@dcs.dataclass(frozen=True)
class ResumeImportDraft:
    """A staged, editable set of content extracted from a resume.

    Attributes:
        objective: A suggested resume objective/summary line.
        sections: Section headings detected in the resume (informational).
        highlights: Reusable accomplishment blocks (with inferred topic + keywords).
        skills: Reusable skill entries.
        background: A professional-background narrative for ``reference/background``.
    """

    objective: str
    sections: tuple[str, ...]
    highlights: tuple[Highlight, ...]
    skills: tuple[Skill, ...]
    background: str


def _slugify(value: str, fallback: str = "item") -> str:
    """Return a lowercase snake_case identifier derived from ``value``."""
    slug = _SLUG_RE.sub("_", (value or "").lower()).strip("_")
    return slug or fallback


def _dedupe_key(key: str, seen: set[str]) -> str:
    """Return ``key`` made unique against ``seen`` by appending a counter."""
    if key not in seen:
        seen.add(key)
        return key
    n = 2
    while f"{key}_{n}" in seen:
        n += 1
    unique = f"{key}_{n}"
    seen.add(unique)
    return unique


def _as_keywords(value: Any) -> tuple[str, ...]:
    """Coerce a model-supplied keywords value into a tuple of clean strings."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(k).strip() for k in value if str(k).strip())


def highlight_from_dict(data: dict, seen: Optional[set[str]] = None) -> Highlight:
    """Build a Highlight from a loosely-typed mapping (model output or edited draft)."""
    seen = seen if seen is not None else set()
    text = str(data.get("text") or "").strip()
    context = _slugify(str(data.get("context") or ""), fallback=_slugify(text[:30], "highlight"))
    return Highlight(
        context=_dedupe_key(context, seen),
        text=text,
        keywords=_as_keywords(data.get("keywords")),
        enabled=bool(data.get("enabled", True)),
        topic=str(data.get("topic") or "").strip(),
    )


def skill_from_dict(data: dict, seen: Optional[set[str]] = None) -> Skill:
    """Build a Skill from a loosely-typed mapping (model output or edited draft)."""
    seen = seen if seen is not None else set()
    text = str(data.get("text") or "").strip()
    label = _slugify(str(data.get("label") or ""), fallback=_slugify(text, "skill"))
    return Skill(
        label=_dedupe_key(label, seen),
        text=text,
        keywords=_as_keywords(data.get("keywords")),
    )


def _voice_anchor(
    reference_dir: Optional[Path],
    max_chars: int = 4000,
    *,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Return a voice-sample block from writing_style/cover_letters, or "".

    Used only in fuller mode: gives the model the candidate's own voice to mirror in
    the objective and background, without copying the samples' content.
    """
    _logger = logger or logging.getLogger(__name__)
    try:
        docs = load_reference_documents(reference_dir)
    except Exception as exc:  # reference dir may be absent in a fresh install
        _logger.debug("No reference docs for voice anchor: %s", exc)
        return ""
    parts = [p for p in (docs.writing_style, docs.cover_letter_examples) if p]
    if not parts:
        return ""
    samples = "\n\n".join(parts)[:max_chars]
    return (
        "\nVOICE SAMPLES (match this writing voice and tone in the objective and "
        "background; do not copy their content or claims):\n"
        f"{samples}\n"
    )


def build_prompt(
    text_content: str,
    *,
    background_mode: str = "fuller",
    reference_dir: Optional[Path] = None,
    prompt_path: Optional[Path] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Format the resume-import prompt for the given resume text and background mode."""
    if background_mode not in BACKGROUND_MODES:
        raise ValueError(
            f"Unknown background_mode {background_mode!r}; expected one of {BACKGROUND_MODES}"
        )
    guidance = _FULLER_GUIDANCE if background_mode == "fuller" else _CONSERVATIVE_GUIDANCE
    anchor = (
        _voice_anchor(reference_dir, logger=logger)
        if background_mode == "fuller"
        else ""
    )
    template = (prompt_path or get_prompt_path("resume_import")).read_text(encoding="utf-8")
    return template.format(
        text_content=text_content,
        background_guidance=guidance,
        voice_anchor=anchor,
    )


def _draft_from_mapping(data: dict) -> ResumeImportDraft:
    """Build a ResumeImportDraft from the model's parsed JSON mapping."""
    seen_h: set[str] = set()
    highlights = tuple(
        highlight_from_dict(h, seen_h)
        for h in (data.get("highlights") or [])
        if isinstance(h, dict) and str(h.get("text") or "").strip()
    )
    seen_s: set[str] = set()
    skills = tuple(
        skill_from_dict(s, seen_s)
        for s in (data.get("skills") or [])
        if isinstance(s, dict) and str(s.get("text") or "").strip()
    )
    sections = tuple(
        str(x).strip() for x in (data.get("sections") or []) if str(x).strip()
    )
    return ResumeImportDraft(
        objective=str(data.get("objective") or "").strip(),
        sections=sections,
        highlights=highlights,
        skills=skills,
        background=str(data.get("background") or "").strip(),
    )


def extract_resume(
    path: Path,
    query_service: Any,
    *,
    background_mode: str = "fuller",
    reference_dir: Optional[Path] = None,
    use_cache: bool = True,
    logger: Optional[logging.Logger] = None,
    _query: Callable[..., Any] = query_ai_service,
    _load_text: Callable[[Path], str] = read_document,
) -> ResumeImportDraft:
    """Extract a staged content draft from a resume document.

    Arguments:
        path: The resume file (.pdf/.docx/.txt/.md).
        query_service: AIClient (the same object the apply/enrich flows use).
        background_mode: "fuller" (default; leans on the profile's voice samples) or
            "conservative" (factual, minimal).
        reference_dir: Override the reference dir used for voice samples (testing).
        use_cache: Whether the query consults/populates the response cache.
        logger: Optional logger; passed through to prompt building.
        _query: Injection point for the AI query (testing).
        _load_text: Injection point for the document text reader (testing).
    Returns:
        A ResumeImportDraft of highlights, skills, objective, sections, and background.
    Raises:
        ValueError: If no text can be read from the document or the mode is unknown.
    """
    path = Path(path)
    text = (_load_text(path) or "").strip()
    if not text:
        raise ValueError(
            f"Could not read any text from {path.name}. If it is a scanned/image-only "
            "PDF, export a text-based PDF or DOCX and try again."
        )
    prompt = build_prompt(
        text,
        background_mode=background_mode,
        reference_dir=reference_dir,
        logger=logger,
    )
    data = _query(prompt, _query_service=query_service, use_cache=use_cache)
    if not isinstance(data, dict):
        raise ValueError("Resume extraction did not return a JSON object.")
    return _draft_from_mapping(data)


def draft_to_dict(draft: ResumeImportDraft) -> dict:
    """Serialize a draft to a JSON-able dict for the webapp review UI."""
    return {
        "objective": draft.objective,
        "sections": list(draft.sections),
        "background": draft.background,
        "highlights": [
            {
                "context": h.context,
                "topic": h.topic,
                "text": h.text,
                "keywords": list(h.keywords),
                "enabled": h.enabled,
            }
            for h in draft.highlights
        ],
        "skills": [
            {"label": s.label, "text": s.text, "keywords": list(s.keywords)}
            for s in draft.skills
        ],
    }


# __END__
