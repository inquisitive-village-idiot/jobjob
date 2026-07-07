#!/usr/bin/env python3
"""Tests for application-status parsing and listing in services.tracking_service."""

import json
import logging
from unittest import mock

from services import tracking_service as MOD
from services.application_metadata import METADATA_FILENAME

_LOGGER = logging.getLogger(__name__)


class TestParseAppName:
    def test_plain_name(self):
        parsed = MOD._parse_app_name("2026-01-01 - Acme - Engineer")
        assert parsed == {
            "date": "2026-01-01",
            "company": "Acme",
            "title": "Engineer",
            "prefix_status": None,
        }

    def test_applied_prefix(self):
        parsed = MOD._parse_app_name("APPLIED 2026-01-02 - Beta - Director")
        assert parsed["prefix_status"] == "APPLIED"
        assert parsed["date"] == "2026-01-02"
        assert parsed["company"] == "Beta"
        assert parsed["title"] == "Director"

    def test_ignored_prefix(self):
        parsed = MOD._parse_app_name("IGNORED 2026-01-03 - Gamma - VP")
        assert parsed["prefix_status"] == "IGNORED"
        assert parsed["date"] == "2026-01-03"
        assert parsed["company"] == "Gamma"
        assert parsed["title"] == "VP"

    def test_status_word_in_title_is_not_a_marker(self):
        parsed = MOD._parse_app_name("2026-01-04 - Delta - Applied Research Lead")
        assert parsed["prefix_status"] is None
        assert parsed["title"] == "Applied Research Lead"

    def test_unparseable_name(self):
        parsed = MOD._parse_app_name("IGNORED some folder")
        assert parsed == {
            "date": "",
            "company": "",
            "title": "some folder",
            "prefix_status": "IGNORED",
        }


def _make_app_folder(root, name, *, artifacts=4, metadata=None):
    folder = root / name
    folder.mkdir()
    for i in range(artifacts):
        (folder / f"artifact_{i}.pdf").write_text("x")
    if metadata is not None:
        (folder / METADATA_FILENAME).write_text(json.dumps(metadata))
    return folder


class TestApplicationItemsLocalMirror:
    def _items(self, local_dir):
        with mock.patch.object(MOD, "list_application_folders", return_value=[]):
            return MOD._application_items(local_dir, None, None, None, _LOGGER)

    def test_prefix_seeds_status(self, tmp_path):
        _make_app_folder(tmp_path, "APPLIED 2026-01-02 - Beta - Director")
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "APPLIED"
        assert item["status_writable"] is True

    def test_bare_folder_defaults_to_generated(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "GENERATED"

    def test_metadata_overrides_prefix(self, tmp_path):
        _make_app_folder(
            tmp_path,
            "APPLIED 2026-01-02 - Beta - Director",
            metadata={"status": "REJECTED"},
        )
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "REJECTED"

    def test_corrupt_metadata_logged_and_ignored(self, tmp_path):
        folder = _make_app_folder(tmp_path, "APPLIED 2026-01-02 - Beta - Director")
        (folder / METADATA_FILENAME).write_text("{not json")
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "APPLIED"  # falls back to the prefix

    def test_metadata_file_not_counted_as_artifact(self, tmp_path):
        _make_app_folder(
            tmp_path,
            "2026-01-01 - Acme - Engineer",
            artifacts=3,
            metadata={"status": "APPLIED"},
        )
        (item,) = self._items(tmp_path)
        assert item["status"] == "error"  # still incomplete: 3 artifacts

    def test_complete_folder_status(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer", artifacts=4)
        (item,) = self._items(tmp_path)
        assert item["status"] == "completed"

    def test_insights_read_from_summary(self, tmp_path):
        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (folder / "summary.json").write_text(
            json.dumps(
                {
                    "fit": {"band": "Strong", "role_fit": 0.72, "preference_fit": None},
                    "ats_coverage": 0.64,
                }
            )
        )
        (item,) = self._items(tmp_path)
        assert item["fit"] == {
            "band": "Strong",
            "role_fit": 0.72,
            "preference_fit": None,
        }
        assert item["ats_coverage"] == 0.64

    def test_missing_summary_degrades_to_empty_insights(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["fit"] is None
        assert item["ats_coverage"] is None

    def test_corrupt_summary_degrades_to_empty_insights(self, tmp_path):
        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (folder / "summary.json").write_text("{not json")
        (item,) = self._items(tmp_path)
        assert item["fit"] is None
        assert item["ats_coverage"] is None


class TestProfileCompletedItem:
    def test_parses_structured_filename(self, tmp_path):
        f = tmp_path / "20260521-20260612-AcmeCorp-JaneDoe.pdf"
        f.write_text("x")
        item = MOD._profile_completed_item(f)
        assert item["type"] == "profile"
        assert item["date_created"] == "2026-05-21"
        assert item["date_processed"] == "2026-06-12"
        assert item["company"] == "AcmeCorp"
        assert item["person"] == "JaneDoe"

    def test_sidecar_overrides_with_spaced_names(self, tmp_path):
        f = tmp_path / "20260521-20260612-AcmeCorp-JaneDoe.pdf"
        f.write_text("x")
        f.with_suffix(".json").write_text(
            json.dumps(
                {
                    "name": "Jane Doe",
                    "company": "Acme Corp",
                    "date_created": "2026-05-21",
                    "date_processed": "2026-06-12",
                }
            )
        )
        item = MOD._profile_completed_item(f)
        assert item["company"] == "Acme Corp"
        assert item["person"] == "Jane Doe"

    def test_legacy_name_degrades_gracefully(self, tmp_path):
        f = tmp_path / "2026-05-21 - Jane Doe - Acme.pdf"
        f.write_text("x")
        item = MOD._profile_completed_item(f)
        assert item["company"] == ""
        assert item["person"] == ""
        assert item["folder_name"] == f.stem

    def test_sheet_url_becomes_drive_link(self, tmp_path):
        f = tmp_path / "20260521-20260612-Acme-JaneDoe.pdf"
        f.write_text("x")
        item = MOD._profile_completed_item(f, sheet_url="https://sheets.test/x")
        assert item["drive"]["web_link"] == "https://sheets.test/x"


class TestApplicationItemsDriveFallback:
    def test_prefix_only_and_not_writable(self):
        folders = [
            {
                "name": "IGNORED 2026-01-03 - Gamma - VP",
                "folder_id": "abc",
                "web_link": "https://example.test/abc",
            }
        ]
        with mock.patch.object(MOD, "list_application_folders", return_value=folders):
            (item,) = MOD._application_items(None, "root", None, None, _LOGGER)
        assert item["app_status"] == "IGNORED"
        assert item["status_writable"] is False
