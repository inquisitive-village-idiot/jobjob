#!/usr/bin/env python3
"""Tests for profile-aware resource resolution in jobjob.loader.location."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import jobjob.loader.location as MOD


def _profile_env(repo: Path) -> dict:
    return {
        "JOBJOB_PROFILE_TEST": str(repo),
        "JOBJOB_ACTIVE_PROFILE": "test",
    }


class TestProfileResolution(TestCase):
    def test_content_resolves_to_profile_when_present(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "content").mkdir()
            hl = repo / "content" / "highlights.toml"
            hl.write_text("[tool.highlights]\n")
            with mock.patch.dict("os.environ", _profile_env(repo), clear=True):
                self.assertEqual(repo / "content", MOD.get_content_dir())
                self.assertEqual(hl, MOD.get_content_path("highlights"))

    def test_content_falls_back_to_static_when_profile_lacks_it(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d)  # no content/ subdir
            with mock.patch.dict("os.environ", _profile_env(repo), clear=True):
                # Falls back to the bundled example (static/example/content).
                self.assertTrue(
                    str(MOD.get_content_dir()).endswith("static/example/content")
                )

    def test_no_profile_uses_static(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertTrue(
                str(MOD.get_reference_dir()).endswith("static/example/reference")
            )

    def test_prompt_override_wins_else_default(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "prompt").mkdir()
            override = repo / "prompt" / "job_description.txt"
            override.write_text("custom prompt")
            with mock.patch.dict("os.environ", _profile_env(repo), clear=True):
                # Provided override wins.
                self.assertEqual(override, MOD.get_prompt_path("job_description"))
                # A prompt the profile does NOT override falls back to jobjob default.
                default = MOD.get_prompt_path("linkedin_profile")
                self.assertTrue(
                    str(default).endswith("jobjob/prompts/linkedin_profile.txt")
                )

    def test_configured_content_dir_is_used(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "credentials").mkdir()  # renamed content dir
            (repo / "credentials" / "highlights.toml").write_text("[tool.highlights]\n")
            env = {**_profile_env(repo), "CONTENT_DIR": "credentials"}
            with mock.patch.dict("os.environ", env, clear=True):
                self.assertEqual(repo / "credentials", MOD.get_content_dir())

    def test_configured_reference_dir_is_used(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "refs").mkdir()  # renamed reference dir
            env = {**_profile_env(repo), "REFERENCE_DIR": "refs"}
            with mock.patch.dict("os.environ", env, clear=True):
                self.assertEqual(repo / "refs", MOD.get_reference_dir())

    def test_configured_prompt_dir_is_used(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "prompts_custom").mkdir()
            override = repo / "prompts_custom" / "job_description.txt"
            override.write_text("custom")
            env = {**_profile_env(repo), "PROMPT_DIR": "prompts_custom"}
            with mock.patch.dict("os.environ", env, clear=True):
                self.assertEqual(repo / "prompts_custom", MOD.get_prompt_dir())
                self.assertEqual(override, MOD.get_prompt_path("job_description"))

    def test_blank_dir_key_falls_back_to_default(self) -> None:
        with TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "content").mkdir()
            (repo / "content" / "highlights.toml").write_text("[tool.highlights]\n")
            env = {**_profile_env(repo), "CONTENT_DIR": "   "}  # blank -> default
            with mock.patch.dict("os.environ", env, clear=True):
                self.assertEqual(repo / "content", MOD.get_content_dir())


# __END__
