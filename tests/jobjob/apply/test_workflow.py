#!/usr/bin/env python3
"""Test."""

from tests.fixtures import fixture_dir, fixture_path
import json
import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, mock

import jobjob.apply.workflow as MOD
from jobjob.ailib.client.anthropic import AnthropicAdapter
from jobjob.ailib.session import AIClient
from jobjob.loader import location
from jobjob.structure.applicant import Applicant
from jobjob.structure.highlight import Highlight, make_highlight_set
from jobjob.structure.reference import ReferenceDocs
from jobjob.structure.template import ResumeSection, ResumeTemplate, make_template_set

LOGGER = logging.getLogger(__name__)


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=4,
        ),
    )


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def get_tmpdir(self) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)

    def make_query_service(self) -> AIClient:
        # NOTE: four responses in workflow call order — parse, highlights, cover
        #   letter, skills (template uses an explicit name, so no archetype call).
        parse_payload = json.dumps(
            {
                "company_name": "Acme",
                "role_title": "Principal Engineer",
                "key_requirements": ["Python"],
                "technical_skills": ["Python"],
                "keywords": ["python"],
            }
        )
        highlights_payload = json.dumps(["fda_class3", "team_growth_80"])
        cover_letter = "Dear Acme Hiring Manager,\n\nI am excited.\n\nSincerely,\n\nJ"
        skills_payload = json.dumps(
            {
                "critical_gaps": [],
                "critical_supported": [{"skill": "Python", "evidence": "resume"}],
                "important_supported": [],
                "strong_supporting": [],
            }
        )
        mock_sdk = mock.MagicMock()
        mock_sdk.messages.create.side_effect = [
            _response(parse_payload),
            _response(highlights_payload),
            _response(cover_letter),
            _response(skills_payload),
        ]
        adapter = AnthropicAdapter(model="claude-sonnet-4-6", _client=mock_sdk)
        return AIClient(adapter)


class TestBuildCachedContext(ThisTestCase):
    """Test function."""

    def make_set(self):
        return make_highlight_set([Highlight("py", "Python work", ("python",))])

    def test_includes_highlights_and_reference_sections(self) -> None:
        ref = ReferenceDocs(background="bg", star_examples="stars", writing_style="ws")
        context = MOD.build_cached_context(self.make_set(), ref)
        for marker in ("AVAILABLE RESUME HIGHLIGHTS", "BACKGROUND", "STAR", "WRITING STYLE"):
            with self.subTest(marker):
                self.assertIn(marker, context)

    def test_appends_resume_last_when_present(self) -> None:
        ref = ReferenceDocs()
        context = MOD.build_cached_context(self.make_set(), ref, resume_text="RESUME")
        self.assertTrue(context.rstrip().endswith("RESUME"))


class TestRunApplicationWorkflowOffline(ThisTestCase):
    """End-to-end offline (skip_drive) with a mocked Anthropic SDK."""

    def test_produces_local_artifacts_and_summary(self) -> None:
        out = self.get_tmpdir()
        jd_pdf = fixture_path("job_description_acme")

        results = MOD.run_application_workflow(
            job_description_pdf=jd_pdf,
            output_dir=out,
            skip_drive=True,
            query_service=self.make_query_service(),
            applicant=Applicant(name="J. Doe"),
            use_cache=False,
        )

        with self.subTest("cover letter PDF written"):
            self.assertTrue(Path(results["cover_letter_pdf"]).is_file())
        with self.subTest("cover letter DOCX written"):
            self.assertTrue(Path(results["cover_letter_docx"]).is_file())
        with self.subTest("skills analysis written and valid"):
            data = json.loads(Path(results["skills_analysis"]).read_text())
            self.assertIn("critical_supported", data)
        with self.subTest("job description copied"):
            self.assertTrue(Path(results["job_description_pdf"]).is_file())
        with self.subTest("summary written with token usage"):
            summary = json.loads(Path(out, "summary.json").read_text())
            self.assertEqual("Acme", summary["job_info"]["company_name"])
            self.assertIn("token_usage", summary)

    def test_writes_readme_artifact(self) -> None:
        out = self.get_tmpdir()
        jd_pdf = fixture_path("job_description_acme")
        results = MOD.run_application_workflow(
            job_description_pdf=jd_pdf,
            output_dir=out,
            skip_drive=True,
            query_service=self.make_query_service(),
            applicant=Applicant(name="J. Doe"),
            use_cache=False,
        )
        self.assertTrue(Path(results["readme"]).is_file())

    def test_does_not_authenticate_with_google_when_skipping(self) -> None:
        out = self.get_tmpdir()
        jd_pdf = fixture_path("job_description_acme")
        creds_loader = mock.MagicMock()

        MOD.run_application_workflow(
            job_description_pdf=jd_pdf,
            output_dir=out,
            skip_drive=True,
            query_service=self.make_query_service(),
            applicant=Applicant(name="J. Doe"),
            use_cache=False,
            _credentials_loader=creds_loader,
        )
        creds_loader.assert_not_called()


