#!/usr/bin/env python3
"""Tests for the config service schema (services.config_service)."""

from jobjob.config import APP_KEYS
from services.config_service import read_config, write_config


class TestAnthropicBaseUrl:
    """ANTHROPIC_BASE_URL is surfaced as an optional, non-secret AI field."""

    def test_exposed_in_app_scope(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("")
        cfg = read_config(env, keys=APP_KEYS)
        field = cfg["ANTHROPIC_BASE_URL"]
        assert field["group"] == "AI"
        assert field["required"] is False
        assert field["is_secret"] is False

    def test_blank_is_not_set(self, tmp_path):
        # Unset/blank must read as not-set so jobjob defaults to Anthropic.
        env = tmp_path / ".env"
        env.write_text("")
        assert read_config(env, keys=APP_KEYS)["ANTHROPIC_BASE_URL"]["is_set"] is False

    def test_writable_and_value_visible(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("")
        write_config(env, {"ANTHROPIC_BASE_URL": "http://localhost:3000"}, APP_KEYS)
        field = read_config(env, keys=APP_KEYS)["ANTHROPIC_BASE_URL"]
        assert field["is_set"] is True
        assert field["value"] == "http://localhost:3000"
