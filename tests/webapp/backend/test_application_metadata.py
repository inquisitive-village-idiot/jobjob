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
        (tmp_path / MOD.METADATA_FILENAME).write_text(json.dumps({"status": "APPLIED"}))
        assert MOD.read_status(tmp_path) is MOD.ApplicationStatus.APPLIED

    def test_unknown_status_raises(self, tmp_path):
        (tmp_path / MOD.METADATA_FILENAME).write_text(json.dumps({"status": "BOGUS"}))
        with pytest.raises(ValueError):
            MOD.read_status(tmp_path)


class TestReadMigration:
    """Legacy GENERATED status normalizes to BUILT on read (schema v0/v1 → v2)."""

    def _write(self, folder, meta):
        (folder / MOD.METADATA_FILENAME).write_text(json.dumps(meta))

    def test_v1_generated_reads_as_built(self, tmp_path):
        self._write(tmp_path, {"schema_version": 1, "status": "GENERATED"})
        assert MOD.read_metadata(tmp_path)["status"] == "BUILT"
        assert MOD.read_status(tmp_path) is MOD.ApplicationStatus.BUILT

    def test_unstamped_generated_reads_as_built(self, tmp_path):
        # Absence of schema_version is a valid v0.
        self._write(tmp_path, {"status": "GENERATED"})
        assert MOD.read_status(tmp_path) is MOD.ApplicationStatus.BUILT

    def test_read_does_not_rewrite_source(self, tmp_path):
        self._write(tmp_path, {"schema_version": 1, "status": "GENERATED"})
        MOD.read_metadata(tmp_path)
        on_disk = json.loads((tmp_path / MOD.METADATA_FILENAME).read_text())
        assert on_disk == {"schema_version": 1, "status": "GENERATED"}

    def test_current_version_status_passes_through(self, tmp_path):
        self._write(tmp_path, {"schema_version": 2, "status": "APPLIED"})
        assert MOD.read_status(tmp_path) is MOD.ApplicationStatus.APPLIED


class TestWriteStatus:
    def test_round_trip(self, tmp_path):
        written = MOD.write_status(tmp_path, MOD.ApplicationStatus.INTERVIEWING)
        assert written["status"] == "INTERVIEWING"
        assert written["schema_version"] == 2
        # The first status set is auto-logged to the changelog.
        assert len(written["notes"]) == 1
        assert written["notes"][0]["kind"] == "status"
        assert written["notes"][0]["text"] == "Status set to INTERVIEWING"
        assert written["status_updated_at"]
        assert MOD.read_status(tmp_path) is MOD.ApplicationStatus.INTERVIEWING

    def test_preserves_unknown_keys_and_appends_transition(self, tmp_path):
        existing = {
            "status": "APPLIED",
            "notes": [
                {"ts": "2026-01-01T00:00:00+00:00", "kind": "note", "text": "hi"}
            ],
            "future_field": {"x": 1},
        }
        (tmp_path / MOD.METADATA_FILENAME).write_text(json.dumps(existing))
        written = MOD.write_status(tmp_path, MOD.ApplicationStatus.REJECTED)
        assert written["status"] == "REJECTED"
        # The pre-existing note is preserved and a transition note is appended.
        assert written["notes"][0] == existing["notes"][0]
        assert written["notes"][1]["kind"] == "status"
        assert written["notes"][1]["text"] == "Status changed from APPLIED to REJECTED"
        assert written["future_field"] == {"x": 1}
        on_disk = json.loads((tmp_path / MOD.METADATA_FILENAME).read_text())
        assert on_disk == written

    def test_same_status_does_not_log(self, tmp_path):
        MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        again = MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        # Re-setting the same status updates the timestamp but adds no changelog entry.
        assert len(again["notes"]) == 1

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


class TestStatusFromMetadata:
    def test_none_when_absent(self):
        assert MOD.status_from_metadata({}) is None

    def test_returns_status(self):
        assert (
            MOD.status_from_metadata({"status": "OFFER"}) is MOD.ApplicationStatus.OFFER
        )

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            MOD.status_from_metadata({"status": "BOGUS"})


