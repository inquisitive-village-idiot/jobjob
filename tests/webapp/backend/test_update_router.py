#!/usr/bin/env python3
"""Tests for the self-update API router (service layer is mocked)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.update as update_router
from services import update_service as u


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(update_router.router, prefix="/api/update")
    return TestClient(app)


_STATUS = {
    "current_version": "1.0.0",
    "current_release_date": "2026-06-19T20:00:00Z",
    "latest_version": "1.2.0",
    "latest_release_date": "2026-06-25T12:00:00Z",
    "last_checked": "2026-06-20T03:00:00Z",
    "check_error": None,
    "install_method": "pipx",
    "update_available": True,
    "can_update": True,
}


def test_status(client, monkeypatch):
    monkeypatch.setattr(u, "get_status", lambda: _STATUS)
    resp = client.get("/api/update/status")
    assert resp.status_code == 200
    assert resp.json()["latest_version"] == "1.2.0"


def test_check_calls_service_then_returns_status(client, monkeypatch):
    calls = []
    monkeypatch.setattr(u, "check_for_updates", lambda: calls.append("checked"))
    monkeypatch.setattr(u, "get_status", lambda: _STATUS)
    resp = client.post("/api/update/check")
    assert resp.status_code == 200
    assert calls == ["checked"]
    assert resp.json()["update_available"] is True


def test_apply(client, monkeypatch):
    monkeypatch.setattr(
        u, "apply_update", lambda: {"ok": True, "method": "pipx", "message": "done"}
    )
    resp = client.post("/api/update/apply")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
