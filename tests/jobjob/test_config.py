#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from unittest import TestCase, mock

import jobjob.config as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def load_with_env(self, env: dict) -> MOD.Settings:
        # NOTE: patch load_dotenv so a real config/.env is never sourced in tests.
        with mock.patch.object(MOD, "load_dotenv"):
            with mock.patch.dict("os.environ", env, clear=True):
                return MOD.load_settings()


class TestLoadSettings(ThisTestCase):
    """Test function."""

    def test_reads_applicant_from_env(self) -> None:
        settings = self.load_with_env(
            {
                MOD.ENV_APPLICANT_NAME: "Ada Lovelace",
                MOD.ENV_APPLICANT_EMAIL: "ada@example.com",
            }
        )
        self.assertEqual("Ada Lovelace", settings.applicant.name)
        self.assertEqual("ada@example.com", settings.applicant.email)

    def test_reads_industry_from_env(self) -> None:
        settings = self.load_with_env({MOD.ENV_INDUSTRY: "science journalism"})
        self.assertEqual("science journalism", settings.industry)

    def test_industry_none_when_unset(self) -> None:
        self.assertIsNone(self.load_with_env({}).industry)

    def test_industry_blank_is_none(self) -> None:
        # A whitespace-only value is treated as "no domain hint", not "".
        self.assertIsNone(self.load_with_env({MOD.ENV_INDUSTRY: "   "}).industry)

    def test_industry_is_profile_scoped(self) -> None:
        self.assertIn(MOD.ENV_INDUSTRY, MOD.PROFILE_KEYS)
        self.assertNotIn(MOD.ENV_INDUSTRY, MOD.APP_KEYS)

    def test_defaults_model_when_unset(self) -> None:
        settings = self.load_with_env({})
        self.assertEqual(MOD.DEFAULT_MODEL, settings.model)

    def test_honors_model_env(self) -> None:
        settings = self.load_with_env({MOD.ENV_MODEL: "claude-opus-4-8"})
        self.assertEqual("claude-opus-4-8", settings.model)

    def test_cache_enabled_parsing(self) -> None:
        with self.subTest("default true"):
            self.assertTrue(self.load_with_env({}).cache_enabled)
        with self.subTest("explicit false"):
            settings = self.load_with_env({MOD.ENV_CACHE_ENABLED: "false"})
            self.assertFalse(settings.cache_enabled)

    def test_google_settings_from_env(self) -> None:
        settings = self.load_with_env(
            {
                MOD.ENV_RESUME_TEMPLATE_ID: "TPL",
                MOD.ENV_APPLICATIONS_OUTPUT_DRIVE_ID: "FOLDER",
                MOD.ENV_GOOGLE_CREDENTIALS_FILE: "~/creds.json",
            }
        )
        self.assertEqual("TPL", settings.google.template_id)
        self.assertEqual("FOLDER", settings.applications_output_drive_id)
        self.assertEqual(
            Path("~/creds.json").expanduser(), settings.google.credentials_file
        )

    def test_no_api_key_is_none(self) -> None:
        self.assertIsNone(self.load_with_env({}).anthropic_api_key)

    def test_reads_anthropic_base_url(self) -> None:
        settings = self.load_with_env(
            {MOD.ENV_ANTHROPIC_BASE_URL: "http://localhost:3000"}
        )
        self.assertEqual("http://localhost:3000", settings.anthropic_base_url)

    def test_base_url_none_when_unset(self) -> None:
        self.assertIsNone(self.load_with_env({}).anthropic_base_url)

    def test_base_url_is_app_scoped(self) -> None:
        self.assertIn(MOD.ENV_ANTHROPIC_BASE_URL, MOD.APP_KEYS)
        self.assertNotIn(MOD.ENV_ANTHROPIC_BASE_URL, MOD.PROFILE_KEYS)