class TestRunApplicationWorkflowDrive(ThisTestCase):
    """Drive path with the gapi layer patched (gapi is unit-tested separately)."""

    def patch_gapi(self) -> dict:
        templates = make_template_set(
            [ResumeTemplate(name="features", archetype="B", doc_id="TPL")],
            default="features",
        )
        patches = {
            "load_templates": mock.patch.object(
                MOD, "load_templates", return_value=templates
            ),
            "tailor_resume": mock.patch.object(
                MOD,
                "tailor_resume",
                return_value=("resume text", ["Set role title", "Highlight: a → b"], []),
            ),
            "verify_page_count": mock.patch.object(
                MOD, "verify_page_count", return_value=True
            ),
            "find_application_folder": mock.patch.object(
                MOD.gdrive, "find_application_folder", return_value=None
            ),
            "create_application_folder": mock.patch.object(
                MOD.gdrive, "create_application_folder", return_value="FOLDER"
            ),
            "copy_resume_template": mock.patch.object(
                MOD.gdrive, "copy_resume_template", return_value="RESUME_ID"
            ),
            "export_doc_as_pdf": mock.patch.object(
                MOD.gdrive, "export_doc_as_pdf", side_effect=lambda *a, **k: a[2]
            ),
            "upload_docx_as_google_doc": mock.patch.object(
                MOD.gdrive, "upload_docx_as_google_doc", return_value="DOCID"
            ),
            "upload_file": mock.patch.object(
                MOD.gdrive, "upload_file", return_value="FILEID"
            ),
        }
        started = {name: patch.start() for name, patch in patches.items()}
        for patch in patches.values():
            self.addCleanup(patch.stop)
        return started

    def run_drive(self):
        out = self.get_tmpdir()
        jd_pdf = fixture_path("job_description_acme")
        return MOD.run_application_workflow(
            job_description_pdf=jd_pdf,
            output_dir=out,
            skip_drive=False,
            query_service=self.make_query_service(),
            applicant=Applicant(name="J. Doe"),
            use_cache=False,
            template_name="features",  # explicit -> no archetype API call
            _credentials_loader=mock.MagicMock(),
            _drive_builder=mock.MagicMock(),
            _docs_builder=mock.MagicMock(),
        )

    def test_reuses_folder_and_skips_self_copy_on_reprocess(self) -> None:
        mocks = self.patch_gapi()
        out = self.get_tmpdir()
        # NOTE: the input IS the JD copy inside the output dir (re-process shape).
        jd_in_out = Path(out, "JD_Acme_PrincipalEngineer.pdf")
        shutil.copy2(fixture_path("job_description_acme"), jd_in_out)

        results = MOD.run_application_workflow(
            job_description_pdf=jd_in_out,
            output_dir=out,
            skip_drive=False,
            query_service=self.make_query_service(),
            applicant=Applicant(name="J. Doe"),
            use_cache=False,
            template_name="features",
            reuse_folder_id="EXISTING_FOLDER",
            _credentials_loader=mock.MagicMock(),
            _drive_builder=mock.MagicMock(),
            _docs_builder=mock.MagicMock(),
        )

        with self.subTest("reused the given folder; did not create one"):
            self.assertEqual("EXISTING_FOLDER", results["folder_id"])
            mocks["create_application_folder"].assert_not_called()
        with self.subTest("JD still present (no self-copy error)"):
            self.assertTrue(Path(results["job_description_pdf"]).is_file())

    def test_fresh_apply_raises_overwrite_conflict_when_folder_exists(self) -> None:
        mocks = self.patch_gapi()
        # An existing folder is found for a fresh apply (no reuse, no override).
        mocks["find_application_folder"].return_value = "EXISTING"
        with self.assertRaises(MOD.OverwriteConflict):
            self.run_drive()
        mocks["create_application_folder"].assert_not_called()

    def test_allow_overwrite_proceeds_past_existing_folder(self) -> None:
        mocks = self.patch_gapi()
        mocks["find_application_folder"].return_value = "EXISTING"
        results = MOD.run_application_workflow(
            job_description_pdf=fixture_path("job_description_acme"),
            output_dir=self.get_tmpdir(),
            skip_drive=False,
            query_service=self.make_query_service(),
            applicant=Applicant(name="J. Doe"),
            use_cache=False,
            template_name="features",
            allow_overwrite=True,
            _credentials_loader=mock.MagicMock(),
            _drive_builder=mock.MagicMock(),
            _docs_builder=mock.MagicMock(),
        )
        # Override skips the conflict check and reuses/creates as normal.
        self.assertEqual("FOLDER", results["folder_id"])

    def test_copies_selected_template_and_uploads_four_artifacts(self) -> None:
        mocks = self.patch_gapi()
        results = self.run_drive()

        with self.subTest("template recorded"):
            self.assertEqual("features", results["template"])
        with self.subTest("resume copied from template doc id"):
            _, kwargs = mocks["copy_resume_template"].call_args
            args = mocks["copy_resume_template"].call_args.args
            self.assertIn("TPL", args)
        with self.subTest("folder + resume id recorded"):
            self.assertEqual("FOLDER", results["folder_id"])
            self.assertEqual("RESUME_ID", results["resume_id"])
        with self.subTest("resume tailored + changes recorded"):
            mocks["tailor_resume"].assert_called_once()
            self.assertEqual(
                ["Set role title", "Highlight: a → b"], results["resume_changes"]
            )
        with self.subTest("resume page count verified"):
            mocks["verify_page_count"].assert_called_once()
            self.assertTrue(results["resume_within_page_limit"])
        with self.subTest("README + cover letter uploaded as Google Docs"):
            names = {c.args[3] for c in mocks["upload_docx_as_google_doc"].call_args_list}
            self.assertEqual({MOD.README_NAME, MOD.COVER_LETTER_NAME}, names)
        with self.subTest("JD uploaded as a file"):
            self.assertEqual(1, mocks["upload_file"].call_count)

    def test_passes_only_enabled_sections_to_tailor_resume(self) -> None:
        mocks = self.patch_gapi()
        sections = (
            ResumeSection(heading="Objective", section="objective", enabled=True),
            ResumeSection(
                heading="Key Career Highlights", section="highlights", enabled=False
            ),
        )
        template = ResumeTemplate(
            name="features", archetype="B", doc_id="TPL", sections=sections
        )
        mocks["load_templates"].return_value = make_template_set(
            [template], default="features"
        )

        self.run_drive()

        passed = mocks["tailor_resume"].call_args.kwargs["sections"]
        with self.subTest("disabled section omitted"):
            self.assertEqual(("Objective",), tuple(s.heading for s in passed))
        with self.subTest("only enabled sections survive the filter"):
            self.assertTrue(all(s.enabled for s in passed))


