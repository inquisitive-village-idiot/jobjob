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

    @staticmethod
    def _local(home: Path) -> Path:
        return home / "profiles" / "local"

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
            self.assertIn(f"JOBJOB_PROFILE_LOCAL={self._local(home)}", env)
            self.assertIn(f"APPLICATIONS_INPUT_DIR={home / 'data'}", env)

    def test_local_profile_is_blank_skeleton_not_tila(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            home = self._scaffold(Path(d))
            local = self._local(home)
            with self.subTest("content TOMLs present"):
                self.assertTrue((local / "content" / "highlights.toml").is_file())
                self.assertTrue((local / "content" / "skills.toml").is_file())
                self.assertTrue((local / "content" / "templates.toml").is_file())
            with self.subTest("reference + config present"):
                self.assertTrue((local / "reference" / "background.md").is_file())
                self.assertTrue((local / "config" / ".profile").is_file())
            with self.subTest("no Tila example content leaked in"):
                # The blank skeleton must not carry the example persona's highlight id.
                text = (local / "content" / "highlights.toml").read_text()
                self.assertNotIn("half_life_column", text)

    def test_migrates_legacy_profile_dir(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "home"
            (home / "config").mkdir(parents=True)
            (home / "profile" / "content").mkdir(parents=True)
            (home / "profile" / "content" / "highlights.toml").write_text("legacy")
            (home / "config" / ".env").write_text(
                f"JOBJOB_PROFILE_LOCAL={home / 'profile'}\n"
                "JOBJOB_ACTIVE_PROFILE=local\n"
            )
            with mock.patch.object(MOD, "_package_root", return_value=Path(d) / "pkg"):
                MOD.scaffold(home)
            with self.subTest("moved to profiles/local"):
                self.assertFalse((home / "profile").exists())
                self.assertEqual(
                    "legacy",
                    (self._local(home) / "content" / "highlights.toml").read_text(),
                )
            with self.subTest("env path rewritten"):
                self.assertIn(
                    f"JOBJOB_PROFILE_LOCAL={self._local(home)}",
                    (home / "config" / ".env").read_text(),
                )

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
