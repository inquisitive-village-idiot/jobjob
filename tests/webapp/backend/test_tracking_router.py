#!/usr/bin/env python3
"""Tests for the PATCH /api/tracking/applications/{folder}/status endpoint.

Builds a minimal FastAPI app with only the tracking router (no CSRF middleware,
no Drive-dependent startup).
"""

import json
import urllib.parse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import security
from routers.tracking import router
from services.application_metadata import METADATA_FILENAME

_FOLDER = "2026-01-01 - Acme - Engineer"


@pytest.fixture
def mirror(tmp_path):
    (tmp_path / _FOLDER).mkdir()
    security.configure_sandbox([tmp_path])
    return tmp_path


@pytest.fixture
def client(mirror):
    app = FastAPI()
    app.include_router(router, prefix="/api/tracking")
    app.state.settings = {"applications_output_dir": str(mirror)}
    return TestClient(app)


def _patch(client, folder, status):
    return client.patch(
        f"/api/tracking/applications/{urllib.parse.quote(folder)}/status",
        json={"status": status},
    )


class TestSetApplicationStatus:
    def test_happy_path_writes_metadata(self, client, mirror):
        resp = _patch(client, _FOLDER, "APPLIED")
        assert resp.status_code == 200
        body = resp.json()
        assert body["folder_name"] == _FOLDER
        assert body["app_status"] == "APPLIED"
        assert body["status_updated_at"]
        on_disk = json.loads((mirror / _FOLDER / METADATA_FILENAME).read_text())
        assert on_disk["status"] == "APPLIED"
        # The first status set is auto-logged to the changelog.
        assert len(on_disk["notes"]) == 1
        assert on_disk["notes"][0]["kind"] == "status"
        assert on_disk["notes"][0]["text"] == "Status set to APPLIED"
        assert body["note_count"] == 1

    def test_unknown_status_rejected(self, client):
        resp = _patch(client, _FOLDER, "BOGUS")
        assert resp.status_code == 422

    def test_missing_folder_404(self, client):
        resp = _patch(client, "2026-01-09 - Nope - Role", "APPLIED")
        assert resp.status_code == 404

    @pytest.mark.parametrize("name", ["..", "../etc", "a/b", "a\\b", ".hidden", ""])
    def test_traversal_names_rejected(self, client, name):
        resp = _patch(client, name, "APPLIED")
        assert resp.status_code in (400, 404, 405)  # 404/405: route mismatch

    def test_mirror_unconfigured_400(self, mirror):
        app = FastAPI()
        app.include_router(router, prefix="/api/tracking")
        app.state.settings = {"applications_output_dir": None}
        resp = _patch(TestClient(app), _FOLDER, "APPLIED")
        assert resp.status_code == 400

    def test_invalidates_completed_cache(self, client, monkeypatch):
        from services import tracking_service

        monkeypatch.setattr(
            tracking_service, "_completed_cache", {"key": "k", "items": []}
        )
        resp = _patch(client, _FOLDER, "IGNORED")
        assert resp.status_code == 200
        assert tracking_service._completed_cache is None


def _notes_url(folder):
    return f"/api/tracking/applications/{urllib.parse.quote(folder)}/notes"


class TestApplicationNotes:
    def test_get_notes_empty(self, client):
        resp = client.get(_notes_url(_FOLDER))
        assert resp.status_code == 200
        assert resp.json() == {
            "folder_name": _FOLDER,
            "app_status": None,
            "notes": [],
        }

    def test_add_note_persists_and_returns_list(self, client, mirror):
        resp = client.post(_notes_url(_FOLDER), json={"text": "recruiter reached out"})
        assert resp.status_code == 200, resp.text
        notes = resp.json()["notes"]
        assert len(notes) == 1
        assert notes[0]["kind"] == "note"
        assert notes[0]["text"] == "recruiter reached out"
        on_disk = json.loads((mirror / _FOLDER / METADATA_FILENAME).read_text())
        assert on_disk["notes"] == notes

    def test_empty_note_rejected(self, client):
        resp = client.post(_notes_url(_FOLDER), json={"text": "   "})
        assert resp.status_code == 422

    def test_status_change_shows_in_notes(self, client):
        _patch(client, _FOLDER, "APPLIED")
        resp = client.get(_notes_url(_FOLDER))
        assert resp.status_code == 200
        body = resp.json()
        assert body["app_status"] == "APPLIED"
        assert body["notes"][0]["kind"] == "status"
        assert body["notes"][0]["text"] == "Status set to APPLIED"

    def test_missing_folder_404(self, client):
        resp = client.post(_notes_url("2026-09-09 - Nope - Role"), json={"text": "x"})
        assert resp.status_code == 404


