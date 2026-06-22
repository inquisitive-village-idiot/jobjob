#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from unittest import TestCase, mock

import jobjob.loader.location as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


# Content
# ======================================================================


class TestGetContentDir(ThisTestCase):
    """Test function."""

    def test_raises_if_path_does_not_exist(self) -> None:
        with mock.patch.object(MOD, "get_root_dir") as mobj:
            mobj.return_value = Path("foo")
            with self.assertRaises(FileNotFoundError):
                MOD.get_content_dir()

    def test_returns_expected_path(self) -> None:
        found = MOD.get_content_dir()
        expected = Path(MOD.get_root_dir(), "static/example/content")
        self.assertEqual(expected, found)


class TestGetContentPath(ThisTestCase):
    """Test function."""

    def test_raises_for_unknown_content(self) -> None:
        given = "foo"
        with self.assertRaisesRegex(ValueError, given):
            MOD.get_content_path(given)

    def test_returns_expected_path(self) -> None:
        given = "highlights"
        expected = Path(MOD.get_content_dir(), "highlights.toml")
        found = MOD.get_content_path(given)
        self.assertEqual(expected, found)


# Prompt
# ======================================================================


class TestGetPromptDir(ThisTestCase):
    """Test function."""

    def test_raises_if_path_does_not_exist(self) -> None:
        with mock.patch.object(MOD, "get_root_dir") as mobj:
            mobj.return_value = Path("foo")
            with self.assertRaises(FileNotFoundError):
                MOD.get_prompt_dir()

    def test_returns_expected_path(self) -> None:
        found = MOD.get_prompt_dir()
        expected = Path(MOD.get_root_dir(), "jobjob/prompts")
        self.assertEqual(expected, found)


class TestGetPromptPath(ThisTestCase):
    """Test function."""

    def test_raises_for_unknown_content(self) -> None:
        given = "foo"
        with self.assertRaisesRegex(ValueError, given):
            MOD.get_prompt_path(given)

    def test_returns_expected_path(self) -> None:
        given = "job_description"
        expected = Path(MOD.get_prompt_dir(), "job_description.txt")
        found = MOD.get_prompt_path(given)
        self.assertEqual(expected, found)


# Root
# ======================================================================


class TestGetRoot(ThisTestCase):
    """Test function."""

    def test_returns_expected_path(self) -> None:
        result = MOD.get_root_dir()

        # it should return the same dir these tests are found in
        # therefore, this file should be relative to the result
        this_file = Path(__file__)
        idx = this_file.parts.index("tests")
        try:
            relpath = this_file.relative_to(result)
        except ValueError as err:
            msg = f"Unexpected result: {result} is not relative to {this_file}"
            raise AssertionError(msg) from err

        expected = Path(*this_file.parts[idx:])
        found = relpath
        self.assertEqual(expected, found)


class TestGetStaticDir(ThisTestCase):
    """Test function."""

    def test_raises_if_path_does_not_exist(self) -> None:
        with mock.patch.object(MOD, "get_root_dir") as mobj:
            mobj.return_value = Path("foo")
            with self.assertRaises(FileNotFoundError):
                MOD.get_static_dir()

    def test_returns_expected_path(self) -> None:
        found = MOD.get_static_dir()
        expected = Path(MOD.get_root_dir(), "static")
        self.assertEqual(expected, found)


# __END__
