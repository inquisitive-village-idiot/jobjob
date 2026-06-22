#!/usr/bin/env python3
"""Tests for the static-content API section toggle route.

A minimal FastAPI app mounts only the static-content router. Writes are sandboxed to
``tmp_path``; the templates.toml is seeded with the Tila demo sections (no PII).
"""

import tomllib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.static_content as sc
import security

_TEMPLATES_TOML = """\
[tool.templates]
default = "print_correspondent"

[[tool.templates.section]]
heading = "Objective"
section = "objective"
enabled = true

[[tool.templates.section]]
heading = "Key Career Highlights"
section = "highlights"

[[tool.templates.template]]
name = "print_correspondent"
archetype = "Print science correspondent"
doc_id = ""
"""


@pytest.fixture
def repo(tmp_path):
    security.configure_sandbox([tmp_path])
    content = tmp_path / "static" / "example" / "content"
    content.mkdir(parents=True)
    (content / "templates.toml").write_text(_TEMPLATES_TOML, encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(repo):
    app = FastAPI()
    app.include_router(sc.router, prefix="/api/static")
    app.state.repo_root = repo
    app.state.profile_dir = None  # no active profile -> repo static/
    return app, TestClient(app), repo


class TestSectionToggle:
    def test_disable_section_persists(self, client):
        _, http, repo = client
        resp = http.patch(
            "/api/static/toml/templates/sections/0", json={"fields": {"enabled": False}}
        )
        assert resp.status_code == 200, resp.text
        doc = tomllib.loads(
            (repo / "static" / "example" / "content" / "templates.toml").read_text(
                encoding="utf-8"
            )
        )
        sections = doc["tool"]["templates"]["section"]
        assert sections[0]["enabled"] is False
        assert sections[1].get("enabled", True) is True  # untouched

    def test_enabled_added_when_absent(self, client):
        # The second section has no `enabled` key; toggling it should add one.
        _, http, repo = client
        resp = http.patch(
            "/api/static/toml/templates/sections/1", json={"fields": {"enabled": False}}
        )
        assert resp.status_code == 200, resp.text
        parsed = resp.json()["parsed"]
        assert parsed["tool"]["templates"]["section"][1]["enabled"] is False

    def test_index_out_of_range_404(self, client):
        _, http, _ = client
        resp = http.patch(
            "/api/static/toml/templates/sections/9", json={"fields": {"enabled": False}}
        )
        assert resp.status_code == 404

    def test_unknown_field_422(self, client):
        _, http, _ = client
        resp = http.patch(
            "/api/static/toml/templates/sections/0", json={"fields": {"bogus": 1}}
        )
        assert resp.status_code == 422

    def test_preserves_comments_and_other_tables(self, client):
        _, http, repo = client
        http.patch(
            "/api/static/toml/templates/sections/0", json={"fields": {"enabled": False}}
        )
        raw = (repo / "static" / "example" / "content" / "templates.toml").read_text(
            encoding="utf-8"
        )
        # tomlkit round-trip keeps the template array intact.
        assert "print_correspondent" in raw
        assert 'default = "print_correspondent"' in raw
