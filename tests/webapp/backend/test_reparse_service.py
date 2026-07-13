#!/usr/bin/env python3
"""Tests for services.reparse_service (application-identity, phase 6c)."""

import dataclasses as dcs

import pytest

from services import application_source
from services import reparse_service as MOD


@dcs.dataclass
class _FakeJob:
    company_name: str
    role_title: str
    summary: str


class TestReparseSource:
    def test_overwrites_company_role_description(self, tmp_path):
        jd = tmp_path / "jd.pdf"
        jd.write_text("jd content")
        application_source.write_source(
            tmp_path,
            {
                "entity_id": "e1",
                "company": "Old Co",
                "role": "Old Role",
                "description": "old summary",
                "file_uri": str(jd),
                "web_uri": "https://example.test/job",
                "external_ref": "REQ-1",
            },
        )
        fresh = _FakeJob(
            company_name="Acme Corp", role_title="Staff Engineer", summary="new summary"
        )

        source = MOD.reparse_source(
            tmp_path, query_service=object(), _parse=lambda *a, **k: fresh
        )

        assert source["company"] == "Acme Corp"
        assert source["role"] == "Staff Engineer"
        assert source["description"] == "new summary"

    def test_preserves_untouched_fields(self, tmp_path):
        jd = tmp_path / "jd.pdf"
        jd.write_text("jd content")
        application_source.write_source(
            tmp_path,
            {
                "entity_id": "e1",
                "company": "Old Co",
                "role": "Old Role",
                "description": "old summary",
                "file_uri": str(jd),
                "web_uri": "https://example.test/job",
                "external_ref": "REQ-1",
            },
        )
        fresh = _FakeJob(
            company_name="Acme Corp", role_title="Staff Engineer", summary="s"
        )

        source = MOD.reparse_source(
            tmp_path, query_service=object(), _parse=lambda *a, **k: fresh
        )

        assert source["entity_id"] == "e1"
        assert source["web_uri"] == "https://example.test/job"
        assert source["external_ref"] == "REQ-1"

    def test_persists_to_disk(self, tmp_path):
        jd = tmp_path / "jd.pdf"
        jd.write_text("jd content")
        application_source.write_source(
            tmp_path,
            {"entity_id": "e1", "company": "Old", "role": "Old", "file_uri": str(jd)},
        )
        fresh = _FakeJob(company_name="New Co", role_title="New Role", summary="s")

        MOD.reparse_source(
            tmp_path, query_service=object(), _parse=lambda *a, **k: fresh
        )

        on_disk = application_source.read_source(tmp_path)
        assert on_disk["company"] == "New Co"

    def test_raises_when_no_file_uri_recorded(self, tmp_path):
        application_source.write_source(tmp_path, {"entity_id": "e1", "company": "X"})
        with pytest.raises(MOD.ReparseError):
            MOD.reparse_source(tmp_path, query_service=object())

    def test_raises_when_file_uri_no_longer_exists(self, tmp_path):
        application_source.write_source(
            tmp_path,
            {"entity_id": "e1", "file_uri": str(tmp_path / "gone.pdf")},
        )
        with pytest.raises(MOD.ReparseError):
            MOD.reparse_source(tmp_path, query_service=object())

    def test_passes_use_cache_through_to_parse(self, tmp_path):
        jd = tmp_path / "jd.pdf"
        jd.write_text("x")
        application_source.write_source(tmp_path, {"file_uri": str(jd)})
        fresh = _FakeJob(company_name="Acme", role_title="Eng", summary="s")
        seen = {}

        def _parse(path, query_service, use_cache=True):
            seen["use_cache"] = use_cache
            return fresh

        MOD.reparse_source(
            tmp_path, query_service=object(), use_cache=False, _parse=_parse
        )

        assert seen["use_cache"] is False
