#!/usr/bin/env python3
"""Tests for re-run source-JD resolution (_find_rerun_jd)."""

from routers.jobs import _find_rerun_jd

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
