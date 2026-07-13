#!/usr/bin/env python3
"""Test."""

import json
import logging
from unittest import TestCase, mock

import jobjob.storage.drive as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_service(self) -> mock.MagicMock:
        # NOTE: service.files() returns the same files-resource mock each call,
        #   so per-method return values are easy to configure.
        service = mock.MagicMock()
        self.files = service.files.return_value
        return service

    def set_list(self, files) -> None:
        self.files.list.return_value.execute.return_value = {"files": files}


class TestPlace(ThisTestCase):
    """Test DriveStorageAdapter.place."""

    def test_uploads_via_upload_file(self) -> None:
        service = self.make_service()
        self.set_list([])
        self.files.create.return_value.execute.return_value = {"id": "NEW", "name": "n"}
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        found = adapter.place(
            "/tmp/JD_Acme_Eng.pdf", "JD_Acme_Eng.pdf", _media_cls=mock.MagicMock()
        )

        with self.subTest("returns the placed artifact"):
            self.assertEqual("JD_Acme_Eng.pdf", found.name)
            self.assertEqual("NEW", found.location)
        with self.subTest("created in the scoped folder"):
            _, kwargs = self.files.create.call_args
            self.assertEqual(["FOLDER"], kwargs["body"]["parents"])

    def test_updates_in_place_when_name_exists(self) -> None:
        service = self.make_service()
        self.set_list([{"id": "EX", "name": "JD_Acme_Eng.pdf"}])
        self.files.update.return_value.execute.return_value = {"id": "EX", "name": "n"}
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        found = adapter.place(
            "/tmp/JD_Acme_Eng.pdf", "JD_Acme_Eng.pdf", _media_cls=mock.MagicMock()
        )

        self.assertEqual("EX", found.location)
        self.files.create.assert_not_called()


class TestExists(ThisTestCase):
    """Test DriveStorageAdapter.exists."""

    def test_true_when_present(self) -> None:
        service = self.make_service()
        self.set_list([{"id": "EX", "name": "README"}])
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        self.assertTrue(adapter.exists("README"))

    def test_false_when_absent(self) -> None:
        service = self.make_service()
        self.set_list([])
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        self.assertFalse(adapter.exists("README"))


class TestArchiveExecution(ThisTestCase):
    """Test DriveStorageAdapter.archive_execution: the move-by-id dispatch."""

    def test_moves_each_item_by_id_with_add_and_remove_parents(self) -> None:
        service = self.make_service()

        # Call order inside archive_execution: (1) ensure_subfolder("archive") —
        # not found, created; (2) list the folder's current contents (the items
        # to move); (3) ensure_subfolder(timestamp) under the archive root — not
        # found, created — only reached once there is something to move.
        self.files.list.return_value.execute.side_effect = [
            {"files": []},  # ensure_subfolder("archive"): not found
            {"files": [{"id": "DOC1", "name": "TilaMer_Resume"}]},  # folder contents
            {"files": []},  # ensure_subfolder(timestamp): not found
        ]
        self.files.create.return_value.execute.side_effect = [
            {"id": "ARCHIVE_ROOT", "name": "archive"},
            {"id": "ARCHIVE_TS", "name": "2026-07-05T09.12.03"},
        ]
        self.files.update.return_value.execute.return_value = {
            "id": "DOC1",
            "parents": ["ARCHIVE_TS"],
        }
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        moved = adapter.archive_execution("2026-07-05T09.12.03")

        with self.subTest("returns the moved artifact"):
            self.assertEqual(["TilaMer_Resume"], [m.name for m in moved])
        with self.subTest("moved by files().update — addParents/removeParents"):
            _, kwargs = self.files.update.call_args
            self.assertEqual("DOC1", kwargs["fileId"])
            self.assertEqual("ARCHIVE_TS", kwargs["addParents"])
            self.assertEqual("FOLDER", kwargs["removeParents"])
        with self.subTest("no export/re-import — only files().update was used"):
            self.files.export_media.assert_not_called()

    def test_no_op_when_folder_is_empty(self) -> None:
        service = self.make_service()
        self.files.list.return_value.execute.side_effect = [
            {"files": []},  # ensure_subfolder("archive"): not found
            {"files": []},  # folder contents: empty
        ]
        self.files.create.return_value.execute.return_value = {
            "id": "ARCHIVE_ROOT",
            "name": "archive",
        }
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        moved = adapter.archive_execution("ts1")

        self.assertEqual([], moved)
        self.files.update.assert_not_called()

    def test_archive_query_excludes_the_archive_folder_itself(self) -> None:
        service = self.make_service()
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "ARCHIVE_ROOT", "name": "archive"}]},  # already exists
            {"files": []},  # folder contents: empty (archive excluded by query)
        ]
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        adapter.archive_execution("ts1")

        # The second list() call is the folder-contents enumeration; its query
        # must exclude the archive folder by name (so re-archiving never sweeps
        # up the archive dir itself).
        _, kwargs = self.files.list.call_args_list[1]
        self.assertIn("archive", kwargs["q"])
        with self.subTest("no items to move, no update calls"):
            self.files.update.assert_not_called()


class TestListExecutions(ThisTestCase):
    """Test DriveStorageAdapter.list_executions."""

    def test_empty_when_no_archive_folder(self) -> None:
        service = self.make_service()
        self.set_list([])
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        self.assertEqual([], adapter.list_executions())

    def test_returns_sorted_subfolder_names(self) -> None:
        service = self.make_service()
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "ARCHIVE_ROOT", "name": "archive"}]},  # find "archive"
            {
                "files": [
                    {"id": "T2", "name": "2026-07-05T09.12.03"},
                    {"id": "T1", "name": "2026-01-01T00.00.00"},
                ]
            },
        ]
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        found = adapter.list_executions()

        self.assertEqual(["2026-01-01T00.00.00", "2026-07-05T09.12.03"], found)


