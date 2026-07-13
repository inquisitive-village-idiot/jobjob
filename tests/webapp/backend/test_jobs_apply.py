#!/usr/bin/env python3
"""Tests for POST /api/jobs/apply — the autofill launch endpoint.

Everything external is mocked: no real browser, no real subprocess. Only the
sentinel constant (``FILL_COMPLETE_SENTINEL``) is imported from the runner —
the browser-driving code path is never exercised. Coverage is the launch
wiring: URL gating from the source tier, the detached-subprocess spawn, and
the run-history/log plumbing.
"""

import sys
import time
from unittest import mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.jobs as jobs
import security
from jobjob.autofill.runner import FILL_COMPLETE_SENTINEL
from services import application_source, run_history
from services.application_metadata import ensure_entity_id

_FOLDER = "2026-01-01 - Acme - Engineer"
_URL = "https://acme.wd1.myworkdayjobs.com/en-US/Acme/job/Software-Engineer_R123"


class _FakeStdout:
    """Minimal stand-in for a subprocess's piped, text-mode stdout."""

    def __init__(self, lines):
        self._lines = list(lines)

    def readline(self) -> str:
        return self._lines.pop(0) if self._lines else ""


class _FakeProcess:
    def __init__(self, lines, pid: int = 4242):
        self.stdout = _FakeStdout(lines)
        self.pid = pid


# The detached runner prints the report, then a machine sentinel line. The pump
# completes the job on the sentinel; the report lines are logged, the sentinel
# is not.
_REPORT_LINES = [
    "Auto-fill report (workday):\n",
    "  filled 2 field(s):\n",
    "    ✓ First name: Ada\n",
    "    ✓ Email: ada@example.com\n",
]
_SENTINEL_LINE = FILL_COMPLETE_SENTINEL + "\n"
_REPORT_THEN_SENTINEL = [*_REPORT_LINES, _SENTINEL_LINE]


@pytest.fixture
def mirror(tmp_path):
    m = tmp_path / "mirror"
    m.mkdir()
    security.configure_sandbox([m])
    return m


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def app_folder(mirror):
    folder = mirror / _FOLDER
    folder.mkdir()
    return folder


@pytest.fixture
def client(mirror, data_dir, monkeypatch):
    monkeypatch.setattr(jobs, "_jobs", {})
    app = FastAPI()
    app.include_router(jobs.router, prefix="/api/jobs")
    app.state.settings = {
        "applications_output_dir": str(mirror),
        "applications_input_dir": data_dir,
    }
    return TestClient(app)


