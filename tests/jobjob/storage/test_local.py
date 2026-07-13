#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

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


class TestPromoteExecution(ThisTestCase):
    """Test LocalStorageAdapter.promote_execution (phase 6b)."""

    def test_archives_root_first_then_promotes(self) -> None:
        # Root holds the "current" execution; archive/ts-old holds the one to
        # promote. ids/entity-tier files must stay at root, untouched.
        root = self.get_tmpdir()
        self.make_source_file(root, "metadata.json", '{"entity_id": "abc"}')
        self.make_source_file(root, "source.json", '{"company": "Acme"}')
        self.make_source_file(root, "summary.json", "current")
        (root / "archive" / "ts-old").mkdir(parents=True)
        self.make_source_file(root / "archive" / "ts-old", "summary.json", "old")
        adapter = MOD.LocalStorageAdapter(root)

        with mock.patch.object(MOD, "archive_timestamp", return_value="ts-new"):
            moved = adapter.promote_execution("ts-old")

        with self.subTest("promoted artifact returned"):
            self.assertEqual(["summary.json"], [m.name for m in moved])
        with self.subTest("root now holds the promoted content"):
            self.assertEqual("old", (root / "summary.json").read_text())
        with self.subTest("current root execution was archived first, under ts-new"):
            self.assertEqual(
                "current", (root / "archive" / "ts-new" / "summary.json").read_text()
            )
        with self.subTest("promoted archive dir is gone (no longer archived)"):
            self.assertFalse((root / "archive" / "ts-old").exists())
        with self.subTest("entity/source tier files untouched at root"):
            self.assertTrue((root / "metadata.json").is_file())
            self.assertTrue((root / "source.json").is_file())
        with self.subTest("no data loss: both executions accounted for"):
            self.assertEqual({"ts-new"}, set(adapter.list_executions()))

    def test_note_sidecar_does_not_travel_to_root(self) -> None:
        root = self.get_tmpdir()
        (root / "archive" / "ts-old").mkdir(parents=True)
        self.make_source_file(root / "archive" / "ts-old", "summary.json", "old")
        self.make_source_file(
            root / "archive" / "ts-old", "execution.json", '{"note": "keep me"}'
        )
        adapter = MOD.LocalStorageAdapter(root)

        with mock.patch.object(MOD, "archive_timestamp", return_value="ts-new"):
            adapter.promote_execution("ts-old")

        self.assertFalse((root / "execution.json").exists())

    def test_raises_when_timestamp_not_archived(self) -> None:
        adapter = MOD.LocalStorageAdapter(self.get_tmpdir())
        with self.assertRaises(FileNotFoundError):
            adapter.promote_execution("nope")

    def test_fresh_root_promote_leaves_no_archive_for_empty_root(self) -> None:
        # A fresh entity (nothing at root yet) promoting an archived execution:
        # archive_execution(new_ts) is a no-op, but promote still succeeds.
        root = self.get_tmpdir()
        (root / "archive" / "ts-old").mkdir(parents=True)
        self.make_source_file(root / "archive" / "ts-old", "README.docx", "r")
        adapter = MOD.LocalStorageAdapter(root)

        with mock.patch.object(MOD, "archive_timestamp", return_value="ts-new"):
            moved = adapter.promote_execution("ts-old")

        self.assertEqual(["README.docx"], [m.name for m in moved])
        self.assertEqual("r", (root / "README.docx").read_text())
        self.assertEqual([], adapter.list_executions())


class TestExecutionNote(ThisTestCase):
    """Test LocalStorageAdapter read/write_execution_note (phase 6b)."""

    def make_archived(self, root: Path, ts: str = "ts1") -> None:
        (root / "archive" / ts).mkdir(parents=True)
        self.make_source_file(root / "archive" / ts, "summary.json")

    def test_read_defaults_when_absent(self) -> None:
        root = self.get_tmpdir()
        self.make_archived(root)
        adapter = MOD.LocalStorageAdapter(root)
        self.assertEqual(
            {"note": None, "locked": False}, adapter.read_execution_note("ts1")
        )

    def test_write_then_read_round_trips(self) -> None:
        root = self.get_tmpdir()
        self.make_archived(root)
        adapter = MOD.LocalStorageAdapter(root)

        written = adapter.write_execution_note(
            "ts1", note="kept for the recruiter callback", locked=True
        )

        with self.subTest("write returns the merged dict"):
            self.assertEqual("kept for the recruiter callback", written["note"])
            self.assertTrue(written["locked"])
        with self.subTest("read returns the same"):
            self.assertEqual(written, adapter.read_execution_note("ts1"))

    def test_partial_update_preserves_other_field(self) -> None:
        root = self.get_tmpdir()
        self.make_archived(root)
        adapter = MOD.LocalStorageAdapter(root)
        adapter.write_execution_note("ts1", note="first", locked=True)

        adapter.write_execution_note("ts1", note="second")

        found = adapter.read_execution_note("ts1")
        self.assertEqual("second", found["note"])
        self.assertTrue(found["locked"])  # untouched by the note-only update

    def test_read_tolerates_corrupt_sidecar(self) -> None:
        root = self.get_tmpdir()
        self.make_archived(root)
        (root / "archive" / "ts1" / "execution.json").write_text("not json")
        adapter = MOD.LocalStorageAdapter(root)
        self.assertEqual(
            {"note": None, "locked": False}, adapter.read_execution_note("ts1")
        )

    def test_write_raises_when_timestamp_not_archived(self) -> None:
        adapter = MOD.LocalStorageAdapter(self.get_tmpdir())
        with self.assertRaises(FileNotFoundError):
            adapter.write_execution_note("nope", note="x")


