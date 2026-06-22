#!/usr/bin/env python3
"""Test."""

import json
import logging
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

import jobjob.enrich.workflow as MOD
from jobjob.ailib.client.anthropic import AnthropicAdapter
from jobjob.ailib.session import AIClient
from tests.fixtures import fixture_path

LOGGER = logging.getLogger(__name__)


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(
            input_tokens=1,
            output_tokens=1,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
    )


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_query_service(self) -> AIClient:
        payload = json.dumps(
            {"name": "Jane Doe", "role": "VP", "company": "Acme", "location": "Boston"}
        )
        sdk = mock.MagicMock()
        sdk.messages.create.return_value = _response(payload)
        return AIClient(AnthropicAdapter(model="claude-sonnet-4-6", _client=sdk))

    def jd_pdf(self):
        # NOTE: any real PDF works as input — the model call is mocked.
        return fixture_path("job_description_acme")


class TestEnrichProfile(ThisTestCase):
    """Test function."""

    def test_dry_run_parses_without_writing(self) -> None:
        creds = mock.MagicMock()
        sheets = mock.MagicMock()
        results = MOD.enrich_profile(
            self.jd_pdf(),
            query_service=self.make_query_service(),
            dry_run=True,
            use_cache=False,
            _credentials_loader=creds,
            _sheets_builder=sheets,
        )
        self.assertEqual("Jane Doe", results["profile"]["name"])
        self.assertNotIn("row", results)
        creds.assert_not_called()
        sheets.assert_not_called()

    def test_writes_to_sheet_when_not_dry_run(self) -> None:
        service = mock.MagicMock()
        get_call = service.spreadsheets.return_value.values.return_value.get
        get_call.return_value.execute.return_value = {
            "values": [["location", "company", "role", "name", "linkedin_url"]]
        }
        results = MOD.enrich_profile(
            self.jd_pdf(),
            query_service=self.make_query_service(),
            spreadsheet_id="SHEET",
            use_cache=False,
            _credentials_loader=mock.MagicMock(),
            _sheets_builder=mock.MagicMock(return_value=service),
        )
        with self.subTest("row recorded"):
            self.assertEqual("Jane Doe", results["row"][3])
        with self.subTest("append called"):
            service.spreadsheets.return_value.values.return_value.append.assert_called_once()

    def test_requires_sheet_id_when_writing(self) -> None:
        with self.assertRaisesRegex(ValueError, "spreadsheet id is required"):
            MOD.enrich_profile(
                self.jd_pdf(),
                query_service=self.make_query_service(),
                spreadsheet_id=None,
                use_cache=False,
            )


