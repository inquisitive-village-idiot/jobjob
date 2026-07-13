#!/usr/bin/env python3
"""Tests for services.application_source (application-identity, phase 1)."""

import json

from services import application_source as MOD


class TestReadSource:
    def test_missing_file_returns_empty_dict(self, tmp_path):
        result = MOD.read_source(tmp_path)
        expected = {}
        assert result == expected

    def test_corrupt_json_degrades_to_empty_dict(self, tmp_path):
        (tmp_path / MOD.SOURCE_FILENAME).write_text("{not json")
        result = MOD.read_source(tmp_path)
        expected = {}
        assert result == expected

    def test_non_object_json_degrades_to_empty_dict(self, tmp_path):
        (tmp_path / MOD.SOURCE_FILENAME).write_text("[1, 2]")
        result = MOD.read_source(tmp_path)
        expected = {}
        assert result == expected

    def test_valid_source_round_trips(self, tmp_path):
        payload = {"schema_version": 1, "entity_id": "e1", "company": "Acme"}
        (tmp_path / MOD.SOURCE_FILENAME).write_text(json.dumps(payload))
        result = MOD.read_source(tmp_path)
        expected = payload
        assert result == expected


class TestEnsureSource:
    def test_writes_once_when_absent(self, tmp_path):
        found = MOD.ensure_source(
            tmp_path,
            entity_id="e1",
            company="Acme",
            role="Engineer",
            description="A role.",
            file_uri="/jd.pdf",
        )
        expected = {
            "schema_version": 1,
            "entity_id": "e1",
            "company": "Acme",
            "role": "Engineer",
            "description": "A role.",
            "file_uri": "/jd.pdf",
            "web_uri": None,
            "external_ref": None,
        }
        assert found == expected
        on_disk = json.loads((tmp_path / MOD.SOURCE_FILENAME).read_text())
        assert on_disk == expected

    def test_parse_once_rebuild_does_not_overwrite(self, tmp_path):
        MOD.ensure_source(
            tmp_path,
            entity_id="e1",
            company="Acme",
            role="Engineer",
            description="Original.",
        )
        # A "rebuild" calls ensure_source again with different parsed values —
        # the parse-once fields (and any user correction) must survive untouched.
        second = MOD.ensure_source(
            tmp_path,
            entity_id="e1",
            company="Different Co",
            role="Different Role",
            description="Different.",
        )
        expected_company = "Acme"
        found_company = second["company"]
        assert found_company == expected_company
        on_disk = json.loads((tmp_path / MOD.SOURCE_FILENAME).read_text())
        assert on_disk["description"] == "Original."

    def test_user_correction_survives_a_rebuild(self, tmp_path):
        MOD.ensure_source(
            tmp_path, entity_id="e1", company="Acme", role="Engineer", description="x"
        )
        MOD.edit_source(tmp_path, company="Acme Corrected")
        # Simulate a rebuild's ensure_source call after the user's correction.
        result = MOD.ensure_source(
            tmp_path, entity_id="e1", company="Acme", role="Engineer", description="x"
        )
        expected = "Acme Corrected"
        found = result["company"]
        assert found == expected


class TestEditSource:
    def test_updates_only_allowed_fields(self, tmp_path):
        MOD.ensure_source(
            tmp_path,
            entity_id="e1",
            company="Acme",
            role="Engineer",
            description="Original description.",
        )
        result = MOD.edit_source(
            tmp_path,
            company="Acme Inc",
            web_uri="https://example.test/job",
            description="Hijacked",  # not editable -> ignored
            entity_id="e2",  # not editable -> ignored
        )
        cases = [
            ("company", "Acme Inc"),
            ("web_uri", "https://example.test/job"),
            ("description", "Original description."),
            ("entity_id", "e1"),
        ]
        for field, expected in cases:
            found = result[field]
            assert found == expected, f"field={field}"

    def test_none_values_are_not_cleared(self, tmp_path):
        MOD.ensure_source(
            tmp_path, entity_id="e1", company="Acme", role="Engineer", description="x"
        )
        result = MOD.edit_source(tmp_path, company=None, role="Updated")
        expected = {"company": "Acme", "role": "Updated"}
        found = {"company": result["company"], "role": result["role"]}
        assert found == expected

    def test_edit_on_missing_source_creates_minimal_file(self, tmp_path):
        result = MOD.edit_source(tmp_path, company="Acme")
        expected = "Acme"
        found = result["company"]
        assert found == expected
        assert (tmp_path / MOD.SOURCE_FILENAME).is_file()


# __END__
