#!/usr/bin/env python3
"""Read text from static documents (PDF, DOCX, plain text)."""

from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument

TEXT_SUFFIXES = (".txt", ".md")
SUPPORTED_SUFFIXES = (".txt", ".md", ".docx", ".pdf")


def load_pdf_text(path: Path) -> str:
    """Extract text from a PDF.

    Arguments:
        path: Path to extract from.
    Returns:
        The string content.
    Raises:
        ValueError: If no text could be extracted.
    """
    text_content = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_content += page_text + "\n"

    if not text_content.strip():
        raise ValueError(f"Could not extract text from PDF: {path}")
    return text_content


def load_pdf_text_or_none(path: Path) -> "str | None":
    """Return the PDF text, or None if none can be extracted (image-only PDF)."""
    try:
        return load_pdf_text(path)
    except ValueError:
        return None


def load_docx_text(path: Path) -> str:
    """Extract paragraph text from a DOCX file.

    Arguments:
        path: Path to the .docx file.
    Returns:
        Non-empty paragraphs joined by blank lines.
    """
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def load_text(path: Path) -> str:
    """Read a plain-text (.txt/.md) file."""
    return path.read_text(encoding="utf-8")


def read_document(path: Path) -> str:
    """Read text from a supported document, dispatching on the file suffix.

    NOTE: Returns "" for unsupported suffixes so callers can collect supported
        files from a directory and silently skip the rest.

    Arguments:
        path: Path to the document.
    Returns:
        The text content, or "" if the suffix is unsupported.
    """
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return load_text(path)
    if suffix == ".docx":
        return load_docx_text(path)
    if suffix == ".pdf":
        return load_pdf_text(path)
    return ""  # EARLY EXIT: unsupported format; skip.


# __END__
