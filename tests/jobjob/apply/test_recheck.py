#!/usr/bin/env python3
"""Test."""

import dataclasses as dcs
import io
import json
import logging
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import jobjob.apply.recheck as MOD
from jobjob.apply.generate.ats import AtsAssessment
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.skill import Skill, SkillSet

LOGGER = logging.getLogger(__name__)


def make_job(**kwargs) -> JobDescription:
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


class FakeDocsService:
    """Stands in for the Google Docs client: documents().get(...).execute()."""

    def __init__(self, document: dict) -> None:
        self.document = document
        self.requested_ids: list[str] = []

    def documents(self) -> "FakeDocsService":
        return self

    def get(self, documentId: str) -> "FakeDocsService":  # noqa: N803 — API shape
        self.requested_ids.append(documentId)
        return self

    def execute(self) -> dict:
        return self.document


def make_docs_service(text: str) -> FakeDocsService:
    return FakeDocsService(
        {
            "body": {
                "content": [
                    {"paragraph": {"elements": [{"textRun": {"content": text}}]}}
                ]
            }
        }
    )


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_application_dir(
        self,
        job: JobDescription | None = None,
        skills: dict | None = None,
        resume_id: str = "doc-123",
        omit: tuple[str, ...] = (),
    ) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        output_dir = Path(tmpdir.name)

        job = job or make_job(
            company_name="Acme",
            role_title="Engineer",
            key_requirements=("Python",),
            canonical_skills={"Python": "Python (computer programming)"},
        )
        summary = {"job_info": dcs.asdict(job), "resume_id": resume_id}
        if MOD.SUMMARY_NAME not in omit:
            Path(output_dir, MOD.SUMMARY_NAME).write_text(
                json.dumps(summary), encoding="utf-8"
            )
        if MOD.SKILLS_NAME not in omit:
            Path(output_dir, MOD.SKILLS_NAME).write_text(
                json.dumps(skills if skills is not None else {}), encoding="utf-8"
            )
        return output_dir


class TestLoadSavedApplication(ThisTestCase):
    """Test function."""

    def test_round_trips_saved_artifacts(self) -> None:
        skills = {"critical_supported": [{"skill": "Python", "evidence": "STAR"}]}
        output_dir = self.make_application_dir(skills=skills)

        result = MOD.load_saved_application(output_dir)

        with self.subTest("job, skills, and resume id"):
            job, loaded_skills, resume_id = result
            expected = ["Acme", ("Python",), skills, "doc-123"]
            found = [
                job.company_name,
                tuple(job.key_requirements),
                loaded_skills,
                resume_id,
            ]
            self.assertEqual(expected, found)

    def test_missing_summary_names_the_file(self) -> None:
        output_dir = self.make_application_dir(omit=(MOD.SUMMARY_NAME,))
        with self.assertRaisesRegex(FileNotFoundError, MOD.SUMMARY_NAME):
            MOD.load_saved_application(output_dir)

    def test_missing_skills_names_the_file(self) -> None:
        output_dir = self.make_application_dir(omit=(MOD.SKILLS_NAME,))
        with self.assertRaisesRegex(FileNotFoundError, MOD.SKILLS_NAME):
            MOD.load_saved_application(output_dir)

    def test_summary_without_job_info_raises(self) -> None:
        output_dir = self.make_application_dir()
        Path(output_dir, MOD.SUMMARY_NAME).write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "job_info"):
            MOD.load_saved_application(output_dir)


class TestReassessApplication(ThisTestCase):
    """Test function."""

    def setUp(self) -> None:
        super().setUp()
        skill_set = SkillSet(
            skills=(
                Skill(
                    label="python",
                    text="Python",
                    canonical_id="python_computer_programming",
                    categories={"technical": 1.0},
                ),
            )
        )
        patcher = mock.patch.object(MOD, "load_skills", return_value=skill_set)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reassesses_from_saved_artifacts(self) -> None:
        skills = {"critical_supported": [{"skill": "Python", "evidence": "STAR"}]}
        output_dir = self.make_application_dir(skills=skills)
        docs = make_docs_service("Wrote Python services at scale.")

        result = MOD.reassess_application(output_dir, docs_service=docs)

        with self.subTest("fetches the saved resume id"):
            expected = ["doc-123"]
            found = docs.requested_ids
            self.assertEqual(expected, found)

        with self.subTest("assessment computed from current doc text"):
            expected = (False, 1.0)
            found = (result.skipped, result.coverage_score)
            self.assertEqual(expected, found)

    def test_drive_skipped_application_returns_skipped(self) -> None:
        output_dir = self.make_application_dir(resume_id="")
        # NOTE: no docs service supplied — must not be needed on this path.
        result = MOD.reassess_application(output_dir)

        expected = True
        found = result.skipped
        self.assertEqual(expected, found)


class TestRenderAtsReport(ThisTestCase):
    """Test function."""

    def test_renders_all_sections(self) -> None:
        from jobjob.apply.generate.ats_checks import AtsCheck

        assessment = AtsAssessment(
            coverage_score=0.64,
            present=("Python",),
            missing_evidenced=("SQL",),
            missing_unevidenced=("Kubernetes",),
            unmapped=("quantum telepathy",),
            recommendations=("SQL is supported but absent.",),
            skills_file_candidates=("Docker",),
            upskill_targets=("Kubernetes",),
            checks=(AtsCheck(name="content-in-tables", passed=False, reason="1"),),
            fit_gaps=("SQL",),
        )

        result = MOD.render_ats_report(assessment)

        for expected in (
            "Keyword coverage: 0.64",
            "Present in resume",
            "Missing (evidenced)",
            "Missing (unevidenced)",
            "Unmapped requirements",
            "Recommendations",
            "Skills-file candidates",
            "Up-skill targets",
            "Fit vs. ATS gaps",
            "content-in-tables: 1",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, result)

    def test_clean_assessment_reports_parseability_pass(self) -> None:
        result = MOD.render_ats_report(AtsAssessment(coverage_score=1.0))
        self.assertIn("all checks passed", result)

    def test_skipped_variant(self) -> None:
        result = MOD.render_ats_report(AtsAssessment(skipped=True))
        self.assertIn("skipped", result)
        self.assertNotIn("Keyword coverage", result)


class TestMain(ThisTestCase):
    """Test function (CLI)."""

    def test_prints_report_and_exits_zero(self) -> None:
        assessment = AtsAssessment(coverage_score=0.5, present=("Python",))
        with (
            mock.patch.object(MOD, "load_settings"),
            mock.patch.object(MOD, "build_credentials_loader"),
            mock.patch.object(MOD, "reassess_application", return_value=assessment),
            redirect_stdout(io.StringIO()) as captured,
        ):
            result = MOD.main(["/tmp/some-app-dir"])

        expected = 0
        found = result
        self.assertEqual(expected, found)
        self.assertIn("Keyword coverage: 0.50", captured.getvalue())

    def test_missing_artifacts_exit_nonzero(self) -> None:
        with TemporaryDirectory() as empty_dir:
            with (
                mock.patch.object(MOD, "load_settings"),
                mock.patch.object(MOD, "build_credentials_loader"),
            ):
                result = MOD.main([empty_dir])

        self.assertNotEqual(0, result)


# __END__
