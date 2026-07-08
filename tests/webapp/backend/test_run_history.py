#!/usr/bin/env python3
"""Tests for services.run_history and the jobs run-history endpoints."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.jobs as jobs
from services import run_history as MOD


@pytest.fixture
def runs(tmp_path):
    return MOD.runs_dir(tmp_path)


class TestRunLifecycle:
    def test_start_then_finish_round_trip(self, runs):
        MOD.start_run(runs, "r1", kind="apply", label="jd.pdf", paths=("/a/jd.pdf",))
        MOD.finish_run(runs, "r1", status="failed", error="boom")
        record = json.loads(MOD.record_path(runs, "r1").read_text())
        assert record["status"] == "failed"
        assert record["error"] == "boom"
        assert record["kind"] == "apply"
        assert record["finished_at"] is not None

    def test_read_log(self, runs):
        MOD.log_path(runs, "r1").write_text("jobjob.apply: hello\n", encoding="utf-8")
        assert MOD.read_log(runs, "r1") == "jobjob.apply: hello\n"
        assert MOD.read_log(runs, "missing") is None


class TestFinishRunEntityId:
    """entity_id on the run record (application-identity, phase 1)."""

    def test_finish_run_stamps_entity_id_when_given(self, runs):
        MOD.start_run(runs, "r1", kind="build", label="jd.pdf")
        MOD.finish_run(runs, "r1", status="completed", entity_id="e1")
        record = json.loads(MOD.record_path(runs, "r1").read_text())
        expected = "e1"
        found = record["entity_id"]
        assert found == expected

    def test_finish_run_omits_entity_id_when_legacy(self, runs):
        MOD.start_run(runs, "r1", kind="build", label="jd.pdf")
        MOD.finish_run(runs, "r1", status="completed")
        record = json.loads(MOD.record_path(runs, "r1").read_text())
        assert "entity_id" not in record


class TestListRuns:
    def test_merged_newest_first_with_live_override(self, runs):
        old = MOD.start_run(runs, "old", kind="apply", label="a")
        old["started_at"] = "2026-01-01T00:00:00+00:00"
        MOD.record_path(runs, "old").write_text(json.dumps(old))
        MOD.finish_run(runs, "old", status="completed")
        MOD.start_run(runs, "live", kind="enrich", label="b")

        items = MOD.list_runs(runs, {"live": {"status": "running", "error": None}})

        assert [i["run_id"] for i in items] == ["live", "old"]
        assert items[0]["status"] == "running"

    def test_interrupted_run_reported_failed(self, runs):
        MOD.start_run(runs, "dead", kind="apply", label="a")
        (item,) = MOD.list_runs(runs, {})
        assert item["status"] == "failed"
        assert "Interrupted" in item["error"]

    def test_has_log_flag(self, runs):
        MOD.start_run(runs, "r1", kind="apply", label="a")
        MOD.finish_run(runs, "r1", status="completed")
        MOD.log_path(runs, "r1").write_text("x", encoding="utf-8")
        (item,) = MOD.list_runs(runs, {})
        assert item["has_log"] is True


class TestPrune:
    def test_oldest_beyond_keep_removed_with_logs(self, runs):
        for i in range(5):
            record = MOD.start_run(runs, f"r{i}", kind="apply", label=str(i))
            record["started_at"] = f"2026-01-0{i + 1}T00:00:00+00:00"
            MOD.record_path(runs, f"r{i}").write_text(json.dumps(record))
            MOD.log_path(runs, f"r{i}").write_text("log", encoding="utf-8")

        MOD.prune(runs, keep=2)

        remaining = sorted(p.stem for p in runs.glob("*.json"))
        assert remaining == ["r3", "r4"]
        assert not MOD.log_path(runs, "r0").exists()


class TestJobsEndpoints:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        monkeypatch.setattr(jobs, "_jobs", {})
        app = FastAPI()
        app.include_router(jobs.router, prefix="/api/jobs")
        app.state.settings = {"applications_input_dir": tmp_path}
        return TestClient(app), MOD.runs_dir(tmp_path)

    def test_list_includes_persisted_history(self, client):
        http, runs = client
        MOD.start_run(runs, "r1", kind="apply", label="jd.pdf")
        MOD.finish_run(runs, "r1", status="completed")

        resp = http.get("/api/jobs")

        assert resp.status_code == 200
        (item,) = resp.json()
        assert item["run_id"] == "r1"
        assert item["status"] == "completed"
        assert item["label"] == "jd.pdf"

    def test_log_endpoint(self, client):
        http, runs = client
        MOD.log_path(runs, "r1").write_text("jobjob: line\n", encoding="utf-8")

        resp = http.get("/api/jobs/r1/log")

        assert resp.status_code == 200
        assert resp.json()["log"] == "jobjob: line\n"

    def test_log_missing_is_404(self, client):
        http, _ = client
        assert http.get("/api/jobs/nope/log").status_code == 404


class TestStartJobRecordsEntityId:
    """_start_job (routers.jobs) forwards a completed result's entity_id to
    finish_run — the wiring behind the run-history "carries the entity id"
    requirement (application-identity, phase 1)."""

    @pytest.fixture(autouse=True)
    def _reset_jobs(self, monkeypatch):
        monkeypatch.setattr(jobs, "_jobs", {})

    def _wait(self, job_id, timeout=2.0):
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            if jobs._jobs[job_id]["status"] != "running":
                return
            time.sleep(0.01)
        raise AssertionError("job did not finish in time")

    def test_entity_id_recorded_on_completion(self, runs):
        job_id = jobs._start_job(
            lambda: {"entity_id": "e1", "output_dir": "/tmp/x"},
            runs_dir=runs,
            kind="build",
            label="jd.pdf",
        )
        self._wait(job_id)
        record = json.loads(MOD.record_path(runs, job_id).read_text())
        expected = "e1"
        found = record["entity_id"]
        assert found == expected

    def test_legacy_result_omits_entity_id(self, runs):
        job_id = jobs._start_job(
            lambda: {"output_dir": "/tmp/x"},
            runs_dir=runs,
            kind="build",
            label="jd.pdf",
        )
        self._wait(job_id)
        record = json.loads(MOD.record_path(runs, job_id).read_text())
        assert "entity_id" not in record

    def test_batch_result_shape_does_not_error(self, runs):
        # Batch/schedule results are {"processed": ..., "items": [...]} — no
        # top-level entity_id; must not raise trying to read one.
        job_id = jobs._start_job(
            lambda: {"processed": 1, "items": []},
            runs_dir=runs,
            kind="batch",
            label="Build all (1)",
        )
        self._wait(job_id)
        record = json.loads(MOD.record_path(runs, job_id).read_text())
        assert "entity_id" not in record


class TestMigrateLegacyKinds:
    """One-time kind:"apply" -> "build" fixup (full-build-rename)."""

    def _kind(self, runs, run_id):
        return json.loads(MOD.record_path(runs, run_id).read_text())["kind"]

    def test_rewrites_apply_to_build_and_leaves_others(self, runs):
        MOD.start_run(runs, "gen", kind="apply", label="jd.pdf")
        MOD.start_run(runs, "enr", kind="enrich", label="profile")

        MOD.migrate_legacy_kinds(runs)

        assert self._kind(runs, "gen") == "build"
        assert self._kind(runs, "enr") == "enrich"
        assert (runs / MOD._KIND_MIGRATION_MARKER).is_file()

    def test_marker_guards_future_autofill_apply_records(self, runs):
        MOD.start_run(runs, "old", kind="apply", label="a")
        MOD.migrate_legacy_kinds(runs)
        # After the one-time fixup, a NEW apply record (autofill) must survive.
        MOD.start_run(runs, "autofill", kind="apply", label="b")

        MOD.migrate_legacy_kinds(runs)

        assert self._kind(runs, "old") == "build"
        assert self._kind(runs, "autofill") == "apply"

    def test_empty_runs_dir_does_not_raise(self, runs):
        MOD.migrate_legacy_kinds(runs)
        assert (runs / MOD._KIND_MIGRATION_MARKER).is_file()


# __END__