class TestIoRenameFallback(ThisTestCase):
    """The per-component rename keeps deprecated keys working (load-time fallback)."""

    def setUp(self) -> None:
        # The deprecation log is once-per-process; reset so each test can assert it.
        MOD._DEPRECATION_WARNED.clear()

    def test_new_key_wins(self) -> None:
        s = self.load_with_env(
            {
                MOD.ENV_APPLICATIONS_INPUT_DIR: "/new",
                MOD.ENV_DATA_DIR: "/old",
            }
        )
        self.assertEqual(Path("/new"), s.applications_input_dir)

    def test_old_key_fallback(self) -> None:
        s = self.load_with_env({MOD.ENV_DATA_DIR: "/old"})
        self.assertEqual(Path("/old"), s.applications_input_dir)

    def test_all_four_old_keys_fall_back(self) -> None:
        s = self.load_with_env(
            {
                MOD.ENV_DATA_DIR: "/in",
                MOD.ENV_APPLICATIONS_LOCAL_DIR: "/mirror",
                MOD.ENV_APPLICATIONS_FOLDER_ID: "DRIVE",
                MOD.ENV_LINKEDIN_SHEET_ID: "SHEET",
            }
        )
        self.assertEqual(Path("/in"), s.applications_input_dir)
        self.assertEqual(Path("/mirror"), s.applications_output_dir)
        self.assertEqual("DRIVE", s.applications_output_drive_id)
        self.assertEqual("SHEET", s.enrichment_output_sheet_id)

    def test_blank_new_key_falls_back_to_old(self) -> None:
        s = self.load_with_env(
            {
                MOD.ENV_APPLICATIONS_OUTPUT_DRIVE_ID: "  ",
                MOD.ENV_APPLICATIONS_FOLDER_ID: "D",
            }
        )
        self.assertEqual("D", s.applications_output_drive_id)

    def test_deprecation_logged_once(self) -> None:
        with self.assertLogs("jobjob.config", level="WARNING") as cm:
            with mock.patch.object(MOD, "load_dotenv"):
                with mock.patch.dict(
                    "os.environ", {MOD.ENV_DATA_DIR: "/old"}, clear=True
                ):
                    MOD.load_settings()
                    MOD.load_settings()  # second load must not warn again
        warnings = [m for m in cm.output if "DATA_DIR" in m]
        self.assertEqual(1, len(warnings))
        self.assertIn("APPLICATIONS_INPUT_DIR", warnings[0])

    def test_enrichment_input_defaults_to_applications_input(self) -> None:
        s = self.load_with_env({MOD.ENV_APPLICATIONS_INPUT_DIR: "/apps"})
        self.assertEqual(Path("/apps"), s.enrichment_input_dir)

    def test_enrichment_input_inherits_resolved_old_applications_input(self) -> None:
        # ENRICHMENT_INPUT_DIR unset, new applications key unset, only old DATA_DIR set:
        # enrichment inherits the applications input AFTER its own old-name fallback.
        s = self.load_with_env({MOD.ENV_DATA_DIR: "/old"})
        self.assertEqual(Path("/old"), s.enrichment_input_dir)

    def test_enrichment_input_own_key_wins(self) -> None:
        s = self.load_with_env(
            {
                MOD.ENV_APPLICATIONS_INPUT_DIR: "/apps",
                MOD.ENV_ENRICHMENT_INPUT_DIR: "/enrich",
            }
        )
        self.assertEqual(Path("/enrich"), s.enrichment_input_dir)
        self.assertEqual(Path("/apps"), s.applications_input_dir)

    def test_default_input_when_unset(self) -> None:
        s = self.load_with_env({})
        self.assertEqual(MOD.DEFAULT_INPUT_DIR, s.applications_input_dir)
        self.assertEqual(MOD.DEFAULT_INPUT_DIR, s.enrichment_input_dir)

    def test_deprecated_aliases_still_app_scoped(self) -> None:
        for key in MOD.RENAMED_KEYS:
            self.assertIn(key, MOD.APP_KEYS)
        for key in MOD.RENAMED_KEYS.values():
            self.assertIn(key, MOD.APP_KEYS)