class TestPromoteExecution(ThisTestCase):
    """Test DriveStorageAdapter.promote_execution: the two-step move-by-id order."""

    def test_archives_root_before_promoting(self) -> None:
        service = self.make_service()
        # _archived_execution_folder_id: find "archive", then find "ts-old" under it.
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "ARCHIVE_ROOT", "name": "archive"}]},
            {"files": [{"id": "TS_OLD", "name": "ts-old"}]},
            # After archive_execution (mocked below) runs, promote lists the
            # target dir's contents to move.
            {"files": [{"id": "DOC1", "name": "TilaMer_Resume"}]},
        ]
        self.files.update.return_value.execute.return_value = {"id": "DOC1"}
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        adapter.archive_execution = mock.MagicMock(return_value=[])

        with mock.patch.object(MOD, "archive_timestamp", return_value="ts-new"):
            moved = adapter.promote_execution("ts-old")

        with self.subTest("current root archived first, under a fresh timestamp"):
            adapter.archive_execution.assert_called_once_with("ts-new")
        with self.subTest("promoted files moved by id, from the target dir to root"):
            self.assertEqual(["TilaMer_Resume"], [m.name for m in moved])
            _, kwargs = self.files.update.call_args
            self.assertEqual("DOC1", kwargs["fileId"])
            self.assertEqual("FOLDER", kwargs["addParents"])
            self.assertEqual("TS_OLD", kwargs["removeParents"])
        with self.subTest("the now-promoted (emptied) archive dir is deleted"):
            self.files.delete.assert_called_once_with(fileId="TS_OLD")

    def test_raises_when_timestamp_not_archived(self) -> None:
        service = self.make_service()
        self.set_list([])  # no "archive" folder at all
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        with self.assertRaises(FileNotFoundError):
            adapter.promote_execution("nope")


class TestExecutionNote(ThisTestCase):
    """Test DriveStorageAdapter read/write_execution_note (phase 6b)."""

    def test_read_defaults_when_no_sidecar(self) -> None:
        service = self.make_service()
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "ARCHIVE_ROOT", "name": "archive"}]},  # find "archive"
            {"files": [{"id": "TS", "name": "ts1"}]},  # find "ts1"
            {"files": []},  # find "execution.json": absent
        ]
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        self.assertEqual(
            {"note": None, "locked": False}, adapter.read_execution_note("ts1")
        )

    def test_write_creates_sidecar_when_absent(self) -> None:
        service = self.make_service()
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "ARCHIVE_ROOT", "name": "archive"}]},  # find "archive"
            {"files": [{"id": "TS", "name": "ts1"}]},  # find "ts1"
            {"files": []},  # find "execution.json" sidecar (absent) -> create
        ]
        self.files.create.return_value.execute.return_value = {"id": "NOTE"}
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        written = adapter.write_execution_note(
            "ts1", note="kept for follow-up", locked=True, _media_cls=mock.MagicMock()
        )

        with self.subTest("returns the merged sidecar"):
            self.assertEqual("kept for follow-up", written["note"])
            self.assertTrue(written["locked"])
        with self.subTest("created (not updated) since none existed"):
            _, kwargs = self.files.create.call_args
            self.assertEqual("execution.json", kwargs["body"]["name"])
            self.assertEqual(["TS"], kwargs["body"]["parents"])
            self.files.update.assert_not_called()

    def test_read_round_trips_written_content(self) -> None:
        # A fake downloader that writes real bytes into the buffer it's
        # constructed with, so the JSON round-trips through the mocked service.
        class FakeDownloader:
            def __init__(self, buffer, _request) -> None:
                buffer.write(json.dumps({"note": "kept", "locked": True}).encode())

            def next_chunk(self):
                return (None, True)

        service = self.make_service()
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "ARCHIVE_ROOT", "name": "archive"}]},  # find "archive"
            {"files": [{"id": "TS", "name": "ts1"}]},  # find "ts1"
            {"files": [{"id": "NOTE", "name": "execution.json"}]},  # sidecar present
        ]
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")

        found = adapter.read_execution_note("ts1", _download_cls=FakeDownloader)

        self.assertEqual({"note": "kept", "locked": True}, found)

    def test_write_raises_when_timestamp_not_archived(self) -> None:
        service = self.make_service()
        self.set_list([])
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        with self.assertRaises(FileNotFoundError):
            adapter.write_execution_note("nope", note="x")


class TestPurgeExecutions(ThisTestCase):
    """Test DriveStorageAdapter.purge_executions: locked executions are exempt."""

    def test_skips_locked_execution(self) -> None:
        service = self.make_service()
        self.files.list.return_value.execute.side_effect = [
            {"files": [{"id": "ARCHIVE_ROOT", "name": "archive"}]},  # find "archive"
            {
                "files": [
                    {"id": "T1", "name": "ts1"},
                    {"id": "T2", "name": "ts2"},
                ]
            },
        ]
        adapter = MOD.DriveStorageAdapter(service, "FOLDER")
        adapter.read_execution_note = mock.MagicMock(
            side_effect=lambda ts: {"note": None, "locked": ts == "ts2"}
        )
        adapter._archived_execution_folder_id = mock.MagicMock(
            side_effect=lambda ts: {"ts1": "T1", "ts2": "T2"}[ts]
        )

        purged = adapter.purge_executions()

        with self.subTest("only the unlocked execution purged"):
            self.assertEqual(["ts1"], purged)
        with self.subTest("deleted by id"):
            self.files.delete.assert_called_once_with(fileId="T1")


# __END__
