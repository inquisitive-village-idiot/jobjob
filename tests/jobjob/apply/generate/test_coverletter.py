#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase, mock

import jobjob.apply.generate.coverletter as MOD
from jobjob.structure.applicant import Applicant
from jobjob.structure.highlight import Highlight
from jobjob.structure.job_decription import JobDescription

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_job(self, **kwargs) -> JobDescription:
        defaults = {f: "" for f in ("company_name", "role_title", "department",
                                     "seniority_level", "salary", "hiring_manager",
                                     "summary")}
        defaults.update({f: () for f in ("location", "key_requirements",
                                         "responsibilities", "technical_skills",
                                         "soft_skills", "keywords")})
        defaults.update(kwargs)
        return JobDescription(**defaults)


class TestGenerateCoverLetterText(ThisTestCase):
    """Test function."""

    def test_strips_preamble_before_dear(self) -> None:
        job = self.make_job(company_name="Acme", role_title="Engineer")
        service = mock.MagicMock(__name__="service")
        service.return_value = (
            "Here is your letter:\n\nDear Acme Hiring Manager,\n\nBody.\n\nSincerely,"
        )

        result = MOD.generate_cover_letter_text(
            job, [Highlight("a", "text")], service, Applicant(), use_cache=False
        )

        self.assertTrue(result.startswith("Dear Acme Hiring Manager,"))
        self.assertNotIn("Here is your letter", result)

    def test_resolves_company_placeholder(self) -> None:
        job = self.make_job(company_name="Acme", role_title="Engineer")
        service = mock.MagicMock(__name__="service")
        service.return_value = "Dear [Company] Hiring Manager,\n\nWe at [COMPANY]..."

        result = MOD.generate_cover_letter_text(
            job, [], service, Applicant(), use_cache=False
        )

        self.assertNotIn("[Company]", result)
        self.assertNotIn("[COMPANY]", result)
        self.assertIn("Acme", result)

    def test_does_not_json_process_text_response(self) -> None:
        # NOTE: cover letters are plain text; passing prose must not raise.
        job = self.make_job(company_name="Acme")
        service = mock.MagicMock(__name__="service")
        service.return_value = "Dear Acme Hiring Manager,\n\nNo JSON here at all."

        result = MOD.generate_cover_letter_text(
            job, [], service, Applicant(), use_cache=False
        )
        self.assertIn("No JSON here", result)


# __END__
