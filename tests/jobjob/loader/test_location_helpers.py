#!/usr/bin/env python3
"""Tests for location.py private helpers and path-resolution edge cases.

These tests bypass the get_root_dir() bug by using mock.patch or by computing
paths relative to this file's known location. They cover branches that the
existing test_location.py tests cannot reach due to the root-dir caching issue.
"""

import logging
from pathlib import Path
from unittest import TestCase, mock

import jobjob.loader.location as MOD

LOGGER = logging.getLogger(__name__)

# The actual project root, resolved relative to this test file's location.
# This bypasses the get_root_dir() bug (which finds the wrong "jobjob" dir).
_TRUE_ROOT = Path(__file__).parent.parent.parent.parent


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def setUp(self) -> None:
        # location getters are @cache'd; clear them so a patched get_root_dir takes
        # effect and a real path cached by another test can't leak in.
        MOD.get_root_dir.cache_clear()
        MOD.get_static_dir.cache_clear()


class TestGetStaticDirHelper(ThisTestCase):
    """Test _get_static_dir private helper."""

    def test_raises_when_dir_does_not_exist(self) -> None:
        with mock.patch.object(MOD, "get_root_dir", return_value=Path("/nonexistent")):
            with self.assertRaises(FileNotFoundError):
                MOD._get_static_dir("content")

    def test_returns_path_when_dir_exists(self) -> None:
        with mock.patch.object(MOD, "get_root_dir", return_value=_TRUE_ROOT):
            result = MOD._get_static_dir("content")
        self.assertEqual(_TRUE_ROOT / "static" / "content", result)


class TestGetStaticPathHelper(ThisTestCase):
    """Test _get_static_path private helper."""

    def test_raises_for_unknown_stem(self) -> None:
        with mock.patch.object(MOD, "get_root_dir", return_value=_TRUE_ROOT):
            with self.assertRaisesRegex(ValueError, "nosuchfile"):
                MOD._get_static_path("content", "nosuchfile")

    def test_returns_correct_path_for_known_stem(self) -> None:
        with mock.patch.object(MOD, "get_root_dir", return_value=_TRUE_ROOT):
            result = MOD._get_static_path("content", "highlights")
        self.assertEqual(_TRUE_ROOT / "static" / "content" / "highlights.toml", result)


class TestGetStaticDir(ThisTestCase):
    """Test get_static_dir."""

    def test_raises_when_static_dir_missing(self) -> None:
        with mock.patch.object(MOD, "get_root_dir", return_value=Path("/nonexistent")):
            with self.assertRaises(FileNotFoundError):
                MOD.get_static_dir()

    def test_returns_static_dir(self) -> None:
        with mock.patch.object(MOD, "get_root_dir", return_value=_TRUE_ROOT):
            result = MOD.get_static_dir()
        self.assertEqual(_TRUE_ROOT / "static", result)


# __END__
