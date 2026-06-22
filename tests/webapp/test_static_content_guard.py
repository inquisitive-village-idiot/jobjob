#!/usr/bin/env python3
"""The read-only example profile must reject content writes with 403."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import static_content as sc


def _app(read_only: bool, profile_dir):
    from security import configure_sandbox

    configure_sandbox([profile_dir])
    app = FastAPI()
    app.include_router(sc.router, prefix="/api/static")
    app.state.repo_root = profile_dir
    app.state.profile_dir = str(profile_dir)
    app.state.profile_read_only = read_only
    return TestClient(app)


@pytest.fixture
def example_dir(tmp_path):
    from jobjob.loader.skeleton import create_blank_profile

    return create_blank_profile(tmp_path / "prof")


class TestReadOnlyGuard:
    def test_put_toml_blocked(self, example_dir):
        client = _app(read_only=True, profile_dir=example_dir)
        r = client.put("/api/static/toml/skills", json={"content": "[tool.skills]\n"})
        assert r.status_code == 403
        assert "read-only" in r.json()["detail"].lower()

    def test_patch_item_blocked(self, example_dir):
        client = _app(read_only=True, profile_dir=example_dir)
        r = client.patch(
            "/api/static/toml/skills/items/0", json={"fields": {"text": "x"}}
        )
        assert r.status_code == 403

    def test_reference_write_blocked(self, example_dir):
        client = _app(read_only=True, profile_dir=example_dir)
        r = client.put("/api/static/reference/background.md", json={"content": "x"})
        assert r.status_code == 403

    def test_writable_profile_allows_toml(self, example_dir):
        client = _app(read_only=False, profile_dir=example_dir)
        r = client.put(
            "/api/static/toml/skills",
            json={"content": "[tool.skills]\ndefault_number = 5\n"},
        )
        assert r.status_code == 200

    def test_reads_allowed_when_read_only(self, example_dir):
        client = _app(read_only=True, profile_dir=example_dir)
        assert client.get("/api/static/toml/skills").status_code == 200
