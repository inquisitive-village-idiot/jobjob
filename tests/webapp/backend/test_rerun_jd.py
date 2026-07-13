#!/usr/bin/env python3
"""Tests for re-run source-JD resolution (_find_rerun_jd)."""

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.jobs as jobs
import security
from routers.jobs import _find_rerun_jd
from services.application_metadata import METADATA_FILENAME

_FOLDER = "2026-02-26 - Thomson Reuters - Sr Director Applied Research"


def _dirs(tmp_path):
    data = tmp_path / "data"
    (data / "completed" / "jobs").mkdir(parents=True)
    mirror = tmp_path / "mirror"
    (mirror / _FOLDER).mkdir(parents=True)
    return data, mirror


def test_finds_old_jobdescription_prefix(tmp_path):
    # Older applications named the JD JobDescription_* — must still resolve.
    data, mirror = _dirs(tmp_path)
    jd = mirror / _FOLDER / "JobDescription_Thomson Reuters_Sr Director.pdf"
    jd.write_text("x")
    assert _find_rerun_jd(data, str(mirror), _FOLDER) == jd


def test_finds_current_jd_prefix(tmp_path):
    data, mirror = _dirs(tmp_path)
    jd = mirror / _FOLDER / "JD_ThomsonReuters_SrDirector.pdf"
    jd.write_text("x")
    assert _find_rerun_jd(data, str(mirror), _FOLDER) == jd


def test_prefers_completed_jobs_over_mirror(tmp_path):
    data, mirror = _dirs(tmp_path)
    completed = data / "completed" / "jobs" / f"{_FOLDER}.pdf"
    completed.write_text("x")
    (mirror / _FOLDER / "JD_x.pdf").write_text("x")
    assert _find_rerun_jd(data, str(mirror), _FOLDER) == completed


def test_returns_none_when_absent(tmp_path):
    data, mirror = _dirs(tmp_path)
    assert _find_rerun_jd(data, str(mirror), _FOLDER) is None


def test_none_mirror_dir_is_tolerated(tmp_path):
    data, _ = _dirs(tmp_path)
    assert _find_rerun_jd(data, None, _FOLDER) is None


class TestEntityIdPreferringResolution:
    """Id-preferring resolution (application-identity, phase 1): resolve by
    entity_id first (survives a rename since the last run), fall back to the
    given folder_name otherwise."""

    def test_resolves_by_id_after_a_rename(self, tmp_path):
        data, mirror = _dirs(tmp_path)
        renamed = "2026-02-26 - Thomson Reuters - VP Applied Research"
        (mirror / renamed).mkdir()
        (mirror / renamed / METADATA_FILENAME).write_text(
            json.dumps({"entity_id": "e1"})
        )
        jd = mirror / renamed / "JD_ThomsonReuters_VP.pdf"
        jd.write_text("x")

        found = _find_rerun_jd(data, str(mirror), _FOLDER, entity_id="e1")

        assert found == jd

    def test_falls_back_to_folder_name_when_id_not_found(self, tmp_path):
        data, mirror = _dirs(tmp_path)
        jd = mirror / _FOLDER / "JD_ThomsonReuters_SrDirector.pdf"
        jd.write_text("x")

        found = _find_rerun_jd(data, str(mirror), _FOLDER, entity_id="nope")

        assert found == jd

    def test_no_entity_id_is_the_legacy_path(self, tmp_path):
        data, mirror = _dirs(tmp_path)
        jd = mirror / _FOLDER / "JD_ThomsonReuters_SrDirector.pdf"
        jd.write_text("x")

        found = _find_rerun_jd(data, str(mirror), _FOLDER)

        assert found == jd

    def test_corrupt_metadata_in_scanned_folder_is_tolerated(self, tmp_path):
        data, mirror = _dirs(tmp_path)
        (mirror / _FOLDER / METADATA_FILENAME).write_text("{not json")
        jd = mirror / _FOLDER / "JD_ThomsonReuters_SrDirector.pdf"
        jd.write_text("x")

        found = _find_rerun_jd(data, str(mirror), _FOLDER, entity_id="e1")

        assert found == jd


class TestRerunEndpointPinsEntityDir:
    """launch_build_rerun pins entity_dir to the application's CURRENT mirror
    folder so a re-run (even after a rename) reuses the entity_id rather than
    minting a fresh one."""

    @pytest.fixture
    def wired(self, tmp_path, monkeypatch):
        data = tmp_path / "data"
        (data / "completed" / "jobs").mkdir(parents=True)
        mirror = tmp_path / "mirror"
        (mirror / _FOLDER).mkdir(parents=True)
        (mirror / _FOLDER / "JD_x.pdf").write_text("x")
        security.configure_sandbox([tmp_path])

        captured: dict = {}

        def _fake_make_build_run(jd_path, **kwargs):
            captured["make_build_run_kwargs"] = kwargs
            return lambda: {"ok": True}

        monkeypatch.setattr(jobs, "_make_build_run", _fake_make_build_run)
        monkeypatch.setattr(jobs, "_start_job", lambda *a, **k: "job-1")

        app = FastAPI()
        app.include_router(jobs.router, prefix="/api/jobs")
        app.state.settings = {
            "applications_input_dir": str(data),
            "applications_output_dir": str(mirror),
        }
        return TestClient(app), mirror, captured

    def test_entity_dir_is_current_mirror_folder(self, wired):
        http, mirror, captured = wired
        resp = http.post("/api/jobs/build/rerun", json={"folder_name": _FOLDER})
        assert resp.status_code == 200, resp.text
        expected = Path(mirror).expanduser() / _FOLDER
        found = captured["make_build_run_kwargs"]["entity_dir"]
        assert found == expected

    def test_entity_dir_none_without_mirror(self, tmp_path, monkeypatch):
        data = tmp_path / "data"
        (data / "completed" / "jobs").mkdir(parents=True)
        jd = data / "completed" / "jobs" / f"{_FOLDER}.pdf"
        jd.write_text("x")
        security.configure_sandbox([tmp_path])

        captured: dict = {}
        monkeypatch.setattr(
            jobs,
            "_make_build_run",
            lambda jd_path, **kwargs: captured.update(kwargs) or (lambda: {}),
        )
        monkeypatch.setattr(jobs, "_start_job", lambda *a, **k: "job-1")

        app = FastAPI()
        app.include_router(jobs.router, prefix="/api/jobs")
        app.state.settings = {
            "applications_input_dir": str(data),
            "applications_output_dir": None,
        }
        resp = TestClient(app).post(
            "/api/jobs/build/rerun", json={"folder_name": _FOLDER}
        )
        assert resp.status_code == 200, resp.text
        assert captured["entity_dir"] is None
