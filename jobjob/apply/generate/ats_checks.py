#!/usr/bin/env python3
"""ATS parseability checks over a Google Docs JSON document.

Each check is a standalone function ``(document) -> AtsCheck`` so checks can be
tested independently and the active set is visible in one place
(``PARSEABILITY_CHECKS``). Checks are template-dominated: results are stable
across applications sharing a template, but running per application is cheap
and catches template edits.

PROVISIONAL: the check set and the recognized-heading list are first-pass;
calibrate against expert-reviewed ATS assessments.
"""

import dataclasses as dcs
from collections.abc import Callable, Mapping

# Section headings ATS parsers commonly recognize (casefolded comparison).
STANDARD_HEADINGS = frozenset(
    {
        "summary",
        "objective",
        "profile",
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "education",
        "skills",
        "key skills",
        "technical skills",
        "key career highlights",
        "highlights",
        "certifications",
        "projects",
        "publications",
        "awards",
        "contact",
        "references",
    }
)


@dcs.dataclass(frozen=True)
class AtsCheck:
    """One parseability check result."""

    name: str
    passed: bool
    reason: str = ""


def _body_content(document: Mapping) -> list:
    return document.get("body", {}).get("content", [])


def check_content_in_tables(document: Mapping) -> AtsCheck:
    """Warn when body content sits inside tables (parsers often drop cells)."""
    tables = [e for e in _body_content(document) if "table" in e]
    return AtsCheck(
        name="content-in-tables",
        passed=not tables,
        reason=(
            f"{len(tables)} table(s) in the body; many ATS parsers drop " "table cells."
            if tables
            else ""
        ),
    )


def check_nonstandard_headings(document: Mapping) -> AtsCheck:
    """Warn on section headings outside the recognized set."""
    headings = []
    for element in _body_content(document):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
        if style.startswith("HEADING"):
            heading_text = "".join(
                run.get("textRun", {}).get("content", "")
                for run in paragraph.get("elements", [])
            ).strip()
            if heading_text:
                headings.append(heading_text)
    unrecognized = [h for h in headings if h.casefold() not in STANDARD_HEADINGS]
    return AtsCheck(
        name="nonstandard-headings",
        passed=not unrecognized,
        reason=(
            "Headings ATS parsers may not recognize: " + ", ".join(unrecognized[:5])
            if unrecognized
            else ""
        ),
    )


def check_images_or_text_boxes(document: Mapping) -> AtsCheck:
    """Warn on inline/positioned objects (content inside them is invisible)."""
    has_objects = bool(document.get("inlineObjects")) or bool(
        document.get("positionedObjects")
    )
    return AtsCheck(
        name="images-or-text-boxes",
        passed=not has_objects,
        reason=(
            "Images or positioned objects present; content inside them is "
            "invisible to ATS parsers."
            if has_objects
            else ""
        ),
    )


def check_multi_column_layout(document: Mapping) -> AtsCheck:
    """Warn on multi-column sections (column order confuses parsers)."""
    multi_column = any(
        len(
            e.get("sectionBreak", {})
            .get("sectionStyle", {})
            .get("columnProperties", [])
        )
        > 1
        for e in _body_content(document)
    )
    return AtsCheck(
        name="multi-column-layout",
        passed=not multi_column,
        reason=(
            "Multi-column section detected; column order confuses many " "ATS parsers."
            if multi_column
            else ""
        ),
    )


# The active check set, in render order.
PARSEABILITY_CHECKS: tuple[Callable[[Mapping], AtsCheck], ...] = (
    check_content_in_tables,
    check_nonstandard_headings,
    check_images_or_text_boxes,
    check_multi_column_layout,
)


def run_parseability_checks(document: Mapping) -> tuple[AtsCheck, ...]:
    """Run every registered check against the document."""
    return tuple(check(document) for check in PARSEABILITY_CHECKS)


# __END__