class TestEntityId:
    """entity_id mint-once / reuse-on-rebuild (application-identity, phase 1)."""

    def test_mints_and_writes_uuid_when_absent(self, tmp_path):
        result = MOD.ensure_entity_id(tmp_path)
        assert result  # a non-empty uuid4 string
        on_disk = json.loads((tmp_path / MOD.METADATA_FILENAME).read_text())
        expected = result
        found = on_disk["entity_id"]
        assert found == expected

    def test_reuses_existing_id_without_rewriting(self, tmp_path):
        first = MOD.ensure_entity_id(tmp_path)
        mtime_before = (tmp_path / MOD.METADATA_FILENAME).stat().st_mtime_ns
        second = MOD.ensure_entity_id(tmp_path)
        expected = first
        found = second
        assert found == expected
        # Reuse is a read-only no-op: the file is not rewritten.
        mtime_after = (tmp_path / MOD.METADATA_FILENAME).stat().st_mtime_ns
        assert mtime_after == mtime_before

    def test_preserves_status_and_notes_when_minting(self, tmp_path):
        MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        entity_id = MOD.ensure_entity_id(tmp_path)
        on_disk = json.loads((tmp_path / MOD.METADATA_FILENAME).read_text())
        assert on_disk["entity_id"] == entity_id
        assert on_disk["status"] == "APPLIED"
        assert len(on_disk["notes"]) == 1

    def test_two_folders_get_different_ids(self, tmp_path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        id_a = MOD.ensure_entity_id(a)
        id_b = MOD.ensure_entity_id(b)
        assert id_a != id_b

    def test_read_entity_id_none_when_absent(self, tmp_path):
        assert MOD.read_entity_id(tmp_path) is None

    def test_read_entity_id_returns_minted_value(self, tmp_path):
        minted = MOD.ensure_entity_id(tmp_path)
        result = MOD.read_entity_id(tmp_path)
        expected = minted
        found = result
        assert found == expected

    def test_entity_id_from_metadata_ignores_blank_string(self):
        assert MOD.entity_id_from_metadata({"entity_id": ""}) is None
        assert MOD.entity_id_from_metadata({}) is None


class TestNotes:
    def test_add_note_appends_entry(self, tmp_path):
        written = MOD.add_note(tmp_path, "  recruiter call  ")
        assert len(written["notes"]) == 1
        entry = written["notes"][0]
        assert entry["kind"] == "note"
        assert entry["text"] == "recruiter call"  # trimmed
        assert entry["ts"]
        assert written["schema_version"] == 2

    def test_add_note_empty_raises(self, tmp_path):
        with pytest.raises(ValueError):
            MOD.add_note(tmp_path, "   ")

    def test_notes_accumulate_with_status_changes(self, tmp_path):
        MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        MOD.add_note(tmp_path, "phone screen scheduled")
        MOD.write_status(tmp_path, MOD.ApplicationStatus.INTERVIEWING)
        notes = MOD.read_notes(tmp_path)
        assert [n["kind"] for n in notes] == ["status", "note", "status"]

    def test_read_notes_empty_when_no_file(self, tmp_path):
        assert MOD.read_notes(tmp_path) == []


class TestUnionNotes:
    """application-identity phase 6c dedup merge: notes unioned, id/status untouched."""

    def test_appends_incoming_notes(self, tmp_path):
        MOD.add_note(tmp_path, "existing note")
        written = MOD.union_notes(
            tmp_path,
            [{"ts": "2026-01-01T00:00:00+00:00", "kind": "note", "text": "from loser"}],
        )
        texts = [n["text"] for n in written["notes"]]
        assert "existing note" in texts
        assert "from loser" in texts

    def test_sorted_by_timestamp(self, tmp_path):
        MOD.add_note(tmp_path, "second", kind="note")
        written = MOD.union_notes(
            tmp_path,
            [{"ts": "2000-01-01T00:00:00+00:00", "kind": "note", "text": "first"}],
        )
        assert [n["text"] for n in written["notes"]] == ["first", "second"]

    def test_duplicate_entry_not_re_added(self, tmp_path):
        note = {"ts": "2026-01-01T00:00:00+00:00", "kind": "note", "text": "dup"}
        MOD.union_notes(tmp_path, [note])
        written = MOD.union_notes(tmp_path, [note])
        assert len(written["notes"]) == 1

    def test_does_not_touch_entity_id_or_status(self, tmp_path):
        MOD.ensure_entity_id(tmp_path)
        MOD.write_status(tmp_path, MOD.ApplicationStatus.APPLIED)
        before = MOD.read_metadata(tmp_path)

        MOD.union_notes(
            tmp_path,
            [{"ts": "2026-02-02T00:00:00+00:00", "kind": "note", "text": "from loser"}],
        )

        after = MOD.read_metadata(tmp_path)
        assert after["entity_id"] == before["entity_id"]
        assert after["status"] == before["status"]

    def test_empty_incoming_is_a_no_op(self, tmp_path):
        MOD.add_note(tmp_path, "existing")
        written = MOD.union_notes(tmp_path, [])
        assert len(written["notes"]) == 1

    def test_no_existing_metadata_file(self, tmp_path):
        written = MOD.union_notes(
            tmp_path, [{"ts": "2026-01-01T00:00:00+00:00", "kind": "note", "text": "x"}]
        )
        assert len(written["notes"]) == 1
        assert written["schema_version"] == MOD._SCHEMA_VERSION
