#!/usr/bin/env python3
"""Tests for the ``_make_build_run`` cache wiring (routers.jobs).

Regression for the removed model-override cache bypass: a per-run model override
must still populate ``use_cache`` from ``settings.cache_enabled`` / ``no_cache``,
not force the run uncached. ``apply_inputs`` is stubbed to capture its kwargs; no
model call, no Drive, no threads.
"""

import jobjob.ailib.client.anthropic as anthropic_mod
import jobjob.apply.workflow as workflow
import jobjob.config as config_mod
import routers.jobs as jobs
from jobjob.config import Settings
from jobjob.structure.applicant import Applicant


def _settings(**overrides) -> Settings:
    kwargs = {
        "applicant": Applicant(),
        "cache_enabled": True,
        "model": "configured-model",
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


def _stub_apply_inputs(monkeypatch, captured):
    def _fake(jd_path, *, use_cache, **kwargs):
        captured["use_cache"] = use_cache
        captured.update(kwargs)
        return {"items": [{"status": "ok", "result": {}}]}

    monkeypatch.setattr(workflow, "apply_inputs", _fake)


class TestMakeApplyRunCaching:
    def test_model_override_still_uses_cache(self, monkeypatch, tmp_path):
        # Regression: before model-scoped-cache, a per-run model override forced
        # use_cache=False. The cache key is now model-scoped, so the override
        # should be cached under its own entry, same as any other run.
        captured: dict = {}
        _stub_apply_inputs(monkeypatch, captured)
        monkeypatch.setattr(config_mod, "load_settings", lambda: _settings())
        monkeypatch.setattr(anthropic_mod, "AnthropicAdapter", lambda **k: object())

        jd_path = tmp_path / "jd.pdf"
        jd_path.write_text("x")

        run = jobs._make_build_run(
            jd_path, skip_drive=True, move_data_dir=None, model="override-model"
        )
        run()

        assert captured["use_cache"] is True

    def test_no_cache_flag_still_disables_cache_with_override(
        self, monkeypatch, tmp_path
    ):
        # The explicit no_cache flag must still win even with a model override.
        captured: dict = {}
        _stub_apply_inputs(monkeypatch, captured)
        monkeypatch.setattr(config_mod, "load_settings", lambda: _settings())
        monkeypatch.setattr(anthropic_mod, "AnthropicAdapter", lambda **k: object())

        jd_path = tmp_path / "jd.pdf"
        jd_path.write_text("x")

        run = jobs._make_build_run(
            jd_path,
            skip_drive=True,
            move_data_dir=None,
            model="override-model",
            no_cache=True,
        )
        run()

        assert captured["use_cache"] is False

    def test_cache_disabled_in_settings_still_disables_cache_with_override(
        self, monkeypatch, tmp_path
    ):
        captured: dict = {}
        _stub_apply_inputs(monkeypatch, captured)
        monkeypatch.setattr(
            config_mod, "load_settings", lambda: _settings(cache_enabled=False)
        )
        monkeypatch.setattr(anthropic_mod, "AnthropicAdapter", lambda **k: object())

        jd_path = tmp_path / "jd.pdf"
        jd_path.write_text("x")

        run = jobs._make_build_run(
            jd_path, skip_drive=True, move_data_dir=None, model="override-model"
        )
        run()

        assert captured["use_cache"] is False


class TestMakeApplyRunIdentityForwarding:
    """_make_build_run forwards the persistent-identity kwargs to apply_inputs
    (application-identity, phase 1): identity must land in the mirror, not the
    ephemeral output dir."""

    def test_forwards_applications_output_dir_and_entity_dir(
        self, monkeypatch, tmp_path
    ):
        captured: dict = {}
        _stub_apply_inputs(monkeypatch, captured)
        mirror = tmp_path / "mirror"
        monkeypatch.setattr(
            config_mod,
            "load_settings",
            lambda: _settings(applications_output_dir=mirror),
        )
        monkeypatch.setattr(anthropic_mod, "AnthropicAdapter", lambda **k: object())

        jd_path = tmp_path / "jd.pdf"
        jd_path.write_text("x")
        entity_dir = mirror / "Acme - Role"

        run = jobs._make_build_run(
            jd_path,
            skip_drive=True,
            move_data_dir=None,
            entity_dir=entity_dir,
        )
        run()

        assert captured["applications_output_dir"] == mirror
        assert captured["entity_dir"] == entity_dir

    def test_fresh_build_forwards_none_entity_dir(self, monkeypatch, tmp_path):
        captured: dict = {}
        _stub_apply_inputs(monkeypatch, captured)
        mirror = tmp_path / "mirror"
        monkeypatch.setattr(
            config_mod,
            "load_settings",
            lambda: _settings(applications_output_dir=mirror),
        )
        monkeypatch.setattr(anthropic_mod, "AnthropicAdapter", lambda **k: object())

        jd_path = tmp_path / "jd.pdf"
        jd_path.write_text("x")

        run = jobs._make_build_run(jd_path, skip_drive=True, move_data_dir=None)
        run()

        assert captured["applications_output_dir"] == mirror
        assert captured["entity_dir"] is None


# __END__
