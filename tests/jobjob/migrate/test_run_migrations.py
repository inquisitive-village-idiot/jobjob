#!/usr/bin/env python3
"""Tests for the migration runner and the legacy-profile-layout migration."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jobjob.migrate import run_migrations
from jobjob.migrate._profile_layout import migrate_legacy_profile


class TestLegacyProfileLayout(TestCase):
    def test_moves_profile_to_profiles_local_and_rewrites_registry(self) -> None:
        with TemporaryDirectory() as d:
            home = Path(d)
            (home / "profile" / "content").mkdir(parents=True)
            (home / "profile" / "content" / "highlights.toml").write_text("x")
            (home / "config").mkdir()
            (home / "config" / ".env").write_text(
                f'JOBJOB_PROFILE_LOCAL={home / "profile"}\n'
                'JOBJOB_ACTIVE_PROFILE="local"\n'
            )
            self.assertTrue(migrate_legacy_profile(home))
            target = home / "profiles" / "local"
            self.assertTrue((target / "content" / "highlights.toml").is_file())
            self.assertFalse((home / "profile").exists())
            env = (home / "config" / ".env").read_text()
            self.assertIn(f"JOBJOB_PROFILE_LOCAL={target}", env)

    def test_noop_when_no_legacy_dir(self) -> None:
        with TemporaryDirectory() as d:
            self.assertFalse(migrate_legacy_profile(Path(d)))


class TestRunMigrations(TestCase):
    def test_runs_both_migrations_in_order(self) -> None:
        with TemporaryDirectory() as d:
            home = Path(d)
            (home / "profile").mkdir()
            (home / "config").mkdir()
            (home / "config" / ".env").write_text(
                f'JOBJOB_PROFILE_LOCAL={home / "profile"}\nDATA_DIR="/data"\n'
            )
            applied = run_migrations(home)
            self.assertEqual(["legacy_profile_layout", "env_key_rename"], applied)
            env = (home / "config" / ".env").read_text()
            self.assertIn('APPLICATIONS_INPUT_DIR="/data"', env)
            self.assertTrue((home / "profiles" / "local").is_dir())

    def test_clean_home_applies_nothing(self) -> None:
        with TemporaryDirectory() as d:
            home = Path(d)
            (home / "config").mkdir()
            (home / "config" / ".env").write_text('CLAUDE_MODEL="m"\n')
            self.assertEqual([], run_migrations(home))


# __END__
