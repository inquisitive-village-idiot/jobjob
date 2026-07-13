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

    def test_bare_folder_defaults_to_built(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "BUILT"

    def test_legacy_generated_prefix_normalizes_to_built(self, tmp_path):
        _make_app_folder(tmp_path, "GENERATED 2026-01-03 - Gamma - Analyst")
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "BUILT"

    def test_legacy_metadata_schema_v1_generated_normalizes_to_built(self, tmp_path):
        # Integration seam (docs-tests-overview): the schema_version rename
        # shim (application_metadata._migrate, unit-tested in isolation in
        # test_application_metadata.py) must also take effect when
        # tracking_service reads a folder for the dashboard's completed
        # list — this is the actual call path a pre-full-build-rename
        # metadata.json hits, not just read_metadata() called directly.
        _make_app_folder(
            tmp_path,
            "2026-01-03 - Gamma - Analyst",
            metadata={"schema_version": 1, "status": "GENERATED"},
        )
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "BUILT"

    def test_unstamped_legacy_metadata_generated_normalizes_to_built(self, tmp_path):
        # schema_version absent entirely (pre-versioning, v0) is likewise
        # migrated when read through the same tracking-list call path.
        _make_app_folder(
            tmp_path,
            "2026-01-03 - Gamma - Analyst",
            metadata={"status": "GENERATED"},
        )
        (item,) = self._items(tmp_path)
        assert item["app_status"] == "BUILT"

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

    def test_source_json_not_counted_as_artifact(self, tmp_path):
        # source.json (application-identity phase 1) is source-tier bookkeeping,
        # not an execution artifact — same carve-out as metadata.json.
        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer", artifacts=3)
        (folder / "source.json").write_text(json.dumps({"company": "Acme"}))
        (item,) = self._items(tmp_path)
        assert item["status"] == "error"  # still incomplete: 3 real artifacts

    def test_archive_dir_not_counted_as_artifact(self, tmp_path):
        # archive/ (application-identity phase 2) holds superseded executions'
        # artifacts, not this execution's — must not inflate the count.
        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer", artifacts=3)
        archive = folder / "archive" / "2026-07-05T09.12.03"
        archive.mkdir(parents=True)
        (archive / "old_artifact_1.pdf").write_text("x")
        (archive / "old_artifact_2.pdf").write_text("x")
        (item,) = self._items(tmp_path)
        assert item["status"] == "error"  # still incomplete: 3 real artifacts

    def test_complete_folder_with_source_and_archive_present(self, tmp_path):
        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer", artifacts=4)
        (folder / "source.json").write_text(json.dumps({"company": "Acme"}))
        (folder / "archive" / "ts1").mkdir(parents=True)
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


class TestApplicationItemEntityId:
    """entity_id surfaced on completed-application items (application-identity)."""

    def _items(self, local_dir):
        with mock.patch.object(MOD, "list_application_folders", return_value=[]):
            return MOD._application_items(local_dir, None, None, None, _LOGGER)

    def test_entity_id_present_when_in_metadata(self, tmp_path):
        _make_app_folder(
            tmp_path,
            "2026-01-01 - Acme - Engineer",
            metadata={"entity_id": "e1", "status": "APPLIED"},
        )
        (item,) = self._items(tmp_path)
        expected = "e1"
        found = item["entity_id"]
        assert found == expected

    def test_entity_id_none_for_legacy_folder(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["entity_id"] is None


class TestApplicationItemPostingUrl:
    """posting_url surfaced on completed-application items (autofill-apply-wiring)."""

    def _items(self, local_dir):
        with mock.patch.object(MOD, "list_application_folders", return_value=[]):
            return MOD._application_items(local_dir, None, None, None, _LOGGER)

    def test_posting_url_from_source_json(self, tmp_path):
        from services import application_source

        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        application_source.write_source(
            folder, {"web_uri": "https://example.test/jobs/123"}
        )
        (item,) = self._items(tmp_path)
        assert item["posting_url"] == "https://example.test/jobs/123"

    def test_posting_url_none_when_no_source(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["posting_url"] is None


class TestApplicationItemExecutionCount:
    """execution_count (application-identity, phase 6b): archived executions."""

    def _items(self, local_dir):
        with mock.patch.object(MOD, "list_application_folders", return_value=[]):
            return MOD._application_items(local_dir, None, None, None, _LOGGER)

    def test_zero_when_no_archive(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["execution_count"] == 0

    def test_counts_archived_executions(self, tmp_path):
        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (folder / "archive" / "ts1").mkdir(parents=True)
        (folder / "archive" / "ts2").mkdir(parents=True)
        (item,) = self._items(tmp_path)
        assert item["execution_count"] == 2


class TestApplicationItemDedupSignal:
    """dedup_signal (phase 6c): source.json preferred over the folder name."""

    def _items(self, local_dir):
        with mock.patch.object(MOD, "list_application_folders", return_value=[]):
            return MOD._application_items(local_dir, None, None, None, _LOGGER)

    def test_prefers_source_company_role_over_folder_name(self, tmp_path):
        from services import application_source

        folder = _make_app_folder(tmp_path, "2026-01-01 - Acme Inc - Engineer")
        application_source.write_source(folder, {"company": "Acme", "role": "Engineer"})
        (item,) = self._items(tmp_path)
        assert item["dedup_signal"] == "acme|engineer"

    def test_falls_back_to_folder_name_when_no_source(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["dedup_signal"] == "acme|engineer"

    def test_none_when_company_and_title_both_blank(self, tmp_path):
        # An unparseable name still recovers the whole string as "title", so
        # this asserts the true empty-signal case: neither field yields
        # anything (a legacy folder with no source.json and a name pattern
        # that leaves company blank).
        with mock.patch.object(MOD, "_parse_app_name") as parse:
            parse.return_value = {
                "date": "",
                "company": "",
                "title": "",
                "prefix_status": None,
            }
            _make_app_folder(tmp_path, "weird")
            (item,) = self._items(tmp_path)
        assert item["dedup_signal"] is None

    def test_seeded_false_and_none_before_grouping(self, tmp_path):
        _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        (item,) = self._items(tmp_path)
        assert item["possible_duplicate"] is False
        assert item["duplicate_group"] is None


class TestFlagDuplicates:
    """_flag_duplicates (application-identity, phase 6c): listing-time grouping."""

    def _items(self, local_dir):
        with mock.patch.object(MOD, "list_application_folders", return_value=[]):
            return MOD._application_items(local_dir, None, None, None, _LOGGER)

    def test_flags_a_real_duplicate_pair(self, tmp_path):
        from services import application_source

        f1 = _make_app_folder(tmp_path, "2026-01-01 - Acme Inc - Engineer")
        application_source.write_source(
            f1, {"company": "Acme Inc.", "role": "Engineer"}
        )
        f2 = _make_app_folder(tmp_path, "2026-02-01 - Acme Incorporated - Engineer")
        application_source.write_source(
            f2, {"company": "Acme Incorporated", "role": "Engineer"}
        )

        items = self._items(tmp_path)
        MOD._flag_duplicates(items)

        assert all(i["possible_duplicate"] for i in items)
        groups = {i["duplicate_group"] for i in items}
        assert len(groups) == 1
        assert None not in groups

    def test_does_not_flag_distinct_applications(self, tmp_path):
        from services import application_source

        f1 = _make_app_folder(tmp_path, "2026-01-01 - Acme - Engineer")
        application_source.write_source(f1, {"company": "Acme", "role": "Engineer"})
        f2 = _make_app_folder(tmp_path, "2026-02-01 - Globex - Analyst")
        application_source.write_source(f2, {"company": "Globex", "role": "Analyst"})

        items = self._items(tmp_path)
        MOD._flag_duplicates(items)

        assert not any(i["possible_duplicate"] for i in items)
        assert all(i["duplicate_group"] is None for i in items)

    def test_only_annotates_does_not_remove_anything(self, tmp_path):
        # Flagging is advisory only (design D3: never auto-merge) — both
        # duplicate items must still be present afterward, just annotated.
        from services import application_source

        names = ["2026-01-01 - Acme - Engineer", "2026-02-01 - Acme - Engineer"]
        for name in names:
            f = _make_app_folder(tmp_path, name)
            application_source.write_source(f, {"company": "Acme", "role": "Engineer"})

        items = self._items(tmp_path)
        MOD._flag_duplicates(items)

        assert len(items) == 2
        assert {i["folder_name"] for i in items} == set(names)

    def test_blank_signals_never_group_together(self):
        items = [
            {"type": "jd", "dedup_signal": None, "folder_name": "a"},
            {"type": "jd", "dedup_signal": None, "folder_name": "b"},
        ]
        MOD._flag_duplicates(items)
        assert not any(i.get("possible_duplicate") for i in items)

    def test_profile_items_are_never_grouped(self):
        items = [
            {"type": "profile", "dedup_signal": "tila|mer", "folder_name": "a"},
            {"type": "profile", "dedup_signal": "tila|mer", "folder_name": "b"},
        ]
        MOD._flag_duplicates(items)
        assert not any(i.get("possible_duplicate") for i in items)


class TestRunMatchesApplication:
    """Id-preferring join across a rename, falling back to folder name."""

    def test_id_join_survives_a_rename(self):
        run = {"folder_name": "2026-01-01 - Old Name - Role", "entity_id": "e1"}
        item = {"folder_name": "2026-01-01 - New Name - Role", "entity_id": "e1"}
        assert MOD.run_matches_application(run, item) is True

    def test_id_mismatch_is_not_a_match_even_if_names_agree(self):
        run = {"folder_name": "2026-01-01 - Acme - Role", "entity_id": "e1"}
        item = {"folder_name": "2026-01-01 - Acme - Role", "entity_id": "e2"}
        assert MOD.run_matches_application(run, item) is False

    def test_legacy_falls_back_to_folder_name(self):
        run = {"folder_name": "2026-01-01 - Acme - Role", "entity_id": None}
        item = {"folder_name": "2026-01-01 - Acme - Role", "entity_id": None}
        assert MOD.run_matches_application(run, item) is True

    def test_legacy_folder_name_mismatch_is_not_a_match(self):
        run = {"folder_name": "2026-01-01 - Acme - Role", "entity_id": None}
        item = {"folder_name": "2026-01-01 - Beta - Role", "entity_id": None}
        assert MOD.run_matches_application(run, item) is False

    def test_one_sided_id_falls_back_to_name(self):
        run = {"folder_name": "2026-01-01 - Acme - Role", "entity_id": "e1"}
        item = {"folder_name": "2026-01-01 - Acme - Role"}  # no entity_id key
        assert MOD.run_matches_application(run, item) is True


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
