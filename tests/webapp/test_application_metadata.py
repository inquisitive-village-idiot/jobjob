#!/usr/bin/env python3
"""Tests for services.application_metadata."""

import json

import pytest

from services import application_metadata as MOD


class TestReadMetadata:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        assert MOD.read_metadata(tmp_path) == {}

    def test_corrupt_json_raises(self, tmp_path):
        (tmp_path / MOD.METADATA_FILENAME).write_text("{not json")
        with pytest.raises(ValueError):
            MOD.read_metadata(tmp_path)

    def test_non_object_json_raises(self, tmp_path):
        (tmp_path / MOD.METADATA_FILENAME).write_text("[1, 2]")
        with pytest.raises(ValueError):
            MOD.read_metadata(tmp_path)


class TestReadStatus:
    def test_no_file_returns_none(self, tmp_path):
        assert MOD.read_status(tmp_path) is None

    def test_no_status_field_returns_none(self, tmp_path):
        (tmp_path / MOD.METADATA_FILENAME).write_text(json.dumps({"notes": []}))
        assert MOD.read_status(tmp_path) is None

    def test_known_status_returned(self, tmp_path):
        (tmp_path / MOD.METADATA_FILENAME).write_text(
            json.dumps({"status": "APPLIED"})
        )
        assert MOD.read_status(tmp_path) is MOD.ApplicationStatus.APPLIED

    def test_unknown_status_raises(self, tmp_path):
        (tmp_path / MOD.METADATA_FILENAME).write_text(
            json.dumps({"status": "BOGUS"})
        )
        with pytest.raises(ValueError):
            MOD.read_status(tmp_path)


class TestWriteStatus:
    def test_round_trip(self, tmp_path):
        written = MOD.write_status(tmp_path, MOD.ApplicationStatus.INTERVIEWING)
        assert written["status"] == "INTERVIEWING"
        assert written["schema_version"] == 1
        assert written["notes"] == []
        assert written["status_updated_at"]
        assert MOD.read_status(tmp_path) is MOD.ApplicationStatus.INTERVIEWING

    def test_preserves_unknown_keys_and_notes(self, tmp_path):
        existing = {
            "status": "APPLIED",
            "notes": [{"ts": "2026-01-01T00:00:00+00:00", "text": "hi"}],
            "future_field": {"x": 1},
        }
        (tmp_path / MOD.METADATA_FILENAME).write_text(json.dumps(existing))
        written = MOD.write_status(tmp_path, MOD.ApplicationStatus.REJECTED)
        assert written["status"] == "REJECTED"
        assert written["notes"] == existing["notes"]
        assert written["future_field"] == {"x": 1}
        on_disk = json.loads((tmp_path / MOD.METADATA_FILENAME).read_text())
        assert on_disk == written

    def test_updates_timestamp(self, tmp_path):
        first = MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        on_disk = json.loads((tmp_path / MOD.METADATA_FILENAME).read_text())
        assert on_disk["status_updated_at"] == first["status_updated_at"]

    def test_corrupt_existing_file_raises_and_is_not_overwritten(self, tmp_path):
        (tmp_path / MOD.METADATA_FILENAME).write_text("{not json")
        with pytest.raises(ValueError):
            MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        assert (tmp_path / MOD.METADATA_FILENAME).read_text() == "{not json"

    def test_no_temp_file_left_behind(self, tmp_path):
        MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        assert [p.name for p in tmp_path.iterdir()] == [MOD.METADATA_FILENAME]
