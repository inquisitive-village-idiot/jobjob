#!/usr/bin/env python3
"""Tests for the profiles lifecycle API (create/duplicate/register/delete/switch)."""

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jobjob.loader.profiles import active_profile_name, build_profiles
from routers import profiles as profiles_router
from services.profile_service import profiles_base


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
        app.state.profiles = build_profiles(profiles_base(cfg))
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
        assert (
            client.post("/api/profiles", json={"name": "has-hyphen"}).status_code == 400
        )

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


class TestResources:
    def test_lists_resource_dirs_with_counts(self, client):
        client.post("/api/profiles", json={"name": "alpha"})
        body = client.get("/api/profiles/alpha/resources").json()
        assert body["name"] == "alpha"
        assert body["location"]
        names = {r["name"]: r for r in body["resources"]}
        assert set(names) == {"content", "reference", "prompt"}
        assert names["content"]["dir"] == "content"

    def test_respects_renamed_dir_from_profile_config(self, client):
        client.post("/api/profiles", json={"name": "alpha"})
        loc = Path(client.get("/api/profiles/alpha/resources").json()["location"])
        # Point the profile's content dir at a renamed folder with two files.
        (loc / "creds").mkdir()
        (loc / "creds" / "a.toml").write_text("x")
        (loc / "creds" / "b.toml").write_text("y")
        (loc / "config").mkdir(exist_ok=True)
        (loc / "config" / ".profile").write_text('CONTENT_DIR="creds"\n')
        names = {
            r["name"]: r
            for r in client.get("/api/profiles/alpha/resources").json()["resources"]
        }
        assert names["content"]["dir"] == "creds"
        assert names["content"]["count"] == 2

    def test_count_skips_hidden_files(self, client):
        client.post("/api/profiles", json={"name": "alpha"})

        def ref_count() -> int:
            resources = client.get("/api/profiles/alpha/resources").json()["resources"]
            return next(r["count"] for r in resources if r["name"] == "reference")

        loc = Path(client.get("/api/profiles/alpha/resources").json()["location"])
        ref = loc / "reference"
        ref.mkdir(exist_ok=True)
        before = ref_count()
        (ref / ".DS_Store").write_text("junk")  # hidden -> not counted
        (ref / "visible.md").write_text("hi")  # +1
        assert ref_count() == before + 1

    def test_unknown_profile_400(self, client):
        assert client.get("/api/profiles/ghost/resources").status_code == 400


# __END__