class TestMergeFrom(ThisTestCase):
    """Test LocalStorageAdapter.merge_from (application-identity phase 6c dedup)."""

    def test_absorbs_losers_root_execution_under_fresh_timestamp(self) -> None:
        survivor_root = self.get_tmpdir() / "Acme - Engineer"
        survivor_root.mkdir()
        loser_root = self.get_tmpdir() / "Acme Inc - Engineer"
        loser_root.mkdir()
        self.make_source_file(loser_root, "summary.json", "loser-current")
        self.make_source_file(loser_root, "metadata.json", '{"entity_id": "loser"}')
        survivor = MOD.LocalStorageAdapter(survivor_root)
        loser = MOD.LocalStorageAdapter(loser_root)

        moved = survivor.merge_from(loser, "ts-new")

        with self.subTest("root execution landed in survivor's archive/ts-new"):
            dest = survivor_root / "archive" / "ts-new" / "summary.json"
            self.assertEqual("loser-current", dest.read_text())
        with self.subTest("returned as a moved artifact"):
            self.assertEqual(["summary.json"], [m.name for m in moved])
        with self.subTest("loser's entity-tier file left untouched (caller's job)"):
            self.assertTrue((loser_root / "metadata.json").is_file())
        with self.subTest("loser's root artifact is gone (moved, not copied)"):
            self.assertFalse((loser_root / "summary.json").exists())

    def test_reparents_losers_archived_executions(self) -> None:
        survivor_root = self.get_tmpdir()
        loser_root = self.get_tmpdir()
        (loser_root / "archive" / "ts-old").mkdir(parents=True)
        self.make_source_file(loser_root / "archive" / "ts-old", "summary.json", "old")
        survivor = MOD.LocalStorageAdapter(survivor_root)
        loser = MOD.LocalStorageAdapter(loser_root)

        moved = survivor.merge_from(loser, "ts-new")

        with self.subTest("archived execution re-parented under its own timestamp"):
            dest = survivor_root / "archive" / "ts-old" / "summary.json"
            self.assertEqual("old", dest.read_text())
        with self.subTest("returned as moved"):
            self.assertEqual(["summary.json"], [m.name for m in moved])
        with self.subTest("gone from the loser"):
            self.assertFalse((loser_root / "archive" / "ts-old").exists())

    def test_timestamp_collision_is_suffixed_not_overwritten(self) -> None:
        survivor_root = self.get_tmpdir()
        (survivor_root / "archive" / "ts1").mkdir(parents=True)
        self.make_source_file(
            survivor_root / "archive" / "ts1", "summary.json", "survivor-original"
        )
        loser_root = self.get_tmpdir()
        (loser_root / "archive" / "ts1").mkdir(parents=True)
        self.make_source_file(
            loser_root / "archive" / "ts1", "summary.json", "loser-dup"
        )
        survivor = MOD.LocalStorageAdapter(survivor_root)
        loser = MOD.LocalStorageAdapter(loser_root)

        survivor.merge_from(loser, "ts-new")

        with self.subTest("survivor's original ts1 untouched"):
            self.assertEqual(
                "survivor-original",
                (survivor_root / "archive" / "ts1" / "summary.json").read_text(),
            )
        with self.subTest("loser's ts1 landed under a suffixed name"):
            self.assertEqual(
                "loser-dup",
                (survivor_root / "archive" / "ts1-merged" / "summary.json").read_text(),
            )

    def test_no_op_when_loser_has_nothing(self) -> None:
        survivor_root = self.get_tmpdir()
        survivor_root.mkdir(exist_ok=True)
        loser_root = self.get_tmpdir() / "never-built"
        survivor = MOD.LocalStorageAdapter(survivor_root)
        loser = MOD.LocalStorageAdapter(loser_root)

        moved = survivor.merge_from(loser, "ts-new")

        self.assertEqual([], moved)
        self.assertFalse((survivor_root / "archive").exists())


class TestPurgeExecutions(ThisTestCase):
    """Test LocalStorageAdapter.purge_executions (phase 6b)."""

    def test_purges_unlocked_executions(self) -> None:
        root = self.get_tmpdir()
        (root / "archive" / "ts1").mkdir(parents=True)
        (root / "archive" / "ts2").mkdir(parents=True)
        adapter = MOD.LocalStorageAdapter(root)

        purged = adapter.purge_executions()

        self.assertEqual({"ts1", "ts2"}, set(purged))
        self.assertEqual([], adapter.list_executions())

    def test_locked_execution_survives_purge(self) -> None:
        root = self.get_tmpdir()
        (root / "archive" / "ts1").mkdir(parents=True)
        (root / "archive" / "ts2").mkdir(parents=True)
        adapter = MOD.LocalStorageAdapter(root)
        adapter.write_execution_note("ts2", locked=True)

        purged = adapter.purge_executions()

        with self.subTest("only the unlocked one purged"):
            self.assertEqual(["ts1"], purged)
        with self.subTest("locked execution still present"):
            self.assertEqual(["ts2"], adapter.list_executions())

    def test_no_op_when_no_archive_dir(self) -> None:
        adapter = MOD.LocalStorageAdapter(self.get_tmpdir())
        self.assertEqual([], adapter.purge_executions())


# __END__