class TestEnrichInputs(TestCase):
    """Test the directory-aware enrich entry point."""

    def make_dir(self, names) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name in names:
            Path(tmp.name, name).write_text("x")
        return Path(tmp.name)

    def test_directory_enriches_only_profiles(self) -> None:
        folder = self.make_dir(["a-linkedin-in.pdf", "job.pdf", "notes.txt"])

        def fake_classify(path, **_) -> str:
            if "linkedin" in path.name:
                return MOD.LINKEDIN_PROFILE
            return "jd" if "job" in path.name else "unsupported"

        with mock.patch.object(MOD, "enrich_profile") as enrich:
            summary = MOD.enrich_inputs(
                folder,
                query_service=mock.MagicMock(),
                spreadsheet_id="SHEET",
                _classify=fake_classify,
            )

        self.assertEqual(1, summary["processed"])
        self.assertEqual(2, summary["skipped"])
        self.assertEqual(0, summary["failed"])
        enrich.assert_called_once()
        self.assertIn("linkedin", enrich.call_args.args[0].name)

    def test_continues_past_a_failure(self) -> None:
        folder = self.make_dir(["p1-linkedin-in.pdf", "p2-linkedin-in.pdf"])
        with mock.patch.object(
            MOD, "enrich_profile", side_effect=[RuntimeError("boom"), None]
        ):
            summary = MOD.enrich_inputs(
                folder,
                query_service=mock.MagicMock(),
                spreadsheet_id="SHEET",
                _classify=lambda path, **_: MOD.LINKEDIN_PROFILE,
            )
        self.assertEqual(1, summary["processed"])
        self.assertEqual(1, summary["failed"])

    def test_single_file_skips_classification(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        single = Path(tmp.name, "whatever.pdf")
        single.write_text("x")
        classify = mock.MagicMock()

        with mock.patch.object(MOD, "enrich_profile") as enrich:
            summary = MOD.enrich_inputs(
                single,
                query_service=mock.MagicMock(),
                spreadsheet_id="SHEET",
                _classify=classify,
            )

        self.assertEqual(1, summary["processed"])
        enrich.assert_called_once()
        classify.assert_not_called()  # an explicitly-named file isn't filtered.

    def test_missing_path_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            MOD.enrich_inputs(Path("/no/such/path"), query_service=mock.MagicMock())


class TestEnrichInputsMove(TestCase):
    """Test that a completed profile is moved out of the input area."""

    def get_tmpdir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def _run_with(self, *, data_dir, dry_run, src_name="profile.pdf"):
        data = self.get_tmpdir()
        src = data / "profiles" / src_name
        src.parent.mkdir(parents=True)
        src.write_text("x")
        with mock.patch.object(
            MOD,
            "enrich_profile",
            return_value={"profile": {"name": "Jane Doe", "company": "Acme"}},
        ):
            MOD.enrich_inputs(
                src,
                query_service=mock.MagicMock(),
                spreadsheet_id="SHEET",
                data_dir=data_dir if data_dir != "self" else data,
                dry_run=dry_run,
            )
        return data, src

    def test_moves_profile_into_completed_on_success(self) -> None:
        data, src = self._run_with(data_dir="self", dry_run=False)
        self.assertFalse(src.exists())  # moved out of the input area
        moved = list((data / "completed" / "profiles").glob("*.pdf"))
        self.assertEqual(1, len(moved))
        # <created8>-<processed8>-<Company>-<Person>; no date in filename → mtime.
        self.assertRegex(moved[0].name, r"^\d{8}-\d{8}-Acme-JaneDoe\.pdf$")

    def test_writes_sidecar_with_parsed_profile(self) -> None:
        data, _ = self._run_with(data_dir="self", dry_run=False)
        moved = list((data / "completed" / "profiles").glob("*.pdf"))[0]
        sidecar = moved.with_suffix(".json")
        self.assertTrue(sidecar.exists())
        record = json.loads(sidecar.read_text())
        with self.subTest("keeps the original spaced name"):
            self.assertEqual("Jane Doe", record["name"])
        with self.subTest("records both dates"):
            self.assertIn("date_created", record)
            self.assertIn("date_processed", record)

    def test_created_date_taken_from_filename(self) -> None:
        data = self.get_tmpdir()
        src = (
            data / "profiles" / "screencapture-linkedin-in-jane-2026-05-21-09_33_56.pdf"
        )
        src.parent.mkdir(parents=True)
        src.write_text("x")
        with mock.patch.object(
            MOD,
            "enrich_profile",
            return_value={"profile": {"name": "Jane Doe", "company": "Acme"}},
        ):
            MOD.enrich_inputs(
                src,
                query_service=mock.MagicMock(),
                spreadsheet_id="SHEET",
                data_dir=data,
            )
        moved = list((data / "completed" / "profiles").glob("*.pdf"))[0]
        self.assertTrue(moved.name.startswith("20260521-"))

    def test_no_move_when_dry_run(self) -> None:
        data, src = self._run_with(data_dir="self", dry_run=True)
        self.assertTrue(src.exists())
        self.assertFalse((data / "completed").exists())

    def test_no_move_when_data_dir_unset(self) -> None:
        data, src = self._run_with(data_dir=None, dry_run=False)
        self.assertTrue(src.exists())


class TestMoveCompletedProfile(TestCase):
    """Test function."""

    def get_tmpdir(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def test_moves_and_renames_to_profile_name(self) -> None:
        data = self.get_tmpdir()
        src = data / "profiles" / "raw.pdf"
        src.parent.mkdir(parents=True)
        src.write_text("x")

        name = MOD.completed_profile_name(
            "Jane Doe", "Acme", created=date(2026, 6, 8), processed=date(2026, 6, 10)
        )
        dest = MOD.move_completed_profile(src, data, name)

        self.assertFalse(src.exists())
        self.assertTrue(dest.exists())
        self.assertEqual(
            data / "completed" / "profiles" / "20260608-20260610-Acme-JaneDoe.pdf", dest
        )

    def test_name_is_structured_pascalcased(self) -> None:
        name = MOD.completed_profile_name(
            "Jane Doe", "Acme & Co", created=date(2026, 5, 21)
        )
        # <created8>-<processed8>-<Company>-<Person>; 8-digit dates, PascalCase,
        # 4 parts.
        self.assertRegex(name, r"^20260521-\d{8}-AcmeCo-JaneDoe$")


class TestExtractFilenameDate(TestCase):
    """Test function."""

    def test_extracts_screencapture_date(self) -> None:
        name = "screencapture-linkedin-in-jane-doe-12345678-2026-05-21-09_33_56.pdf"
        self.assertEqual(date(2026, 5, 21), MOD.extract_filename_date(name))

    def test_none_when_no_date(self) -> None:
        self.assertIsNone(MOD.extract_filename_date("profile.pdf"))


# __END__
