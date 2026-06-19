#!/usr/bin/env python3
"""Tests for DELETE /api/tracking/queue (clear a failed job's JD)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import security
from routers import tracking


@pytest.fixture
def client(tmp_path):
    (tmp_path / "jobs").mkdir()
    (tmp_path / "completed" / "jobs").mkdir(parents=True)
    security.configure_sandbox([tmp_path])
    app = FastAPI()
    app.include_router(tracking.router, prefix="/api/tracking")
    app.state.settings = {"data_dir": tmp_path}
    return TestClient(app), tmp_path


def test_deletes_queued_file(client):
    c, tmp = client
    jd = tmp / "jobs" / "x.pdf"
    jd.write_text("x")
    r = c.request("DELETE", "/api/tracking/queue", json={"path": str(jd)})
    assert r.status_code == 200
    assert not jd.exists()


def test_refuses_completed(client):
    c, tmp = client
    done = tmp / "completed" / "jobs" / "y.pdf"
    done.write_text("y")
    r = c.request("DELETE", "/api/tracking/queue", json={"path": str(done)})
    assert r.status_code == 400
    assert done.exists()


def test_missing_file_404(client):
    c, tmp = client
    r = c.request("DELETE", "/api/tracking/queue", json={"path": str(tmp / "jobs" / "nope.pdf")})
    assert r.status_code == 404


def test_outside_data_dir_rejected(client):
    c, tmp = client
    r = c.request("DELETE", "/api/tracking/queue", json={"path": "/etc/hosts"})
    assert r.status_code == 400
