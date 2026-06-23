#!/usr/bin/env python3
"""Tests for the URL / paste-text JD ingestion endpoints.

A minimal FastAPI app mounts only the jobs router. The apply pipeline is stubbed
(no model call, no threads) and the budget guard is neutralized, so the tests cover
exactly the ingestion wiring: snapshot creation feeds the shared apply pipeline, and
extraction failures surface as 422. No network, Tila/Acme only.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.jobs as jobs
from jobjob.ingest.jd_source import JDIngestError

_ACME_POSTING = (
    "Acme Gazette seeks a science correspondent to cover print science and the "
    "history of typography. Five years of newsroom experience required; a nose for "
    "accuracy and lively prose for a general audience are essential."
)


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    (d / "jobs").mkdir(parents=True)
    return d


@pytest.fixture
def client(data_dir, monkeypatch):
    # Neutralize the budget guard and the apply pipeline: these tests cover only the
    # ingestion → snapshot → launch wiring, not model/thread execution.
    monkeypatch.setattr(jobs, "check_budget", lambda **k: None)
    monkeypatch.setattr(jobs, "_make_apply_run", lambda *a, **k: (lambda: {"ok": True}))
    monkeypatch.setattr(jobs, "_start_job", lambda fn: "job-test-1")

    app = FastAPI()
    app.include_router(jobs.router, prefix="/api/jobs")
    app.state.settings = {
        "applications_input_dir": data_dir,
        "per_run_budget": 2.0,
        "daily_budget": 20.0,
    }
    return TestClient(app)


class TestApplyFromUrl:
    def test_writes_snapshot_and_launches(self, client, data_dir, monkeypatch):
        def _fake_snapshot(url, jobs_dir, **kwargs):
            path = Path(jobs_dir) / "jd-acme.md"
            path.write_text(_ACME_POSTING, encoding="utf-8")
            return path

        monkeypatch.setattr(jobs, "snapshot_from_url", _fake_snapshot)

        resp = client.post(
            "/api/jobs/apply/from-url",
            json={"url": "https://jobs.example.com/acme/science-correspondent"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["job_id"] == "job-test-1"
        assert body["snapshot"].endswith("jd-acme.md")
        assert (data_dir / "jobs" / "jd-acme.md").is_file()

    def test_extraction_failure_is_422(self, client, monkeypatch):
        def _boom(url, jobs_dir, **kwargs):
            raise JDIngestError("Couldn't extract text from this URL")

        monkeypatch.setattr(jobs, "snapshot_from_url", _boom)
        resp = client.post(
            "/api/jobs/apply/from-url",
            json={"url": "https://linkedin.com/jobs/view/123"},
        )
        assert resp.status_code == 422
        assert "extract" in resp.json()["detail"]


class TestApplyFromText:
    def test_writes_snapshot_and_launches(self, client, data_dir):
        # Uses the real snapshot_from_text (no network).
        resp = client.post(
            "/api/jobs/apply/from-text",
            json={"text": _ACME_POSTING},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["job_id"] == "job-test-1"
        snapshots = list((data_dir / "jobs").glob("*.md"))
        assert len(snapshots) == 1
        assert "Acme Gazette" in snapshots[0].read_text(encoding="utf-8")

    def test_too_short_paste_is_422(self, client, data_dir):
        resp = client.post("/api/jobs/apply/from-text", json={"text": "too short"})
        assert resp.status_code == 422
        assert list((data_dir / "jobs").glob("*.md")) == []


# __END__
