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


def _executions_url(folder):
    return f"/api/tracking/applications/{urllib.parse.quote(folder)}/executions"


def _execution_url(folder, timestamp):
    return f"{_executions_url(folder)}/{timestamp}"


class TestListApplicationExecutions:
    """GET /applications/{folder}/executions (application-identity, phase 6b)."""

    def test_empty_when_no_archive(self, client):
        resp = client.get(_executions_url(_FOLDER))
        assert resp.status_code == 200
        assert resp.json() == {"folder_name": _FOLDER, "executions": []}

    def test_lists_note_and_lock_state(self, client, mirror):
        archive = mirror / _FOLDER / "archive" / "ts1"
        archive.mkdir(parents=True)
        (archive / "summary.json").write_text("{}")

        resp = client.get(_executions_url(_FOLDER))

        assert resp.status_code == 200
        executions = resp.json()["executions"]
        assert executions == [{"timestamp": "ts1", "note": None, "locked": False}]

    def test_missing_folder_404(self, client):
        resp = client.get(_executions_url("2026-09-09 - Nope - Role"))
        assert resp.status_code == 404


class TestPromoteApplicationExecution:
    """POST .../executions/{timestamp}/promote (application-identity, phase 6b)."""

    def _seed(self, mirror):
        app_dir = mirror / _FOLDER
        (app_dir / "summary.json").write_text("current")
        archive = app_dir / "archive" / "ts-old"
        archive.mkdir(parents=True)
        (archive / "summary.json").write_text("old")
        return app_dir

    def test_promotes_and_archives_current_root_first(self, client, mirror):
        app_dir = self._seed(mirror)

        resp = client.post(f"{_execution_url(_FOLDER, 'ts-old')}/promote")

        assert resp.status_code == 200, resp.text
        assert (app_dir / "summary.json").read_text() == "old"
        # The previously-current root is now archived under a fresh timestamp,
        # not "ts-old" (which no longer exists — it's been promoted out).
        archived = {p.name for p in (app_dir / "archive").iterdir()}
        assert "ts-old" not in archived
        assert len(archived) == 1
        body = resp.json()
        assert body["executions"][0]["timestamp"] in archived

    def test_missing_execution_404(self, client, mirror):
        self._seed(mirror)
        resp = client.post(f"{_execution_url(_FOLDER, 'nope')}/promote")
        assert resp.status_code == 404

    def test_missing_folder_404(self, client):
        resp = client.post(
            f"{_execution_url('2026-09-09 - Nope - Role', 'ts1')}/promote"
        )
        assert resp.status_code == 404


class TestUpdateApplicationExecution:
    """PATCH .../executions/{timestamp} — note/lock (application-identity, phase 6b)."""

    def _seed(self, mirror, ts="ts1"):
        archive = mirror / _FOLDER / "archive" / ts
        archive.mkdir(parents=True)
        (archive / "summary.json").write_text("{}")

    def test_sets_note_and_lock(self, client, mirror):
        self._seed(mirror)

        resp = client.patch(
            _execution_url(_FOLDER, "ts1"),
            json={"note": "kept for the recruiter callback", "locked": True},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["note"] == "kept for the recruiter callback"
        assert body["locked"] is True

    def test_partial_update_preserves_other_field(self, client, mirror):
        self._seed(mirror)
        client.patch(
            _execution_url(_FOLDER, "ts1"), json={"note": "first", "locked": True}
        )

        resp = client.patch(_execution_url(_FOLDER, "ts1"), json={"note": "second"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["note"] == "second"
        assert body["locked"] is True

    def test_rejects_unknown_field(self, client, mirror):
        self._seed(mirror)
        resp = client.patch(_execution_url(_FOLDER, "ts1"), json={"bogus": "x"})
        assert resp.status_code == 422

    def test_missing_execution_404(self, client, mirror):
        resp = client.patch(_execution_url(_FOLDER, "nope"), json={"note": "x"})
        assert resp.status_code == 404


class TestPurgeApplicationExecutions:
    """DELETE .../executions (per-entity) and /executions (global), phase 6b."""

    def test_per_entity_purge_respects_lock(self, client, mirror):
        app_dir = mirror / _FOLDER
        for ts in ("ts1", "ts2"):
            (app_dir / "archive" / ts).mkdir(parents=True)
        client.patch(_execution_url(_FOLDER, "ts2"), json={"locked": True})

        resp = client.delete(_executions_url(_FOLDER))

        assert resp.status_code == 200, resp.text
        assert resp.json() == {"folder_name": _FOLDER, "purged": ["ts1"]}
        remaining = {p.name for p in (app_dir / "archive").iterdir()}
        assert remaining == {"ts2"}

    def test_global_purge_scope(self, client, mirror):
        other_folder = "2026-01-02 - Beta - Director"
        (mirror / other_folder).mkdir()
        for folder, ts in ((_FOLDER, "ts1"), (other_folder, "tsA")):
            (mirror / folder / "archive" / ts).mkdir(parents=True)

        resp = client.delete("/api/tracking/executions")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 2
        assert body["purged"] == {_FOLDER: ["ts1"], other_folder: ["tsA"]}

    def test_global_purge_respects_lock(self, client, mirror):
        app_dir = mirror / _FOLDER
        (app_dir / "archive" / "ts1").mkdir(parents=True)
        client.patch(_execution_url(_FOLDER, "ts1"), json={"locked": True})

        resp = client.delete("/api/tracking/executions")

        assert resp.status_code == 200
        assert resp.json() == {"purged": {}, "total": 0}
        assert (app_dir / "archive" / "ts1").is_dir()
