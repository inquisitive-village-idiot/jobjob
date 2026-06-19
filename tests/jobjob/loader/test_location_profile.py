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
                # Falls back to the repo's static/content (which ships defaults).
                self.assertTrue(str(MOD.get_content_dir()).endswith("static/content"))

    def test_no_profile_uses_static(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertTrue(str(MOD.get_reference_dir()).endswith("static/reference"))

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
                self.assertTrue(str(default).endswith("jobjob/prompts/linkedin_profile.txt"))


# __END__
