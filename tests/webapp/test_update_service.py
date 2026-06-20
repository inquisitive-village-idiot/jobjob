#!/usr/bin/env python3
"""Tests for the self-update service (no network, no real subprocess)."""

import json

import pytest

from services import update_service as u


class _FakeResp:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener_for(payload: dict):
    def _open(_req, timeout=None):
        return _FakeResp(payload)

    return _open


_PYPI = {
    "info": {"version": "1.2.0"},
    "releases": {
        "1.0.0": [{"upload_time_iso_8601": "2026-06-19T20:00:00Z"}],
        "1.2.0": [{"upload_time_iso_8601": "2026-06-25T12:00:00Z"}],
    },
}


@pytest.fixture(autouse=True)
def _cache_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(u, "_CACHE_FILE", tmp_path / "update.json")


class TestVersionCompare:
    @pytest.mark.parametrize(
        "latest,current,expected",
        [
            ("1.2.0", "1.0.0", True),
            ("1.0.0", "1.0.0", False),
            ("1.0.0", "1.2.0", False),
            ("1.0.10", "1.0.2", True),
        ],
    )
    def test_is_newer(self, latest, current, expected):
        assert u.is_newer(latest, current) is expected

    def test_naive_fallback(self):
        assert u._naive_gt("2.0.0", "1.9.9") is True
        assert u._naive_gt("1.0.0", "1.0.0") is False


class TestCheckForUpdates:
    def test_populates_cache(self):
        cache = u.check_for_updates(_opener=_opener_for(_PYPI))
        assert cache["latest_version"] == "1.2.0"
        assert cache["latest_release_date"] == "2026-06-25T12:00:00Z"
        assert cache["current_release_date"] == "2026-06-19T20:00:00Z"
        assert cache["check_error"] is None
        assert cache["last_checked"]

    def test_network_error_records_and_keeps_prior(self, monkeypatch):
        u.check_for_updates(_opener=_opener_for(_PYPI))  # seed prior latest

        def _boom(_req, timeout=None):
            raise OSError("no network")

        cache = u.check_for_updates(_opener=_boom)
        assert cache["check_error"] == "no network"
        # prior known latest is preserved
        assert cache["latest_version"] == "1.2.0"


class TestGetStatus:
    def test_update_available_flags(self, monkeypatch):
        monkeypatch.setattr(u, "detect_install_method", lambda: "pipx")
        u.check_for_updates(_opener=_opener_for(_PYPI))
        st = u.get_status()
        assert st["current_version"] == u.CURRENT_VERSION
        assert st["latest_version"] == "1.2.0"
        assert st["update_available"] is True
        assert st["can_update"] is True
        assert st["install_method"] == "pipx"

    def test_source_install_cannot_update(self, monkeypatch):
        monkeypatch.setattr(u, "detect_install_method", lambda: "source")
        u.check_for_updates(_opener=_opener_for(_PYPI))
        st = u.get_status()
        assert st["update_available"] is True
        assert st["can_update"] is False

    def test_no_cache_is_safe(self):
        st = u.get_status()
        assert st["latest_version"] is None
        assert st["update_available"] is False
        assert st["last_checked"] is None


class TestApplyUpdate:
    def test_pipx_command(self, monkeypatch):
        monkeypatch.setattr(u, "detect_install_method", lambda: "pipx")
        captured = {}

        class _Proc:
            returncode = 0
            stdout = "upgraded"
            stderr = ""

        def _runner(cmd, **kw):
            captured["cmd"] = cmd
            return _Proc()

        res = u.apply_update(_runner=_runner)
        assert captured["cmd"] == ["pipx", "upgrade", "jobjob"]
        assert res["ok"] is True
        assert "restart" in res["message"].lower()

    def test_pip_command_uses_sys_executable(self, monkeypatch):
        monkeypatch.setattr(u, "detect_install_method", lambda: "pip")
        captured = {}

        class _Proc:
            returncode = 1
            stdout = ""
            stderr = "boom"

        def _runner(cmd, **kw):
            captured["cmd"] = cmd
            return _Proc()

        res = u.apply_update(_runner=_runner)
        assert captured["cmd"][1:] == ["-m", "pip", "install", "--upgrade", "jobjob"]
        assert res["ok"] is False
        assert res["stderr"] == "boom"

    def test_source_install_refuses(self, monkeypatch):
        monkeypatch.setattr(u, "detect_install_method", lambda: "source")
        res = u.apply_update(_runner=lambda *a, **k: None)
        assert res["ok"] is False
        assert "source checkout" in res["message"]


class TestDetectInstallMethod:
    def test_returns_known_value(self):
        assert u.detect_install_method() in {"pipx", "pip", "source"}
