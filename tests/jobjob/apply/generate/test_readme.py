#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import jobjob.apply.generate.readme as MOD
from jobjob.structure.fit import BAND_MODERATE, BAND_STRONG, BAND_WEAK
from jobjob.structure.job_decription import JobDescription

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def get_tmpdir(self) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)

    def make_job(self, **kwargs) -> JobDescription:
        defaults = {
            f: ""
            for f in (
                "company_name",
                "role_title",
                "department",
                "seniority_level",
                "salary",
                "hiring_manager",
                "summary",
            )
        }
        defaults.update(
            {
                f: ()
                for f in (
                    "location",
                    "key_requirements",
                    "responsibilities",
                    "technical_skills",
                    "soft_skills",
                    "keywords",
                )
            }
        )
        defaults.update(kwargs)
        return JobDescription(**defaults)


class TestAssessFit(ThisTestCase):
    """Test function."""

    def test_strong_when_no_gaps(self) -> None:
        skills = {"critical_gaps": [], "critical_supported": [{"skill": "Python"}]}
        fit = MOD.assess_fit(skills)
        self.assertEqual(BAND_STRONG, fit.band)
        self.assertIn("Python", fit.summary)

    def test_moderate_with_few_gaps(self) -> None:
        skills = {"critical_gaps": [{"skill": "Rust"}, {"skill": "Go"}]}
        self.assertEqual(BAND_MODERATE, MOD.assess_fit(skills).band)

    def test_weak_with_many_gaps(self) -> None:
        skills = {"critical_gaps": [{"skill": "a"}, {"skill": "b"}, {"skill": "c"}]}
        self.assertEqual(BAND_WEAK, MOD.assess_fit(skills).band)

    def test_placeholder_scores_are_none(self) -> None:
        fit = MOD.assess_fit({"critical_gaps": []})
        self.assertIsNone(fit.role_fit)
        self.assertIsNone(fit.preference_fit)

    def test_weak_with_any_blocking_gap(self) -> None:
        skills = {
            "critical_gaps": [{"skill": "Rust", "severity": "blocking"}],
            "critical_supported": [{"skill": s} for s in "abcdefgh"],
        }
        self.assertEqual(BAND_WEAK, MOD.assess_fit(skills).band)

    def test_strong_when_only_aspirational_gaps(self) -> None:
        skills = {
            "critical_gaps": [{"skill": "Quantum", "severity": "aspirational"}],
            "critical_supported": [{"skill": "Python"}],
        }
        fit = MOD.assess_fit(skills)
        self.assertEqual(BAND_STRONG, fit.band)
        self.assertEqual(("Quantum (aspirational)",), fit.weaknesses)

    def test_moderate_when_support_outweighs_stretch_gaps(self) -> None:
        # Many stretch gaps would read Weak alone, but heavy supporting
        # evidence (>= 2x) keeps the band at Moderate.
        skills = {
            "critical_gaps": [
                {"skill": s, "severity": "stretch"} for s in ("a", "b", "c", "d")
            ],
            "critical_supported": [{"skill": s} for s in "abcdefgh"],
        }
        self.assertEqual(BAND_MODERATE, MOD.assess_fit(skills).band)

    def test_strengths_and_weaknesses_are_structured(self) -> None:
        skills = {
            "critical_gaps": [{"skill": "Rust"}],
            "critical_supported": [{"skill": "Python"}],
            "important_supported": [{"skill": "Docs"}],
        }
        fit = MOD.assess_fit(skills)
        self.assertEqual(("Python", "Docs"), fit.strengths)
        self.assertEqual(("Rust",), fit.weaknesses)


class TestGenerateApplicationReadme(ThisTestCase):
    """Test function."""

    def test_writes_nonempty_docx(self) -> None:
        job = self.make_job(company_name="Acme", role_title="Engineer")
        skills = {
            "critical_gaps": [
                {"skill": "Rust", "why_critical": "x", "mitigation": "y"}
            ],
            "critical_supported": [{"skill": "Python", "evidence": "resume"}],
            "important_supported": [],
            "strong_supporting": [],
        }
        out = Path(self.get_tmpdir(), "readme.docx")
        result = MOD.generate_application_readme(
            job,
            skills,
            out,
            issues=["parse warning"],
            template_name="features_writer",
            template_archetype="Features Writer",
            resume_changes=["Swapped objective for the role"],
        )
        self.assertEqual(out, result)
        self.assertTrue(out.is_file())
        self.assertGreater(out.stat().st_size, 0)

    def test_renders_template_and_two_column_fit(self) -> None:
        """README shows the template, its changes, and a Strengths/Weaknesses table."""
        from docx import Document as DocxDocument

        job = self.make_job(company_name="Acme", role_title="Engineer")
        skills = {
            "critical_gaps": [{"skill": "Rust"}],
            "critical_supported": [{"skill": "Python"}],
        }
        out = Path(self.get_tmpdir(), "readme.docx")
        MOD.generate_application_readme(
            job,
            skills,
            out,
            template_name="features_writer",
            template_archetype="Features Writer",
            resume_changes=["Objective swap"],
        )
        doc = DocxDocument(str(out))
        text = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("features_writer", text)
        self.assertIn("Features Writer", text)
        self.assertIn("Objective swap", text)
        # Strengths/Weaknesses rendered as a two-column table.
        self.assertTrue(doc.tables, "expected a fit table")
        header = [c.text for c in doc.tables[0].rows[0].cells]
        self.assertEqual(["Strengths", "Weaknesses"], header)
        table_text = "\n".join(c.text for r in doc.tables[0].rows for c in r.cells)
        self.assertIn("Python", table_text)
        self.assertIn("Rust", table_text)


# __END__
