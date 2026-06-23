#!/usr/bin/env python3
"""Tests for the deprecated-env-key rename migration."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jobjob.migrate._env_keys import migrate_env_keys


def _write_env(home: Path, body: str) -> Path:
    (home / "config").mkdir(parents=True, exist_ok=True)
    env = home / "config" / ".env"
    env.write_text(body, encoding="utf-8")
    return env


class TestMigrateEnvKeys(TestCase):
    def test_renames_old_keys_preserving_values(self) -> None:
        with TemporaryDirectory() as d:
            home = Path(d)
            env = _write_env(
                home,
                'DATA_DIR="/data"\n'
                'APPLICATIONS_LOCAL_DIR="/mirror"\n'
                'APPLICATIONS_FOLDER_ID="DRIVE"\n'
                'LINKEDIN_SHEET_ID="SHEET"\n',
            )
            self.assertTrue(migrate_env_keys(home))
            text = env.read_text()
            self.assertIn('APPLICATIONS_INPUT_DIR="/data"', text)
            self.assertIn('APPLICATIONS_OUTPUT_DIR="/mirror"', text)
            self.assertIn('APPLICATIONS_OUTPUT_DRIVE_ID="DRIVE"', text)
            self.assertIn('ENRICHMENT_OUTPUT_SHEET_ID="SHEET"', text)
            # Old names are gone.
            self.assertNotIn("DATA_DIR=", text)
            self.assertNotIn("LINKEDIN_SHEET_ID=", text)

    def test_preserves_comments_and_other_keys(self) -> None:
        with TemporaryDirectory() as d:
            home = Path(d)
            env = _write_env(
                home,
                "# a comment\n"
                'CLAUDE_MODEL="m"\n'
                'DATA_DIR="/data"\n'
                'JOBJOB_ACTIVE_PROFILE="local"\n',
            )
            migrate_env_keys(home)
            text = env.read_text()
            self.assertIn("# a comment", text)
            self.assertIn('CLAUDE_MODEL="m"', text)
            self.assertIn('JOBJOB_ACTIVE_PROFILE="local"', text)

    def test_does_not_clobber_existing_new_key(self) -> None:
        with TemporaryDirectory() as d:
            home = Path(d)
            env = _write_env(
                home,
                'APPLICATIONS_INPUT_DIR="/new"\nDATA_DIR="/old"\n',
            )
            migrate_env_keys(home)
            text = env.read_text()
            # New key kept verbatim; old key left as-is (not renamed over the new one).
            self.assertIn('APPLICATIONS_INPUT_DIR="/new"', text)
            self.assertIn('DATA_DIR="/old"', text)

    def test_idempotent(self) -> None:
        with TemporaryDirectory() as d:
            home = Path(d)
            env = _write_env(home, 'DATA_DIR="/data"\n')
            self.assertTrue(migrate_env_keys(home))
            first = env.read_text()
            self.assertFalse(migrate_env_keys(home))  # nothing left to do
            self.assertEqual(first, env.read_text())

    def test_missing_env_is_noop(self) -> None:
        with TemporaryDirectory() as d:
            self.assertFalse(migrate_env_keys(Path(d)))


# __END__
