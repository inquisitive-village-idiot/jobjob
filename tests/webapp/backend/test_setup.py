#!/usr/bin/env python3
"""Tests for the first-run setup API (routers.setup)."""

import json
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import setup


@pytest.fixture
def client(tmp_path):
    app_cfg = tmp_path / "config" / ".env"
    app_cfg.parent.mkdir(parents=True)
    app_cfg.write_text("")
    profile_cfg = tmp_path / "profile" / "config" / ".profile"
    profile_cfg.parent.mkdir(parents=True)
    profile_cfg.write_text("")

    app = FastAPI()
    app.include_router(setup.router, prefix="/api/setup")
    app.state.app_config_path = app_cfg
    app.state.profile_config_path = profile_cfg
    app.state.settings = {
        "credentials_file": tmp_path / "cfg" / "credentials.json",
        "token_file": tmp_path / "cfg" / "token.pickle",
    }
    return TestClient(app), tmp_path, app_cfg, profile_cfg


def test_status_empty(client):
    c, *_ = client
    s = c.get("/api/setup/status").json()
    assert s["anthropic_key"] is False
    assert s["applicant"] is False
    assert s["complete"] is False
    assert s["dismissed"] is False


def test_set_anthropic_key_then_status(client):
    c, _tmp, app_cfg, _ = client
    r = c.put("/api/setup/anthropic-key", json={"value": "sk-test-123"})
    assert r.status_code == 200
    assert 'ANTHROPIC_API_KEY="sk-test-123"' in app_cfg.read_text()
    assert c.get("/api/setup/status").json()["anthropic_key"] is True


def test_empty_key_rejected(client):
    c, *_ = client
    assert c.put("/api/setup/anthropic-key", json={"value": "   "}).status_code == 400


def test_complete_when_key_and_applicant_set(client):
    c, _tmp, _app, profile_cfg = client
    profile_cfg.write_text('APPLICANT_NAME="Jane Doe"\n')
    c.put("/api/setup/anthropic-key", json={"value": "sk"})
    s = c.get("/api/setup/status").json()
    assert s["applicant"] is True
    assert s["complete"] is True


def test_dismiss_roundtrip(client):
    c, _tmp, app_cfg, _ = client
    c.post("/api/setup/dismiss", json={"dismissed": True})
    assert (app_cfg.parent / setup._DISMISS_MARKER).is_file()
    assert c.get("/api/setup/status").json()["dismissed"] is True
    c.post("/api/setup/dismiss", json={"dismissed": False})
    assert c.get("/api/setup/status").json()["dismissed"] is False


def test_credentials_upload(client):
    c, _tmp, _app, _ = client
    payload = json.dumps({"installed": {"client_id": "x"}}).encode()
    r = c.post(
        "/api/setup/credentials",
        files={"file": ("credentials.json", payload, "application/json")},
    )
    assert r.status_code == 200
    assert c.get("/api/setup/status").json()["credentials_file"] is True


def test_credentials_rejects_non_json(client):
    c, *_ = client
    r = c.post(
        "/api/setup/credentials",
        files={"file": ("credentials.json", b"not json", "application/json")},
    )
    assert r.status_code == 400


def test_google_auth_requires_credentials(client):
    c, *_ = client
    assert c.post("/api/setup/google-auth").status_code == 400


def test_google_auth_starts_when_credentials_present(client):
    c, *_ = client
    c.post(
        "/api/setup/credentials",
        files={"file": ("credentials.json", b"{}", "application/json")},
    )
    with mock.patch.object(setup, "_run_google_auth"):
        r = c.post("/api/setup/google-auth")
    assert r.status_code == 200
    assert r.json()["started"] is True


# __END__
