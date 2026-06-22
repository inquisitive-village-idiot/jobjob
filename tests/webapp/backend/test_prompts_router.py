#!/usr/bin/env python3
"""Tests for the prompt-editor API.

A minimal FastAPI app mounts only the prompts router. Overrides are sandboxed to a
profile dir under ``tmp_path``; the bundled defaults come from the real package, so the
catalog and placeholder derivation are exercised end to end.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.prompts as prompts_router
import security


@pytest.fixture
def profile(tmp_path):
    security.configure_sandbox([tmp_path])
    p = tmp_path / "profiles" / "local"
    p.mkdir(parents=True)
    return p


def _make_client(profile, *, read_only=False, profile_dir=None):
    app = FastAPI()
    app.include_router(prompts_router.router, prefix="/api/prompts")
    app.state.profile_dir = profile if profile_dir is None else profile_dir
    app.state.profile_read_only = read_only
    return TestClient(app)


class TestListPrompts:
    def test_lists_catalog_with_defaults(self, profile):
        http = _make_client(profile)
        resp = http.get("/api/prompts")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        stems = [p["stem"] for p in data]
        assert "cover_letter" in stems and "resume_objective" in stems
        cover = next(p for p in data if p["stem"] == "cover_letter")
        assert cover["overridden"] is False
        assert cover["editable"] is True
        assert cover["content"] == cover["default"]
        # Placeholders are derived from the live template text.
        assert "name" in cover["placeholders"]


class TestSaveAndReset:
    def test_save_creates_override(self, profile):
        http = _make_client(profile)
        resp = http.put(
            "/api/prompts/cover_letter",
            json={"content": "Custom letter for ${name}."},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["overridden"] is True
        assert body["content"] == "Custom letter for ${name}."
        assert body["placeholders"] == ["name"]
        assert (profile / "prompt" / "cover_letter.txt").is_file()

    def test_reset_removes_override(self, profile):
        http = _make_client(profile)
        http.put("/api/prompts/cover_letter", json={"content": "Custom ${name}"})
        resp = http.delete("/api/prompts/cover_letter")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["overridden"] is False
        assert body["content"] == body["default"]
        assert not (profile / "prompt" / "cover_letter.txt").exists()

    def test_reset_when_no_override_is_noop(self, profile):
        http = _make_client(profile)
        resp = http.delete("/api/prompts/skills_analysis")
        assert resp.status_code == 200, resp.text
        assert resp.json()["overridden"] is False


class TestGuards:
    def test_read_only_profile_cannot_save(self, profile):
        http = _make_client(profile, read_only=True)
        resp = http.put("/api/prompts/cover_letter", json={"content": "x"})
        assert resp.status_code == 403

    def test_no_active_profile_cannot_save(self, profile):
        http = _make_client(profile, profile_dir=None)
        # profile_dir is falsy -> nowhere to write.
        app = http.app
        app.state.profile_dir = None
        resp = http.put("/api/prompts/cover_letter", json={"content": "x"})
        assert resp.status_code == 403

    def test_unknown_stem_404(self, profile):
        http = _make_client(profile)
        assert http.put("/api/prompts/bogus", json={"content": "x"}).status_code == 404
        assert http.delete("/api/prompts/bogus").status_code == 404

    def test_no_profile_list_marks_not_editable(self, profile):
        http = _make_client(profile)
        http.app.state.profile_dir = None
        data = http.get("/api/prompts").json()
        assert all(p["editable"] is False for p in data)
        assert all(p["overridden"] is False for p in data)