def _wait_for_job(job_id, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if jobs._jobs[job_id]["status"] != "running":
            return
        time.sleep(0.01)
    raise AssertionError("job did not finish in time")


class TestUrlGating:
    def test_no_source_json_is_400(self, client, app_folder):
        resp = client.post("/api/jobs/apply", json={"folder_name": _FOLDER})
        assert resp.status_code == 400
        assert "posting URL" in resp.json()["detail"]

    def test_source_without_web_uri_is_400(self, client, app_folder):
        application_source.write_source(app_folder, {"company": "Acme"})
        resp = client.post("/api/jobs/apply", json={"folder_name": _FOLDER})
        assert resp.status_code == 400

    def test_unsupported_ats_host_is_400(self, client, app_folder, monkeypatch):
        application_source.write_source(app_folder, {"web_uri": _URL})
        monkeypatch.setattr(jobs, "select_adapter", lambda url: None)
        resp = client.post("/api/jobs/apply", json={"folder_name": _FOLDER})
        assert resp.status_code == 400
        assert "adapter" in resp.json()["detail"]

    def test_missing_folder_is_404(self, client):
        resp = client.post(
            "/api/jobs/apply", json={"folder_name": "2099-01-01 - Nope - Role"}
        )
        assert resp.status_code == 404

    def test_mirror_unconfigured_is_400(self, mirror, data_dir, monkeypatch):
        monkeypatch.setattr(jobs, "_jobs", {})
        app = FastAPI()
        app.include_router(jobs.router, prefix="/api/jobs")
        app.state.settings = {
            "applications_output_dir": None,
            "applications_input_dir": data_dir,
        }
        resp = TestClient(app).post("/api/jobs/apply", json={"folder_name": _FOLDER})
        assert resp.status_code == 400

    def test_neither_id_given_is_400(self, client, app_folder):
        application_source.write_source(app_folder, {"web_uri": _URL})
        resp = client.post("/api/jobs/apply", json={})
        assert resp.status_code == 400


class TestLaunch:
    def test_spawns_detached_subprocess_and_returns_promptly(
        self, client, app_folder, data_dir
    ):
        application_source.write_source(app_folder, {"web_uri": _URL})
        mock_popen = mock.Mock(return_value=_FakeProcess(list(_REPORT_THEN_SENTINEL)))
        with mock.patch.object(jobs.subprocess, "Popen", mock_popen):
            started = time.perf_counter()
            resp = client.post("/api/jobs/apply", json={"folder_name": _FOLDER})
            elapsed = time.perf_counter() - started

        assert resp.status_code == 200, resp.text
        job_id = resp.json()["job_id"]
        # The HTTP response itself never waits on the subprocess/human.
        assert elapsed < 2.0

        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0] == [
            sys.executable,
            "-m",
            "jobjob",
            "apply",
            _URL,
            "--assisted-detached",
        ]
        assert kwargs["start_new_session"] is True

        _wait_for_job(job_id)
        assert jobs._jobs[job_id]["status"] == "completed"

    def test_records_kind_apply_run(self, client, app_folder, data_dir):
        application_source.write_source(app_folder, {"web_uri": _URL})
        mock_popen = mock.Mock(return_value=_FakeProcess(list(_REPORT_THEN_SENTINEL)))
        with mock.patch.object(jobs.subprocess, "Popen", mock_popen):
            resp = client.post("/api/jobs/apply", json={"folder_name": _FOLDER})
        job_id = resp.json()["job_id"]
        _wait_for_job(job_id)

        runs = run_history.runs_dir(data_dir)
        (record,) = run_history.list_runs(runs, jobs._jobs)
        assert record["kind"] == "apply"
        assert record["folder_name"] == _FOLDER
        assert record["status"] == "completed"

    def test_completes_on_sentinel_which_is_not_logged(
        self, client, app_folder, data_dir
    ):
        application_source.write_source(app_folder, {"web_uri": _URL})
        mock_popen = mock.Mock(return_value=_FakeProcess(list(_REPORT_THEN_SENTINEL)))
        with mock.patch.object(jobs.subprocess, "Popen", mock_popen):
            resp = client.post("/api/jobs/apply", json={"folder_name": _FOLDER})
        job_id = resp.json()["job_id"]
        _wait_for_job(job_id)

        assert jobs._jobs[job_id]["status"] == "completed"
        runs = run_history.runs_dir(data_dir)
        log = run_history.read_log(runs, job_id)
        assert log is not None
        # The report lines are captured; the machine sentinel is not.
        assert "Auto-fill report (workday):" in log
        assert "First name: Ada" in log
        assert FILL_COMPLETE_SENTINEL not in log

    def test_entity_id_resolves_folder_and_is_stamped(
        self, client, app_folder, data_dir
    ):
        ensure_entity_id(app_folder)
        from services.application_metadata import read_entity_id

        entity_id = read_entity_id(app_folder)
        application_source.write_source(app_folder, {"web_uri": _URL})
        mock_popen = mock.Mock(return_value=_FakeProcess(list(_REPORT_THEN_SENTINEL)))
        with mock.patch.object(jobs.subprocess, "Popen", mock_popen):
            resp = client.post("/api/jobs/apply", json={"entity_id": entity_id})
        assert resp.status_code == 200, resp.text
        job_id = resp.json()["job_id"]
        _wait_for_job(job_id)

        runs = run_history.runs_dir(data_dir)
        (record,) = run_history.list_runs(runs, jobs._jobs)
        assert record["entity_id"] == entity_id

    def test_process_exits_without_sentinel_fails_the_job(
        self, client, app_folder, data_dir
    ):
        application_source.write_source(app_folder, {"web_uri": _URL})
        # Playwright missing / adapter crash: report/sentinel never printed,
        # stdout closes. The job fails (but the subprocess is left unkilled).
        mock_popen = mock.Mock(return_value=_FakeProcess([]))
        with mock.patch.object(jobs.subprocess, "Popen", mock_popen):
            resp = client.post("/api/jobs/apply", json={"folder_name": _FOLDER})
        job_id = resp.json()["job_id"]
        _wait_for_job(job_id)
        assert jobs._jobs[job_id]["status"] == "failed"


# __END__