def _source_url(folder):
    return f"/api/tracking/applications/{urllib.parse.quote(folder)}/source"


class TestApplicationSource:
    """GET/PATCH /applications/{folder}/source (application-identity, phase 1)."""

    def test_get_missing_source_returns_empty_dict(self, client):
        resp = client.get(_source_url(_FOLDER))
        assert resp.status_code == 200
        assert resp.json() == {"folder_name": _FOLDER, "source": {}}

    def test_get_missing_folder_404(self, client):
        resp = client.get(_source_url("2026-09-09 - Nope - Role"))
        assert resp.status_code == 404

    def test_patch_writes_editable_fields(self, client, mirror):
        resp = client.patch(
            _source_url(_FOLDER),
            json={"company": "Acme Inc", "web_uri": "https://example.test/job"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["source"]["company"] == "Acme Inc"
        assert body["source"]["web_uri"] == "https://example.test/job"
        from services import application_source as source_mod

        on_disk = source_mod.read_source(mirror / _FOLDER)
        assert on_disk["company"] == "Acme Inc"

    def test_patch_rejects_description_field(self, client):
        resp = client.patch(_source_url(_FOLDER), json={"description": "hijack"})
        assert resp.status_code == 422

    def test_patch_rejects_entity_id_field(self, client):
        resp = client.patch(_source_url(_FOLDER), json={"entity_id": "hijack"})
        assert resp.status_code == 422

    def test_patch_missing_folder_404(self, client):
        resp = client.patch(
            _source_url("2026-09-09 - Nope - Role"), json={"company": "X"}
        )
        assert resp.status_code == 404

    def test_patch_invalidates_completed_cache(self, client, monkeypatch):
        from services import tracking_service

        monkeypatch.setattr(
            tracking_service, "_completed_cache", {"key": "k", "items": []}
        )
        resp = client.patch(_source_url(_FOLDER), json={"company": "Acme"})
        assert resp.status_code == 200
        assert tracking_service._completed_cache is None


class TestGetApplicationAts:
    def _url(self, folder):
        return f"/api/tracking/applications/{urllib.parse.quote(folder)}/ats"

    def test_returns_assessment_json(self, client, monkeypatch):
        from jobjob.apply.generate.ats import AtsAssessment
        from jobjob.apply.generate.ats_checks import AtsCheck

        assessment = AtsAssessment(
            coverage_score=0.75,
            present=("Python",),
            missing_evidenced=("SQL",),
            recommendations=("SQL is supported but absent.",),
            checks=(AtsCheck(name="content-in-tables", passed=True),),
            fit_gaps=("SQL",),
        )
        monkeypatch.setattr(
            "routers.tracking.reassess_application", lambda folder: assessment
        )

        resp = client.get(self._url(_FOLDER))

        assert resp.status_code == 200
        body = resp.json()
        assert body["coverage_score"] == 0.75
        assert body["present"] == ["Python"]
        assert body["recommendations"] == ["SQL is supported but absent."]
        # nested dataclasses arrive as JSON objects
        assert body["checks"][0] == {
            "name": "content-in-tables",
            "passed": True,
            "reason": "",
        }

    def test_missing_artifacts_409(self, client, monkeypatch):
        def _raise(folder):
            raise FileNotFoundError("Missing application artifact: summary.json")

        monkeypatch.setattr("routers.tracking.reassess_application", _raise)

        resp = client.get(self._url(_FOLDER))

        assert resp.status_code == 409
        assert "summary.json" in resp.json()["detail"]

    def test_missing_folder_404(self, client):
        resp = client.get(self._url("2026-09-09 - Nope - Role"))
        assert resp.status_code == 404
