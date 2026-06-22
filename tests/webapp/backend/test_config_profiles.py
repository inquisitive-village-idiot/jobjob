#!/usr/bin/env python3
"""Tests for the scoped config API and the profiles API (minimal app, no CSRF)."""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jobjob.loader.profiles import Profile
from routers import config as config_router
from routers import profiles as profiles_router


@pytest.fixture
def client(tmp_path, monkeypatch):
    app_cfg = tmp_path / "config" / ".env"
    app_cfg.parent.mkdir(parents=True)
    app_cfg.write_text('CLAUDE_MODEL="m"\nAPPLICATIONS_FOLDER_ID="F"\n')
    repo = tmp_path / "jobjob-resources-demo"
    (repo / "config").mkdir(parents=True)
    prof_cfg = repo / "config" / ".profile"
    prof_cfg.write_text('APPLICANT_NAME="Ada"\nRESUME_TEMPLATE_ID="T"\n')

    app = FastAPI()
    app.include_router(config_router.router, prefix="/api/config")
    app.include_router(profiles_router.router, prefix="/api/profiles")
    app.state.app_config_path = app_cfg
    app.state.profile_config_path = prof_cfg
    app.state.profile_name = "demo"
    app.state.profiles = {
        "demo": Profile("demo", repo, read_only=False, owned=True),
        "ic": Profile("ic", tmp_path / "ic", read_only=False, owned=False),
    }

    def _reload():
        app.state.profile_name = os.environ.get(
            "JOBJOB_ACTIVE_PROFILE", app.state.profile_name
        )

    app.state.reload_state = _reload
    monkeypatch.setattr(profiles_router, "write_config", lambda *a, **k: None)
    return TestClient(app)


class TestScopedConfig:
    def test_app_scope_excludes_profile_keys(self, client):
        body = client.get("/api/config", params={"scope": "app"}).json()
        assert "CLAUDE_MODEL" in body
        assert "APPLICANT_NAME" not in body and "RESUME_TEMPLATE_ID" not in body

    def test_profile_scope_has_applicant(self, client):
        body = client.get("/api/config", params={"scope": "profile"}).json()
        assert set(body) >= {"APPLICANT_NAME", "RESUME_TEMPLATE_ID"}
        assert body["APPLICANT_NAME"]["value"] == "Ada"

    def test_cross_scope_write_rejected(self, client):
        r = client.put(
            "/api/config",
            params={"scope": "app"},
            json={"updates": {"APPLICANT_NAME": "X"}},
        )
        assert r.status_code == 400

    def test_unknown_scope_400(self, client):
        assert client.get("/api/config", params={"scope": "bogus"}).status_code == 400


class TestProfiles:
    def test_list(self, client):
        body = client.get("/api/profiles").json()
        assert body["active"] == "demo"
        assert sorted(body["profiles"]) == ["demo", "ic"]

    def test_switch_known(self, client):
        r = client.put("/api/profiles/active", json={"name": "ic"})
        assert r.status_code == 200
        assert r.json()["active"] == "ic"

    def test_switch_unknown_400(self, client):
        assert (
            client.put("/api/profiles/active", json={"name": "ghost"}).status_code
            == 400
        )
