#!/usr/bin/env python3
"""Tests for services.dedup_service (application-identity, phase 6c dedup)."""

from services import application_metadata
from services import dedup_service as MOD

_META = application_metadata.METADATA_FILENAME


class TestMergeApplications:
    def test_absorbs_losers_root_execution(self, tmp_path):
        survivor = tmp_path / "2026-01-01 - Acme - Engineer"
        survivor.mkdir()
        loser = tmp_path / "2026-01-02 - Acme Inc - Engineer"
        loser.mkdir()
        (loser / "summary.json").write_text("loser-current")

        result = MOD.merge_applications(survivor, loser)

        archived = list((survivor / "archive").iterdir())
        assert len(archived) == 1
        assert (archived[0] / "summary.json").read_text() == "loser-current"
        assert result["merged_artifacts"] == 1

    def test_reparents_losers_already_archived_executions(self, tmp_path):
        survivor = tmp_path / "2026-01-01 - Acme - Engineer"
        survivor.mkdir()
        loser = tmp_path / "2026-01-02 - Acme Inc - Engineer"
        (loser / "archive" / "ts-old").mkdir(parents=True)
        (loser / "archive" / "ts-old" / "summary.json").write_text("old")

        MOD.merge_applications(survivor, loser)

        assert (survivor / "archive" / "ts-old" / "summary.json").read_text() == "old"

    def test_unions_notes_into_survivor(self, tmp_path):
        survivor = tmp_path / "2026-01-01 - Acme - Engineer"
        survivor.mkdir()
        application_metadata.write_status(
            survivor, application_metadata.ApplicationStatus.APPLIED
        )
        loser = tmp_path / "2026-01-02 - Acme Inc - Engineer"
        loser.mkdir()
        application_metadata.add_note(loser, "recruiter reached out on the dup posting")

        MOD.merge_applications(survivor, loser)

        notes = application_metadata.read_notes(survivor)
        texts = [n["text"] for n in notes]
        assert "recruiter reached out on the dup posting" in texts

    def test_survivor_id_and_status_untouched(self, tmp_path):
        survivor = tmp_path / "2026-01-01 - Acme - Engineer"
        survivor.mkdir()
        survivor_id = application_metadata.ensure_entity_id(survivor)
        application_metadata.write_status(
            survivor, application_metadata.ApplicationStatus.INTERVIEWING
        )
        loser = tmp_path / "2026-01-02 - Acme Inc - Engineer"
        loser.mkdir()
        application_metadata.ensure_entity_id(loser)

        MOD.merge_applications(survivor, loser)

        meta = application_metadata.read_metadata(survivor)
        assert meta["entity_id"] == survivor_id
        assert meta["status"] == "INTERVIEWING"

    def test_loser_folder_is_removed(self, tmp_path):
        survivor = tmp_path / "2026-01-01 - Acme - Engineer"
        survivor.mkdir()
        loser = tmp_path / "2026-01-02 - Acme Inc - Engineer"
        loser.mkdir()

        MOD.merge_applications(survivor, loser)

        assert not loser.exists()

    def test_no_notes_on_loser_is_a_no_op_for_notes(self, tmp_path):
        survivor = tmp_path / "2026-01-01 - Acme - Engineer"
        survivor.mkdir()
        loser = tmp_path / "2026-01-02 - Acme Inc - Engineer"
        loser.mkdir()

        result = MOD.merge_applications(survivor, loser)

        assert result["notes_added"] == 0
        assert not (survivor / _META).exists()


class TestDeleteApplication:
    def test_removes_the_folder(self, tmp_path):
        folder = tmp_path / "2026-01-01 - Acme - Engineer"
        folder.mkdir()
        (folder / "summary.json").write_text("x")

        MOD.delete_application(folder)

        assert not folder.exists()
