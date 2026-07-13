#!/usr/bin/env python3
"""Tests for the static-content skills-suggestions route.

A minimal FastAPI app mounts only the static-content router. The applications
mirror is a tmp dir seeded with saved apply artifacts; skill resolution uses the
real packaged skill cloud ("Python" resolves canonically, as in the recheck tests).
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.static_content as sc
import security


@pytest.fixture
def apps_dir(tmp_path):
    security.configure_sandbox([tmp_path])
    apps = tmp_path / "applications"
    app_dir = apps / "2026-07-01 - Acme - Engineer"
    app_dir.mkdir(parents=True)
    (app_dir / "summary.json").write_text("{}", encoding="utf-8")
    (app_dir / "skills_analysis.json").write_text(
        json.dumps({"critical_supported": [{"skill": "Python", "evidence": "STAR A"}]}),
        encoding="utf-8",
    )
    return apps


@pytest.fixture
def client(tmp_path, apps_dir):
    app = FastAPI()
    app.include_router(sc.router, prefix="/api/static")
    app.state.repo_root = tmp_path
    app.state.profile_dir = None  # no active profile -> repo static/ (no skills.toml)
    app.state.settings = {"applications_output_dir": str(apps_dir)}
    return app, TestClient(app)


class TestSkillSuggestions:
    def test_returns_aggregated_candidates(self, client):
        _, http = client
        resp = http.get("/api/static/skills/suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert [s["canonical_id"] for s in data] == ["python_computer_programming"]
        assert data[0]["citations"][0]["application"] == "2026-07-01 - Acme - Engineer"

    def test_unconfigured_mirror_is_400(self, client):
        app, http = client
        app.state.settings = {}
        resp = http.get("/api/static/skills/suggestions")
        assert resp.status_code == 400
        assert "APPLICATIONS_OUTPUT_DIR" in resp.json()["detail"]

    def test_missing_mirror_directory_is_400(self, client):
        app, http = client
        app.state.settings = {"applications_output_dir": "/nope/never"}
        resp = http.get("/api/static/skills/suggestions")
        assert resp.status_code == 400


# __END__
