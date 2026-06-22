#!/usr/bin/env python3
"""Resume template variations (archetypes)."""

import dataclasses as dcs
from collections.abc import Iterable, Mapping
from typing import Optional

# Section kinds — select how a located section is filled during tailoring.
SECTION_OBJECTIVE = "objective"
SECTION_HIGHLIGHTS = "highlights"


@dcs.dataclass(frozen=True)
class ResumeSection:
    """An editable region of a resume template, located by its heading.

    Attributes:
        heading: The section heading text to find (matched case-insensitively).
        section: How the section is filled — ``SECTION_OBJECTIVE`` (model-rewritten
            paragraph) or ``SECTION_HIGHLIGHTS`` (bullets replaced with selected
            highlights, verbatim).
        enabled: Whether the apply flow edits this section. A disabled section is
            omitted from tailoring so its template text is left untouched.
    """

    heading: str
    section: str
    enabled: bool = True


@dcs.dataclass(frozen=True)
class ResumeTemplate:
    """A resume template tailored to a role archetype.

    Attributes:
        name: Stable key (e.g. "print_correspondent").
        archetype: Human-readable archetype label.
        doc_id: Google Doc id of the template.
        keywords: Keywords used to auto-detect the archetype from a job description.
        description: Longer description used in the auto-detection prompt.
        sections: Editable sections located by heading and tailored per ``section``.
    """

    name: str
    archetype: str
    doc_id: str
    keywords: tuple[str, ...] = dcs.field(default_factory=tuple)
    description: Optional[str] = None
    sections: tuple[ResumeSection, ...] = dcs.field(default_factory=tuple)


@dcs.dataclass(frozen=True)
class TemplateSet:
    """A collection of resume templates plus the default selection.

    Attributes:
        templates: All available templates.
        default: Name of the default template.
    """

    templates: tuple[ResumeTemplate, ...]
    default: Optional[str] = None

    def by_name(self, name: str) -> Optional[ResumeTemplate]:
        """Return the template with ``name``, or None."""
        return self._index().get(name)

    def names(self) -> tuple[str, ...]:
        """Return the available template names."""
        return tuple(t.name for t in self.templates)

    def require(self, name: str) -> ResumeTemplate:
        """Return the template with ``name`` or raise.

        Raises:
            KeyError: If no template has that name.
        """
        template = self.by_name(name)
        if template is None:
            raise KeyError(f"Unknown resume template: {name}. Known: {self.names()}")
        return template

    def default_template(self) -> Optional[ResumeTemplate]:
        """Return the default template (falls back to the first available)."""
        if self.default:
            chosen = self.by_name(self.default)
            if chosen is not None:
                return chosen
        return self.templates[0] if self.templates else None

    def _index(self) -> Mapping[str, ResumeTemplate]:
        return {t.name: t for t in self.templates}


def make_template_set(
    templates: Iterable[ResumeTemplate],
    default: Optional[str] = None,
    sections: Iterable[ResumeSection] = (),
) -> TemplateSet:
    """Build a TemplateSet from an iterable of templates.

    NOTE: ``sections`` are shared template structure (the resumes share headings); they
        are attached to every template that does not already define its own.
    """
    shared = tuple(sections)
    built = tuple(
        dcs.replace(t, sections=shared) if shared and not t.sections else t
        for t in templates
    )
    return TemplateSet(templates=built, default=default)


# __END__
