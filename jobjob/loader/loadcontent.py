#!/usr/bin/env python3
"""Load credential highlights and skills from the static TOML content files."""

import tomllib
from pathlib import Path
from typing import Optional

from jobjob.loader.location import get_content_path
from jobjob.structure.highlight import Highlight, HighlightSet, make_highlight_set
from jobjob.structure.skill import Skill, SkillSet, make_skill_set
from jobjob.structure.template import (
    ResumeSection,
    ResumeTemplate,
    TemplateSet,
    make_template_set,
)

DEFAULT_TEMPLATE_NAME = "default"


def _load_toml_table(path: Path, name: str) -> dict:
    """Return the ``[tool.<name>]`` table from a TOML file.

    Arguments:
        path: Path to the TOML file.
        name: The sub-table key under ``[tool]`` (e.g. "highlights").
    Returns:
        The table dict.
    Raises:
        ValueError: If the expected ``[tool.<name>]`` table is missing.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    try:
        return data["tool"][name]
    except KeyError:
        raise ValueError(f"Missing [tool.{name}] table in {path}")


def load_highlights(path: Optional[Path] = None) -> HighlightSet:
    """Load the highlight set from ``static/content/highlights.toml``.

    Arguments:
        path: Override path to the TOML file. Defaults to the static content path.
    Returns:
        A populated HighlightSet.
    """
    path = path or get_content_path("highlights")
    table = _load_toml_table(path, "highlights")
    highlights = [
        Highlight(
            context=entry["context"],
            text=entry["text"].strip(),
            keywords=tuple(entry.get("keywords", ())),
            enabled=entry.get("enabled", True),
            topic=entry.get("topic", ""),
        )
        for entry in table.get("highlight", [])
    ]
    # NOTE: pass through TOML values (or None) — the defaults live on HighlightSet.
    return make_highlight_set(
        highlights,
        default_number=table.get("default_number"),
        max_characters=table.get("max_characters"),
        min_characters=table.get("min_characters"),
    )


def load_skills(path: Optional[Path] = None) -> SkillSet:
    """Load the skill set from ``static/content/skills.toml``.

    Arguments:
        path: Override path to the TOML file. Defaults to the static content path.
    Returns:
        A populated SkillSet.
    """
    path = path or get_content_path("skills")
    table = _load_toml_table(path, "skills")
    skills = [
        Skill(
            label=entry["label"],
            text=entry["text"],
            keywords=tuple(entry.get("keywords", ())),
        )
        for entry in table.get("skill", [])
    ]
    # NOTE: pass through TOML value (or None) — the default lives on SkillSet.
    return make_skill_set(skills, default_number=table.get("default_number"))


def load_templates(
    path: Optional[Path] = None,
    fallback_doc_id: Optional[str] = None,
) -> TemplateSet:
    """Load resume templates from ``static/content/templates.toml``.

    NOTE: when the TOML is absent and ``fallback_doc_id`` is given, returns a
        single "default" template using that id (backward-compatible with a single
        ``RESUME_TEMPLATE_ID``).

    Arguments:
        path: Override path to the TOML file. Defaults to the static content path.
        fallback_doc_id: A single Google Doc id to use when no TOML is present.
    Returns:
        A TemplateSet (possibly empty if neither source is available).
    """
    if path is None:
        try:
            path = get_content_path("templates")
        except (FileNotFoundError, ValueError):
            path = None

    if path is None:
        if fallback_doc_id:
            template = ResumeTemplate(
                name=DEFAULT_TEMPLATE_NAME, archetype="Default", doc_id=fallback_doc_id
            )
            return make_template_set([template], default=DEFAULT_TEMPLATE_NAME)
        return make_template_set([])  # EARLY EXIT: nothing configured.

    table = _load_toml_table(path, "templates")
    templates = [
        ResumeTemplate(
            name=entry["name"],
            archetype=entry.get("archetype", ""),
            doc_id=entry.get("doc_id", ""),
            keywords=tuple(entry.get("keywords", ())),
            description=entry.get("description"),
        )
        for entry in table.get("template", [])
    ]
    sections = [
        ResumeSection(heading=entry["heading"], section=entry["section"])
        for entry in table.get("section", [])
    ]
    return make_template_set(templates, default=table.get("default"), sections=sections)


# __END__
