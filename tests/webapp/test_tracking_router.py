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
    app.state.settings = {"applications_local_dir": str(mirror)}
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
        assert on_disk["notes"] == []

    def test_unknown_status_rejected(self, client):
        resp = _patch(client, _FOLDER, "BOGUS")
        assert resp.status_code == 422

    def test_missing_folder_404(self, client):
        resp = _patch(client, "2026-01-09 - Nope - Role", "APPLIED")
        assert resp.status_code == 404

    @pytest.mark.parametrize(
        "name", ["..", "../etc", "a/b", "a\\b", ".hidden", ""]
    )
    def test_traversal_names_rejected(self, client, name):
        resp = _patch(client, name, "APPLIED")
        assert resp.status_code in (400, 404, 405)  # 404/405: route mismatch

    def test_mirror_unconfigured_400(self, mirror):
        app = FastAPI()
        app.include_router(router, prefix="/api/tracking")
        app.state.settings = {"applications_local_dir": None}
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