class TestTwoTierLoad(TestCase):
    """Two-tier app + profile config load, validated as disjoint."""

    def _build(self, tmp: Path, app_lines: list[str], profile_lines: list[str]):
        """Write an app config + a 'demo' profile repo; return the app path."""
        repo = tmp / "jobjob-resources-demo"
        (repo / "config").mkdir(parents=True)
        (repo / "config" / ".profile").write_text("\n".join(profile_lines) + "\n")
        app = tmp / "config" / ".env"
        app.parent.mkdir(parents=True)
        registry = [
            f'JOBJOB_PROFILE_DEMO="{repo}"',
            'JOBJOB_ACTIVE_PROFILE="demo"',
        ]
        app.write_text("\n".join(app_lines + registry) + "\n")
        return app, repo

    def test_loads_app_and_profile(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            app, repo = self._build(
                tmp,
                [
                    'CLAUDE_MODEL="claude-opus-4-8"',
                    'APPLICATIONS_OUTPUT_DRIVE_ID="FOLDER"',
                ],
                ['APPLICANT_NAME="Ada Lovelace"', 'RESUME_TEMPLATE_ID="TPL"'],
            )
            with mock.patch.dict("os.environ", {}, clear=True):
                settings = MOD.load_settings(app_config=app)
            self.assertEqual("demo", settings.profile_name)
            self.assertEqual(repo, settings.profile_dir)
            self.assertEqual("Ada Lovelace", settings.applicant.name)  # from profile
            self.assertEqual("TPL", settings.google.template_id)  # from profile
            self.assertEqual("claude-opus-4-8", settings.model)  # from app
            self.assertEqual("FOLDER", settings.applications_output_drive_id)

    def test_env_var_outranks_config_file(self) -> None:
        # Priority: env > config file. A real env var wins over the .env file even
        # for the same key.
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            app, _ = self._build(
                tmp,
                ['APPLICATIONS_INPUT_DIR="/from-file"'],
                ['APPLICANT_NAME="A"'],
            )
            with mock.patch.dict(
                "os.environ", {"APPLICATIONS_INPUT_DIR": "/from-env"}, clear=True
            ):
                settings = MOD.load_settings(app_config=app)
            self.assertEqual(Path("/from-env"), settings.applications_input_dir)

    def test_env_var_deprecated_name_outranks_config_file_new_name(self) -> None:
        # A deprecated name set as a real env var (a contextual override) still
        # outranks the new name sitting in the config file: env > file dominates the
        # name-version preference. The deprecation warning fires.
        import tempfile

        MOD._DEPRECATION_WARNED.clear()
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            app, _ = self._build(
                tmp,
                ['APPLICATIONS_INPUT_DIR="/from-file-new"'],
                ['APPLICANT_NAME="A"'],
            )
            with mock.patch.dict(
                "os.environ", {"DATA_DIR": "/from-env-old"}, clear=True
            ):
                settings = MOD.load_settings(app_config=app)
            self.assertEqual(Path("/from-env-old"), settings.applications_input_dir)

    def test_config_file_new_name_outranks_deprecated_file_name(self) -> None:
        # Within the config file (no env override), the new name wins over the old.
        import tempfile

        MOD._DEPRECATION_WARNED.clear()
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            app, _ = self._build(
                tmp,
                ['APPLICATIONS_INPUT_DIR="/new"', 'DATA_DIR="/old"'],
                ['APPLICANT_NAME="A"'],
            )
            with mock.patch.dict("os.environ", {}, clear=True):
                settings = MOD.load_settings(app_config=app)
            self.assertEqual(Path("/new"), settings.applications_input_dir)

    def test_rejects_profile_key_in_app_config(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            app, _ = self._build(
                tmp, ['APPLICANT_NAME="leak"'], ['RESUME_TEMPLATE_ID="TPL"']
            )
            with mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(ValueError):
                    MOD.load_settings(app_config=app)

    def test_rejects_app_key_in_profile_config(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            app, _ = self._build(
                tmp, ['CLAUDE_MODEL="m"'], ['DATA_DIR="/leak"', 'APPLICANT_NAME="A"']
            )
            with mock.patch.dict("os.environ", {}, clear=True):
                with self.assertRaises(ValueError):
                    MOD.load_settings(app_config=app)

    def test_app_profile_key_sets_are_disjoint(self) -> None:
        self.assertEqual(frozenset(), MOD.APP_KEYS & MOD.PROFILE_KEYS)


# __END__
