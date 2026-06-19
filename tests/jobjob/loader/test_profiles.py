#!/usr/bin/env python3
"""Tests for the profile registry resolution."""

from pathlib import Path
from unittest import TestCase, mock

import jobjob.loader.profiles as MOD


class TestListProfiles(TestCase):
    def test_reads_registry_prefix_and_lowercases(self) -> None:
        env = {
            "JOBJOB_PROFILE_DEMO": "~/dev/jobjob-resources-demo",
            "JOBJOB_PROFILE_IC": "/abs/ic",
            "JOBJOB_ACTIVE_PROFILE": "demo",  # not a registry entry
            "UNRELATED": "x",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            profiles = MOD.list_profiles()
        self.assertEqual({"demo", "ic"}, set(profiles))
        self.assertEqual(Path("/abs/ic"), profiles["ic"])
        self.assertEqual(
            Path("~/dev/jobjob-resources-demo").expanduser(),
            profiles["demo"],
        )

    def test_empty_when_no_registry(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual({}, MOD.list_profiles())


class TestActiveProfile(TestCase):
    def test_active_name_lowercased(self) -> None:
        with mock.patch.dict("os.environ", {"JOBJOB_ACTIVE_PROFILE": "Demo"}, clear=True):
            self.assertEqual("demo", MOD.active_profile_name())

    def test_none_when_unset(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(MOD.active_profile_name())

    def test_resolve_active_dir(self) -> None:
        env = {
            "JOBJOB_PROFILE_DEMO": "/repos/demo",
            "JOBJOB_ACTIVE_PROFILE": "demo",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            self.assertEqual(Path("/repos/demo"), MOD.resolve_active_profile_dir())

    def test_resolve_none_when_active_not_registered(self) -> None:
        with mock.patch.dict("os.environ", {"JOBJOB_ACTIVE_PROFILE": "ghost"}, clear=True):
            self.assertIsNone(MOD.resolve_active_profile_dir())


class TestReadEnvKeys(TestCase):
    def test_parses_keys_ignoring_comments(self, *_) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as d:
            p = Path(d, ".env")
            p.write_text('# comment\nA="1"\n\nB=2\nnot a line\n')
            self.assertEqual({"A", "B"}, MOD.read_env_keys(p))

    def test_missing_file_empty(self) -> None:
        self.assertEqual(set(), MOD.read_env_keys(Path("/no/such/file")))

    def test_profile_config_file_layout(self) -> None:
        self.assertEqual(
            Path("/repo/config/.profile"), MOD.profile_config_file(Path("/repo"))
        )


# __END__
