#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jobjob.apply.output.cover_letter_docx import create_cover_letter_docx
from jobjob.apply.output.cover_letter_pdf import create_cover_letter_pdf
from jobjob.structure.applicant import Applicant

LOGGER = logging.getLogger(__name__)

BODY = (
    "Dear Acme Hiring Manager,\n\nFirst paragraph.\n\n"
    "Second paragraph.\n\nSincerely,\n\nJ. Doe"
)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def get_tmpdir(self) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)


class TestCreateCoverLetterPdf(ThisTestCase):
    """Test function."""

    def test_writes_nonempty_pdf(self) -> None:
        out = Path(self.get_tmpdir(), "cl.pdf")
        result = create_cover_letter_pdf(
            BODY,
            out,
            role_title="Engineer",
            company_name="Acme",
            applicant=Applicant(),
        )
        self.assertEqual(out, result)
        self.assertTrue(out.is_file())
        self.assertGreater(out.stat().st_size, 0)


class TestCreateCoverLetterDocx(ThisTestCase):
    """Test function."""

    def test_writes_nonempty_docx(self) -> None:
        out = Path(self.get_tmpdir(), "cl.docx")
        result = create_cover_letter_docx(
            BODY,
            out,
            role_title="Engineer",
            company_name="Acme",
            applicant=Applicant(),
        )
        self.assertEqual(out, result)
        self.assertTrue(out.is_file())
        self.assertGreater(out.stat().st_size, 0)


# __END__
