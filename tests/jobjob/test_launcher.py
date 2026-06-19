#!/usr/bin/env python3
"""Tests for the installed-app launcher scaffold."""

from pathlib import Path
from unittest import TestCase, mock

import jobjob.launcher as MOD


class TestScaffold(TestCase):
    """Test function."""

    def _scaffold(self, tmp: Path) -> Path:
        # Point the bundled-static lookup at a temp tree so the test is hermetic.
        static = tmp / "pkg" / "static"
        (static / "content").mkdir(parents=True)
        (static / "reference").mkdir(parents=True)
        (static / "content" / "highlights.toml").write_text("x")
        (static / "reference" / "background.md").write_text("y")
        with mock.patch.object(MOD, "_package_root", return_value=tmp / "pkg"):
            return MOD.scaffold(tmp / "home")

    def test_creates_working_dirs_and_config(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            home = self._scaffold(Path(d))
            with self.subTest("config/.env written"):
                self.assertTrue((home / "config" / ".env").is_file())
            with self.subTest("data dir created"):
                self.assertTrue((home / "data").is_dir())

    def test_env_registers_local_profile_and_paths(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            home = self._scaffold(Path(d))
            env = (home / "config" / ".env").read_text()
            self.assertIn("JOBJOB_ACTIVE_PROFILE=local", env)
            self.assertIn(f"JOBJOB_PROFILE_LOCAL={home / 'profile'}", env)
            self.assertIn(f"DATA_DIR={home / 'data'}", env)

    def test_profile_seeded_from_bundled_static(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            home = self._scaffold(Path(d))
            with self.subTest("content copied"):
                self.assertTrue((home / "profile" / "content" / "highlights.toml").is_file())
            with self.subTest("reference copied"):
                self.assertTrue((home / "profile" / "reference" / "background.md").is_file())
            with self.subTest(".profile template written"):
                self.assertTrue((home / "profile" / "config" / ".profile").is_file())

    def test_idempotent_preserves_existing_files(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            home = self._scaffold(Path(d))
            env_path = home / "config" / ".env"
            env_path.write_text("EDITED")
            # Re-scaffolding must not clobber a user-edited config.
            with mock.patch.object(MOD, "_package_root", return_value=Path(d) / "pkg"):
                MOD.scaffold(home)
            self.assertEqual("EDITED", env_path.read_text())


# __END__
