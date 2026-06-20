#!/usr/bin/env python3
"""Tests for the profiles lifecycle API (create/duplicate/register/delete/switch)."""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jobjob.loader.profiles import all_profiles, active_profile_name
from routers import profiles as profiles_router


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Isolate the environment registry; keep only what the test sets.
    for k in list(os.environ):
        if k.startswith("JOBJOB_"):
            monkeypatch.delenv(k, raising=False)

    cfg = tmp_path / "config" / ".env"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('CLAUDE_MODEL="m"\n')

    app = FastAPI()
    app.include_router(profiles_router.router, prefix="/api/profiles")
    app.state.app_config_path = cfg

    def _reload():
        app.state.profiles = all_profiles()
        app.state.profile_name = active_profile_name()

    app.state.reload_state = _reload
    _reload()
    return TestClient(app)


class TestList:
    def test_example_always_present(self, client):
        body = client.get("/api/profiles").json()
        assert "example" in body["profiles"]
        entries = {e["name"]: e for e in body["entries"]}
        assert entries["example"]["read_only"] is True


class TestCreate:
    def test_create_blank(self, client):
        body = client.post("/api/profiles", json={"name": "alpha"}).json()
        assert "alpha" in body["profiles"]
        entries = {e["name"]: e for e in body["entries"]}
        assert entries["alpha"]["read_only"] is False
        assert entries["alpha"]["external"] is False

    def test_create_invalid_name_400(self, client):
        assert client.post("/api/profiles", json={"name": "has-hyphen"}).status_code == 400

    def test_create_reserved_400(self, client):
        assert client.post("/api/profiles", json={"name": "example"}).status_code == 400


class TestDuplicate:
    def test_duplicate_example(self, client):
        body = client.post(
            "/api/profiles/duplicate", json={"source": "example", "name": "mine"}
        ).json()
        assert "mine" in body["profiles"]

    def test_duplicate_unknown_source_400(self, client):
        r = client.post(
            "/api/profiles/duplicate", json={"source": "ghost", "name": "mine"}
        )
        assert r.status_code == 400


class TestSwitchAndDelete:
    def test_switch_then_delete(self, client):
        client.post("/api/profiles", json={"name": "alpha"})
        client.post("/api/profiles", json={"name": "beta"})
        # switch active to alpha
        body = client.put("/api/profiles/active", json={"name": "alpha"}).json()
        assert body["active"] == "alpha"
        # cannot delete the active one
        assert client.delete("/api/profiles/alpha").status_code == 400
        # delete the inactive one
        body = client.delete("/api/profiles/beta").json()
        assert "beta" not in body["profiles"]

    def test_cannot_delete_example(self, client):
        assert client.delete("/api/profiles/example").status_code == 400


# __END__
