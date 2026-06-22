#!/usr/bin/env python3
"""Test."""

import logging
from datetime import datetime
from unittest import TestCase, mock

import jobjob.gapi.sheets as MOD
from jobjob.structure.profile import LinkedInProfile

LOGGER = logging.getLogger(__name__)

# The real "contacts" header (column A onward).
HEADER = [
    "location",
    "company",
    "role",
    "name",
    "linkedin_url",
    "Request",
    "1st Msg",
    "2nd",
    "3rd",
    "corporate_url",
    "shared_connections",
    "notes",
    "last_verified",
    "citations",
    "found_by",
]


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_service(self, header) -> mock.MagicMock:
        service = mock.MagicMock()
        values = service.spreadsheets.return_value.values.return_value
        values.get.return_value.execute.return_value = {"values": [header]}
        self.values = values
        return service

    def make_profile(self, **kwargs) -> LinkedInProfile:
        defaults = {
            "name": "",
            "role": "",
            "company": "",
            "location": "",
            "headline": "",
            "linkedin_url": "",
        }
        defaults.update(kwargs)
        return LinkedInProfile(**defaults)


class TestDetectColumns(ThisTestCase):
    """Test function."""

    def test_maps_known_headers(self) -> None:
        col_map = MOD.detect_columns(HEADER)
        self.assertEqual(0, col_map["location"])
        self.assertEqual(3, col_map["name"])
        self.assertEqual(4, col_map["linkedin_url"])
        self.assertEqual(14, col_map["found_by"])


class TestBuildRow(ThisTestCase):
    """Test function."""

    def test_full_width_aligned(self) -> None:
        row = MOD.build_row(
            HEADER, {"name": 3, "location": 0}, {"name": "X", "location": "Y"}
        )
        self.assertEqual(len(HEADER), len(row))
        self.assertEqual("Y", row[0])
        self.assertEqual("X", row[3])
        self.assertEqual("", row[1])


class TestAppendProfile(ThisTestCase):
    """Test function."""

    def test_appends_row_aligned_to_header(self) -> None:
        service = self.make_service(HEADER)
        profile = self.make_profile(
            name="Jane Doe",
            role="VP",
            company="Acme",
            location="Boston",
            linkedin_url="li/jane",
        )

        row = MOD.append_profile(service, "SHEET", profile, date=datetime(2026, 6, 7))

        with self.subTest("no blank leading columns (location at A)"):
            self.assertEqual("Boston", row[0])
        with self.subTest("values land in mapped columns"):
            self.assertEqual("Acme", row[1])
            self.assertEqual("VP", row[2])
            self.assertEqual("Jane Doe", row[3])
            self.assertEqual("li/jane", row[4])
            self.assertEqual("06/07/2026", row[5])
            self.assertEqual("screenshot", row[14])
        with self.subTest("appended at A1 with INSERT_ROWS"):
            _, kwargs = self.values.append.call_args
            self.assertEqual("contacts!A1", kwargs["range"])
            self.assertEqual("INSERT_ROWS", kwargs["insertDataOption"])
            self.assertEqual([row], kwargs["body"]["values"])

    def test_empty_fields_become_missing_marker(self) -> None:
        service = self.make_service(HEADER)
        row = MOD.append_profile(service, "SHEET", self.make_profile(name="Jane"))
        self.assertEqual("Jane", row[3])
        self.assertEqual(MOD.MISSING, row[0])  # location empty -> "--"

    def test_use_lock_false_skips_lock(self) -> None:
        service = self.make_service(HEADER)
        MOD.append_profile(
            service, "SHEET", self.make_profile(name="Jane"), use_lock=False
        )
        service.spreadsheets.return_value.batchUpdate.assert_not_called()


class TestSheetLock(ThisTestCase):
    """Test function."""

    def make_locking_service(
        self, sheet_name="contacts", sheet_id=42, range_id=99, existing_locks=()
    ) -> mock.MagicMock:
        service = mock.MagicMock()
        ss = service.spreadsheets.return_value
        protected = [
            {"protectedRangeId": i, "description": MOD.LOCK_DESCRIPTION}
            for i in existing_locks
        ]
        ss.get.return_value.execute.return_value = {
            "sheets": [
                {
                    "properties": {"sheetId": sheet_id, "title": sheet_name},
                    "protectedRanges": protected,
                }
            ]
        }
        ss.batchUpdate.return_value.execute.return_value = {
            "replies": [
                {
                    "addProtectedRange": {
                        "protectedRange": {"protectedRangeId": range_id}
                    }
                }
            ]
        }
        self.ss = ss
        return service

    def test_acquires_then_releases(self) -> None:
        service = self.make_locking_service()
        with MOD.sheet_lock(service, "SHEET", "contacts"):
            pass
        bodies = [
            c.kwargs["body"]["requests"] for c in self.ss.batchUpdate.call_args_list
        ]
        self.assertEqual(2, len(bodies))  # lock (add), then unlock (delete)
        self.assertIn("addProtectedRange", bodies[0][-1])
        self.assertEqual(
            {"deleteProtectedRange": {"protectedRangeId": 99}}, bodies[1][0]
        )

    def test_clears_stale_lock_first(self) -> None:
        service = self.make_locking_service(existing_locks=(7,))
        with MOD.sheet_lock(service, "SHEET", "contacts"):
            pass
        lock_requests = self.ss.batchUpdate.call_args_list[0].kwargs["body"]["requests"]
        self.assertEqual(
            {"deleteProtectedRange": {"protectedRangeId": 7}}, lock_requests[0]
        )
        self.assertIn("addProtectedRange", lock_requests[-1])

    def test_unknown_sheet_proceeds_without_lock(self) -> None:
        service = self.make_locking_service(sheet_name="other")  # title won't match
        with MOD.sheet_lock(service, "SHEET", "contacts"):
            pass
        self.ss.batchUpdate.assert_not_called()  # never acquired -> nothing to release

    def test_release_failure_is_swallowed(self) -> None:
        service = self.make_locking_service()
        self.ss.batchUpdate.return_value.execute.side_effect = [
            {
                "replies": [
                    {"addProtectedRange": {"protectedRange": {"protectedRangeId": 99}}}
                ]
            },
            RuntimeError("unlock boom"),
        ]
        # Must not raise despite the unlock failing.
        with MOD.sheet_lock(service, "SHEET", "contacts"):
            pass

    def test_append_locks_by_default(self) -> None:
        service = self.make_locking_service()
        get_call = service.spreadsheets.return_value.values.return_value.get
        get_call.return_value.execute.return_value = {"values": [HEADER]}
        MOD.append_profile(service, "SHEET", self.make_profile(name="Jane"))
        self.assertEqual(2, self.ss.batchUpdate.call_count)  # acquire + release


# __END__
