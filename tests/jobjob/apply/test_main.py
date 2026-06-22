#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from unittest import TestCase, mock

import jobjob.apply.__main__ as MOD
from jobjob.config import GoogleSettings, Settings
from jobjob.structure.applicant import Applicant

LOGGER = logging.getLogger(__name__)


def _settings(**kwargs) -> Settings:
    defaults = {
        "applicant": Applicant(name="J. Doe"),
        "anthropic_api_key": "test-key",
        "cache_enabled": True,
        "google": GoogleSettings(template_id="TPL", applications_folder_id="FOLDER"),
    }
    defaults.update(kwargs)
    return Settings(**defaults)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestParseArgs(ThisTestCase):
    """Test function."""

    def test_parses_flags(self) -> None:
        args = MOD.parse_args(["jd.pdf", "-o", "out", "--skip-drive", "--no-cache"])
        self.assertEqual(Path("jd.pdf"), args.job_description)
        self.assertEqual(Path("out"), args.output)
        self.assertTrue(args.skip_drive)
        self.assertTrue(args.no_cache)


class TestMain(ThisTestCase):
    """Test function."""

    def test_invokes_workflow_with_injected_settings(self) -> None:
        with mock.patch.object(MOD, "load_settings", return_value=_settings()):
            with mock.patch.object(
                MOD,
                "apply_inputs",
                return_value={"processed": 1, "skipped": 0, "failed": 0},
            ) as mock_run:
                retcode = MOD.main(
                    ["jd.pdf", "--skip-drive", "--no-cache", "-o", "out"]
                )

        args, kwargs = mock_run.call_args
        with self.subTest("returns 0"):
            self.assertEqual(0, retcode)
        with self.subTest("forwards input path + flags"):
            self.assertEqual(Path("jd.pdf"), args[0])
            self.assertEqual(Path("out"), kwargs["output_dir"])
            self.assertTrue(kwargs["skip_drive"])
            self.assertFalse(kwargs["use_cache"])
        with self.subTest("injects applicant + google ids from settings"):
            self.assertEqual("J. Doe", kwargs["applicant"].name)
            self.assertEqual("TPL", kwargs["template_id"])
            self.assertEqual("FOLDER", kwargs["parent_id"])

    def test_reprocess_uses_jd_parent_dir_and_reuses_folder(self) -> None:
        from pathlib import Path as _Path
        from tempfile import TemporaryDirectory

        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = _Path(tmp.name)
        (out / "summary.json").write_text('{"folder_id": "FID123"}')
        jd = out / "JD_Acme_Engineer.pdf"
        jd.write_text("pdf")

        with mock.patch.object(MOD, "load_settings", return_value=_settings()):
            with mock.patch.object(MOD, "run_application_workflow") as mock_run:
                MOD.main([str(jd), "--reprocess", "--skip-drive"])

        _, kwargs = mock_run.call_args
        self.assertEqual(out, kwargs["output_dir"])
        self.assertEqual("FID123", kwargs["reuse_folder_id"])

    def test_clear_cache_when_requested(self) -> None:
        with mock.patch.object(MOD, "load_settings", return_value=_settings()):
            with mock.patch.object(
                MOD,
                "apply_inputs",
                return_value={"processed": 1, "skipped": 0, "failed": 0},
            ):
                with mock.patch.object(MOD, "clear_cache") as mock_clear:
                    MOD.main(["jd.pdf", "--skip-drive", "--clear-cache"])
        mock_clear.assert_called_once()


# __END__
