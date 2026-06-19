#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import jobjob.loader.loadreference as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def get_tmpdir(self) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)


class TestLoadReferenceDocumentsStatic(ThisTestCase):
    """Test against the real static/reference directory."""

    def setUp(self) -> None:
        self.result = MOD.load_reference_documents()

    def test_loads_writing_style(self) -> None:
        self.assertTrue(self.result.writing_style)

    def test_loads_cover_letter_examples(self) -> None:
        self.assertTrue(self.result.cover_letter_examples)

    def test_loads_star_examples(self) -> None:
        self.assertTrue(self.result.star_examples)


class TestLoadReferenceDocumentsTmp(ThisTestCase):
    """Test against a controlled temp directory."""

    def test_missing_dir_yields_empty_docs(self) -> None:
        missing = Path(self.get_tmpdir(), "does-not-exist")
        result = MOD.load_reference_documents(reference_dir=missing)
        found = (
            result.background,
            result.cover_letter_examples,
            result.star_examples,
            result.writing_style,
        )
        self.assertEqual((None, None, None, None), found)

    def test_reads_background_and_caps_cover_letters(self) -> None:
        ref = self.get_tmpdir()
        Path(ref, "background.md").write_text("career narrative")
        cl_dir = Path(ref, "cover_letters")
        cl_dir.mkdir()
        for i in range(4):
            Path(cl_dir, f"cl_{i}.txt").write_text(f"letter {i}")

        result = MOD.load_reference_documents(reference_dir=ref, max_cover_letters=2)

        with self.subTest("background"):
            self.assertEqual("career narrative", result.background)
        with self.subTest("cover letters capped and labeled"):
            self.assertIn("=== cl_0 ===", result.cover_letter_examples)
            self.assertIn("=== cl_1 ===", result.cover_letter_examples)
            self.assertNotIn("cl_2", result.cover_letter_examples)


# __END__
