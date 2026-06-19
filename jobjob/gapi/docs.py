#!/usr/bin/env python3
"""Google Docs operations: text extraction, text replacement, page estimation.

NOTE: The resume *content* strategy (which text to replace) is reworked in part 2
    (block-aware swap). This module stays a thin, tested I/O layer over the Docs API.
"""

import logging
from collections.abc import Mapping
from typing import Any, Optional

CHARS_PER_PAGE = 5000
PAGE_BUFFER = 0.5

# Paragraph named styles that denote a section heading (vs. body text).
_HEADING_STYLES = {
    "TITLE",
    "SUBTITLE",
    "HEADING_1",
    "HEADING_2",
    "HEADING_3",
    "HEADING_4",
    "HEADING_5",
    "HEADING_6",
}


def extract_doc_text(content: list) -> str:
    """Extract plain text from a Google Docs ``body.content`` structure.

    Arguments:
        content: The list of structural elements (paragraphs, tables).
    Returns:
        The concatenated text.
    """
    parts = []
    for element in content:
        if "paragraph" in element:
            for elem in element["paragraph"].get("elements", []):
                if "textRun" in elem:
                    parts.append(elem["textRun"].get("content", ""))
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    parts.append(extract_doc_text(cell.get("content", [])))
    return "".join(parts)


def get_document_text(service: Any, doc_id: str) -> str:
    """Fetch a document and return its plain text."""
    doc = service.documents().get(documentId=doc_id).execute()
    return extract_doc_text(doc.get("body", {}).get("content", []))


def get_document(service: Any, doc_id: str) -> dict:
    """Fetch the full document structure (for index/section-aware editing)."""
    return service.documents().get(documentId=doc_id).execute()


def paragraph_text(element: Mapping) -> str:
    """Return the plain text of a single ``body.content`` paragraph element."""
    parts = []
    for elem in element.get("paragraph", {}).get("elements", []):
        if "textRun" in elem:
            parts.append(elem["textRun"].get("content", ""))
    return "".join(parts)


def is_heading(element: Mapping) -> bool:
    """Return True if ``element`` is a paragraph styled as a heading/title."""
    paragraph = element.get("paragraph")
    if not paragraph:
        return False
    style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
    return style in _HEADING_STYLES


def find_section(content: list, heading: str) -> Optional[tuple[dict, list[dict]]]:
    """Locate a section by its heading and return ``(heading_elem, body_paragraphs)``.

    The heading is matched case-insensitively (trimmed) against paragraphs styled as a
    heading. The body is the run of paragraph elements after the heading up to the next
    heading (or document end); non-paragraph elements (e.g. tables) are skipped.

    Arguments:
        content: The document ``body.content`` list.
        heading: The section heading text to find.
    Returns:
        ``(heading_element, [body_paragraph_elements])`` or None when not found.
    """
    target = heading.strip().casefold()
    start = None
    for index, element in enumerate(content):
        if is_heading(element) and paragraph_text(element).strip().casefold() == target:
            start = index
            break
    if start is None:
        return None  # EARLY EXIT: heading not present.

    body: list[dict] = []
    for element in content[start + 1:]:
        if is_heading(element):
            break  # Next section begins.
        if "paragraph" in element:
            body.append(element)
    return content[start], body


def replace_paragraph_text_requests(element: Mapping, new_text: str) -> list[dict]:
    """Build requests that swap a paragraph's text while keeping the paragraph.

    Deletes the paragraph's text range (preserving its terminating newline, so the
    paragraph — and its bullet/list style — survives) and inserts ``new_text`` at the
    paragraph start. Returns an empty list when there is nothing to do.
    """
    start = element.get("startIndex")
    end = element.get("endIndex")
    if start is None or end is None:
        return []
    requests: list[dict] = []
    # Keep the trailing newline (end - 1) so the paragraph and its style remain.
    if end - 1 > start:
        requests.append(
            {"deleteContentRange": {"range": {"startIndex": start, "endIndex": end - 1}}}
        )
    if new_text:
        requests.append(
            {"insertText": {"location": {"index": start}, "text": new_text}}
        )
    return requests


def apply_replacements(
    service: Any,
    doc_id: str,
    replacements: Mapping[str, str],
    match_case: bool = True,
) -> int:
    """Apply ``replaceAllText`` edits to a document.

    Arguments:
        service: Docs service client.
        doc_id: Target document id.
        replacements: Mapping of existing text -> replacement text.
        match_case: Whether matching is case-sensitive.
    Returns:
        The number of replacement requests submitted.
    """
    requests = [
        {
            "replaceAllText": {
                "containsText": {"text": old, "matchCase": match_case},
                "replaceText": new,
            }
        }
        for old, new in replacements.items()
    ]
    if not requests:
        return 0  # EARLY EXIT: nothing to do.
    service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()
    return len(requests)


def estimate_page_count(service: Any, doc_id: str) -> float:
    """Estimate page count from the document's end index.

    NOTE: The Docs API does not expose page count; this is a rough character-based
        heuristic (~5000 chars/page).
    """
    doc = service.documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])
    if not content:
        return 0.0
    end_index = content[-1].get("endIndex", 0)
    return end_index / CHARS_PER_PAGE


def verify_page_count(
    service: Any,
    doc_id: str,
    max_pages: int = 3,
    logger: logging.Logger | None = None,
) -> bool:
    """Return True if the document is estimated to be within ``max_pages``."""
    _logger = logger or logging.getLogger(__name__)
    estimated = estimate_page_count(service, doc_id)
    _logger.info("Estimated pages: %.1f", estimated)
    if estimated > max_pages + PAGE_BUFFER:
        _logger.warning("Document may exceed %d pages", max_pages)
        return False
    return True


# __END__
