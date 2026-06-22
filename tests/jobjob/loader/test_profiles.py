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


class TestBundledExample(TestCase):
    def test_bundled_example_dir_is_isolated_subdir(self) -> None:
        d = MOD.bundled_example_dir()
        self.assertIsNotNone(d)
        self.assertEqual("example", d.name)
        self.assertEqual("static", d.parent.name)
        self.assertTrue((d / "content").is_dir())

    def test_all_profiles_injects_example(self) -> None:
        with mock.patch.dict("os.environ", {"JOBJOB_PROFILE_DEMO": "/x"}, clear=True):
            allp = MOD.all_profiles()
        self.assertIn(MOD.EXAMPLE_PROFILE_NAME, allp)
        self.assertIn("demo", allp)

    def test_registry_overrides_example(self) -> None:
        with mock.patch.dict(
            "os.environ", {"JOBJOB_PROFILE_EXAMPLE": "/custom"}, clear=True
        ):
            self.assertEqual(Path("/custom"), MOD.all_profiles()["example"])

    def test_resolve_active_can_select_example(self) -> None:
        with mock.patch.dict(
            "os.environ", {"JOBJOB_ACTIVE_PROFILE": "example"}, clear=True
        ):
            self.assertEqual(
                MOD.bundled_example_dir(), MOD.resolve_active_profile_dir()
            )


class TestBuildProfiles(TestCase):
    """``build_profiles`` carries read_only/owned, resolved once at load time."""

    def test_example_is_read_only_not_owned(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            profiles = MOD.build_profiles(Path("/home/profiles"))
        example = profiles["example"]
        self.assertTrue(example.read_only)
        self.assertFalse(example.owned)
        self.assertEqual(MOD.bundled_example_dir(), example.path)

    def test_owned_when_under_base(self) -> None:
        base = Path("/home/profiles")
        env = {"JOBJOB_PROFILE_MINE": str(base / "mine")}
        with mock.patch.dict("os.environ", env, clear=True):
            profiles = MOD.build_profiles(base)
        mine = profiles["mine"]
        self.assertFalse(mine.read_only)
        self.assertTrue(mine.owned)

    def test_external_dir_not_owned(self) -> None:
        env = {"JOBJOB_PROFILE_EXT": "/elsewhere/ext"}
        with mock.patch.dict("os.environ", env, clear=True):
            profiles = MOD.build_profiles(Path("/home/profiles"))
        ext = profiles["ext"]
        self.assertFalse(ext.read_only)
        self.assertFalse(ext.owned)

    def test_no_base_means_nothing_owned(self) -> None:
        env = {"JOBJOB_PROFILE_MINE": "/home/profiles/mine"}
        with mock.patch.dict("os.environ", env, clear=True):
            profiles = MOD.build_profiles(None)
        self.assertFalse(profiles["mine"].owned)


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
