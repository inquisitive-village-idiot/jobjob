#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import jobjob.storage.local as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def get_tmpdir(self) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)

    def make_source_file(self, root: Path, name: str, text: str = "x") -> Path:
        path = root / name
        path.write_text(text)
        return path


class TestPlace(ThisTestCase):
    """Test LocalStorageAdapter.place."""

    def test_moves_source_into_root_under_given_name(self) -> None:
        scratch = self.get_tmpdir()
        root = self.get_tmpdir() / "Acme - Engineer"
        source = self.make_source_file(scratch, "scratch.docx", "content")
        adapter = MOD.LocalStorageAdapter(root)

        found = adapter.place(source, "TilaMer_Resume.docx")

        with self.subTest("returns the placed artifact"):
            self.assertEqual("TilaMer_Resume.docx", found.name)
            self.assertEqual(str(root / "TilaMer_Resume.docx"), found.location)
        with self.subTest("moved (not copied) — source no longer exists"):
            self.assertFalse(source.exists())
        with self.subTest("content landed at the destination"):
            self.assertEqual("content", (root / "TilaMer_Resume.docx").read_text())

    def test_creates_root_when_absent(self) -> None:
        root = self.get_tmpdir() / "new" / "Acme - Engineer"
        source = self.make_source_file(self.get_tmpdir(), "x.pdf")
        adapter = MOD.LocalStorageAdapter(root)

        adapter.place(source, "x.pdf")

        self.assertTrue(root.is_dir())

    def test_no_op_when_source_already_is_destination(self) -> None:
        # A caller that wrote directly into the entity root (source IS the
        # destination) must not error trying to "move" a file onto itself.
        root = self.get_tmpdir()
        root.mkdir(exist_ok=True)
        existing = self.make_source_file(root, "already-here.json")
        adapter = MOD.LocalStorageAdapter(root)

        found = adapter.place(existing, "already-here.json")

        self.assertTrue(existing.is_file())
        self.assertEqual(str(existing), found.location)


class TestExists(ThisTestCase):
    """Test LocalStorageAdapter.exists."""

    def test_true_when_present(self) -> None:
        root = self.get_tmpdir()
        self.make_source_file(root, "summary.json")
        adapter = MOD.LocalStorageAdapter(root)
        self.assertTrue(adapter.exists("summary.json"))

    def test_false_when_absent(self) -> None:
        adapter = MOD.LocalStorageAdapter(self.get_tmpdir())
        self.assertFalse(adapter.exists("summary.json"))

    def test_false_when_root_does_not_exist_yet(self) -> None:
        adapter = MOD.LocalStorageAdapter(self.get_tmpdir() / "not-yet-created")
        self.assertFalse(adapter.exists("summary.json"))


class TestArchiveExecution(ThisTestCase):
    """Test LocalStorageAdapter.archive_execution."""

    def test_moves_root_entries_into_archive_timestamp_dir(self) -> None:
        root = self.get_tmpdir()
        self.make_source_file(root, "summary.json", '{"a": 1}')
        self.make_source_file(root, "TilaMer_Resume.pdf", "resume")
        adapter = MOD.LocalStorageAdapter(root)

        moved = adapter.archive_execution("2026-07-05T09.12.03")

        archive_dir = root / "archive" / "2026-07-05T09.12.03"
        with self.subTest("both files moved"):
            self.assertEqual(
                {"summary.json", "TilaMer_Resume.pdf"}, {m.name for m in moved}
            )
        with self.subTest("files present at the archive path"):
            self.assertTrue((archive_dir / "summary.json").is_file())
            self.assertEqual("resume", (archive_dir / "TilaMer_Resume.pdf").read_text())
        with self.subTest("root no longer holds the moved files"):
            self.assertFalse((root / "summary.json").exists())
            self.assertFalse((root / "TilaMer_Resume.pdf").exists())

    def test_excludes_entity_and_source_tier_files(self) -> None:
        root = self.get_tmpdir()
        self.make_source_file(root, "metadata.json")
        self.make_source_file(root, "source.json")
        self.make_source_file(root, "summary.json")
        adapter = MOD.LocalStorageAdapter(root)

        adapter.archive_execution("ts1")

        with self.subTest("entity/source tier files stay at root"):
            self.assertTrue((root / "metadata.json").is_file())
            self.assertTrue((root / "source.json").is_file())
        with self.subTest("execution artifact moved"):
            self.assertFalse((root / "summary.json").exists())

    def test_never_nests_archive_within_archive(self) -> None:
        root = self.get_tmpdir()
        self.make_source_file(root, "summary.json")
        adapter = MOD.LocalStorageAdapter(root)
        adapter.archive_execution("ts1")

        # A second archive call must not sweep the first archive/ dir into a
        # nested archive/archive/....
        self.make_source_file(root, "summary.json")
        adapter.archive_execution("ts2")

        self.assertFalse((root / "archive" / "ts2" / "archive").exists())
        self.assertTrue((root / "archive" / "ts1" / "summary.json").is_file())
        self.assertTrue((root / "archive" / "ts2" / "summary.json").is_file())

    def test_no_op_when_root_does_not_exist(self) -> None:
        adapter = MOD.LocalStorageAdapter(self.get_tmpdir() / "never-built")
        self.assertEqual([], adapter.archive_execution("ts1"))

    def test_no_op_when_nothing_to_archive(self) -> None:
        # A fresh entity folder holding only metadata.json/source.json (no
        # execution yet) has nothing to move.
        root = self.get_tmpdir()
        self.make_source_file(root, "metadata.json")
        adapter = MOD.LocalStorageAdapter(root)

        self.assertEqual([], adapter.archive_execution("ts1"))
        self.assertFalse((root / "archive").exists())


class TestListExecutions(ThisTestCase):
    """Test LocalStorageAdapter.list_executions."""

    def test_empty_when_no_archive_dir(self) -> None:
        adapter = MOD.LocalStorageAdapter(self.get_tmpdir())
        self.assertEqual([], adapter.list_executions())

    def test_returns_sorted_timestamp_dirs(self) -> None:
        root = self.get_tmpdir()
        (root / "archive" / "2026-07-05T09.12.03").mkdir(parents=True)
        (root / "archive" / "2026-01-01T00.00.00").mkdir(parents=True)
        adapter = MOD.LocalStorageAdapter(root)

        found = adapter.list_executions()

        self.assertEqual(["2026-01-01T00.00.00", "2026-07-05T09.12.03"], found)

    def test_ignores_non_directory_entries(self) -> None:
        root = self.get_tmpdir()
        archive = root / "archive"
        archive.mkdir(parents=True)
        (archive / "stray.txt").write_text("x")
        adapter = MOD.LocalStorageAdapter(root)

        self.assertEqual([], adapter.list_executions())


# __END__