class TestApplyInputs(ThisTestCase):
    """Test the directory-aware apply entry point."""

    def make_dir(self, names) -> Path:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name in names:
            Path(tmp.name, name).write_text("x")
        return Path(tmp.name)

    def test_directory_processes_only_jds(self) -> None:
        folder = self.make_dir(["job-careers.pdf", "a-linkedin-in.pdf", "notes.txt"])

        def fake_classify(path, **_) -> str:
            if "job" in path.name:
                return MOD.JD
            return "linkedin_profile" if "linkedin" in path.name else "unsupported"

        with mock.patch.object(MOD, "run_application_workflow") as run:
            summary = MOD.apply_inputs(
                folder,
                query_service=mock.MagicMock(),
                applicant=mock.MagicMock(),
                _classify=fake_classify,
            )

        self.assertEqual(1, summary["processed"])
        self.assertEqual(2, summary["skipped"])
        self.assertEqual(0, summary["failed"])
        run.assert_called_once()
        self.assertIn("job", run.call_args.args[0].name)

    def test_per_jd_output_subdir(self) -> None:
        folder = self.make_dir(["alpha.pdf", "beta.pdf"])
        out = self.get_tmpdir()

        with mock.patch.object(MOD, "run_application_workflow") as run:
            MOD.apply_inputs(
                folder,
                query_service=mock.MagicMock(),
                applicant=mock.MagicMock(),
                output_dir=out,
                _classify=lambda path, **_: MOD.JD,
            )

        out_dirs = {c.kwargs["output_dir"] for c in run.call_args_list}
        self.assertEqual({out / "alpha", out / "beta"}, out_dirs)

    def test_continues_past_a_failure(self) -> None:
        folder = self.make_dir(["a.pdf", "b.pdf"])
        with mock.patch.object(
            MOD, "run_application_workflow", side_effect=[RuntimeError("boom"), {}]
        ):
            summary = MOD.apply_inputs(
                folder,
                query_service=mock.MagicMock(),
                applicant=mock.MagicMock(),
                _classify=lambda path, **_: MOD.JD,
            )
        self.assertEqual(1, summary["processed"])
        self.assertEqual(1, summary["failed"])

    def test_single_file_skips_classification(self) -> None:
        single = self.make_dir(["jd.pdf"]) / "jd.pdf"
        classify = mock.MagicMock()

        with mock.patch.object(MOD, "run_application_workflow") as run:
            summary = MOD.apply_inputs(
                single,
                query_service=mock.MagicMock(),
                applicant=mock.MagicMock(),
                output_dir=Path("out"),
                _classify=classify,
            )

        self.assertEqual(1, summary["processed"])
        classify.assert_not_called()
        # A single file uses output_dir directly (no per-JD subdir).
        self.assertEqual(Path("out"), run.call_args.kwargs["output_dir"])

    def test_missing_path_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            MOD.apply_inputs(
                Path("/no/such/path"),
                query_service=mock.MagicMock(),
                applicant=mock.MagicMock(),
            )

    def _run_with(self, *, data_dir, skip_drive, src_name="jd.pdf"):
        data = self.get_tmpdir()
        src = data / "jobs" / src_name
        src.parent.mkdir(parents=True)
        src.write_text("x")
        with mock.patch.object(
            MOD,
            "run_application_workflow",
            return_value={"job_info": {"company_name": "Acme", "role_title": "Eng"}},
        ):
            MOD.apply_inputs(
                src,
                query_service=mock.MagicMock(),
                applicant=mock.MagicMock(),
                data_dir=data_dir if data_dir != "self" else data,
                skip_drive=skip_drive,
            )
        return data, src

    def test_moves_jd_into_completed_on_success(self) -> None:
        data, src = self._run_with(data_dir="self", skip_drive=False)
        self.assertFalse(src.exists())  # moved out of the input area
        moved = list((data / "completed" / "jobs").glob("*.pdf"))
        self.assertEqual(1, len(moved))
        self.assertIn("Acme", moved[0].name)

    def test_no_move_when_skip_drive(self) -> None:
        data, src = self._run_with(data_dir="self", skip_drive=True)
        self.assertTrue(src.exists())
        self.assertFalse((data / "completed").exists())

    def test_no_move_when_data_dir_unset(self) -> None:
        data, src = self._run_with(data_dir=None, skip_drive=False)
        self.assertTrue(src.exists())


class TestMoveCompletedJd(ThisTestCase):
    """Test function."""

    def test_moves_and_renames_to_folder_name(self) -> None:
        data = self.get_tmpdir()
        src = data / "jobs" / "raw.pdf"
        src.parent.mkdir(parents=True)
        src.write_text("x")

        dest = MOD.move_completed_jd(src, data, "2026-06-08 - Acme - Eng")

        self.assertFalse(src.exists())
        self.assertTrue(dest.exists())
        self.assertEqual(
            data / "completed" / "jobs" / "2026-06-08 - Acme - Eng.pdf", dest
        )


# __END__
