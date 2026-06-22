#!/usr/bin/env python3
"""Render a cover-letter body to a professional PDF via reportlab."""

from datetime import datetime
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from jobjob.structure.applicant import Applicant


def create_cover_letter_pdf(
    text: str,
    output_path: Path,
    role_title: str,
    company_name: str,
    applicant: Applicant,
) -> Path:
    """Write ``text`` as a formatted cover-letter PDF.

    Arguments:
        text: The cover-letter body (paragraphs separated by blank lines).
        output_path: Destination PDF path.
        role_title: Role title (used in metadata and the RE line).
        company_name: Company name (used in metadata).
        applicant: Applicant identity for the header.
    Returns:
        The output path.
    """
    output_path = Path(output_path)
    name = applicant.name or ""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title=f"Cover Letter - {role_title}",
        author=name,
        subject=f"Application for {role_title} at {company_name}",
        creator="Microsoft Word",
        producer="Microsoft Word",
    )

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "Name",
        parent=styles["Normal"],
        fontSize=12,
        leading=14,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    contact_style = ParagraphStyle(
        "Contact", parent=styles["Normal"], fontSize=10, leading=12, alignment=TA_LEFT
    )
    date_style = ParagraphStyle(
        "Date", parent=styles["Normal"], fontSize=11, leading=14, alignment=TA_LEFT
    )
    subject_style = ParagraphStyle(
        "Subject",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )
    # Left-aligned: full justification produces uneven word spacing at this
    # column width, which reads worse than a ragged right edge.
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceAfter=12,
    )

    story = [
        Paragraph(name, name_style),
        Paragraph(applicant.contact_line(), contact_style),
        Spacer(1, 0.15 * inch),
        Paragraph(datetime.now().strftime("%B %d, %Y"), date_style),
        Spacer(1, 0.15 * inch),
        Paragraph(f"RE: {role_title}", subject_style),
        Spacer(1, 0.15 * inch),
    ]
    for para in text.strip().split("\n\n"):
        if para.strip():
            story.append(Paragraph(para.replace("\n", " ").strip(), body_style))

    doc.build(story)
    return output_path


# __END__
