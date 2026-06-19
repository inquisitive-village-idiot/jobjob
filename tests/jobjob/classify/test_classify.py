#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from unittest import TestCase, mock

import jobjob.classify.classify as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def reader(self, text: str) -> mock.MagicMock:
        return mock.MagicMock(return_value=text)


class TestClassifyFile(ThisTestCase):
    """Test function."""

    def test_unsupported_suffix(self) -> None:
        found = MOD.classify_file(Path("notes.rtf"), _read=self.reader(""))
        self.assertEqual(MOD.UNSUPPORTED, found)

    def test_linkedin_filename_fast_path(self) -> None:
        reader = self.reader("")  # should not be read
        found = MOD.classify_file(
            Path("data/screencapture-linkedin-in-jane-doe.pdf"), _read=reader
        )
        self.assertEqual(MOD.LINKEDIN_PROFILE, found)
        reader.assert_not_called()

    def test_job_board_filename_fast_path(self) -> None:
        reader = self.reader("")  # should not be read
        found = MOD.classify_file(
            Path("data/screencapture-careers-lilly-us-job-123.pdf"), _read=reader
        )
        self.assertEqual(MOD.JD, found)
        reader.assert_not_called()

    def test_jd_text_signals(self) -> None:
        text = "About the role. Responsibilities and minimum qualifications. Apply."
        found = MOD.classify_file(Path("posting.pdf"), _read=self.reader(text))
        self.assertEqual(MOD.JD, found)

    def test_profile_text_signals(self) -> None:
        text = "500+ connections. 1,200 followers. See all activity."
        found = MOD.classify_file(Path("export.pdf"), _read=self.reader(text))
        self.assertEqual(MOD.LINKEDIN_PROFILE, found)

    def test_ambiguous_without_service_is_unsupported(self) -> None:
        found = MOD.classify_file(Path("blank.pdf"), _read=self.reader("hello world"))
        self.assertEqual(MOD.UNSUPPORTED, found)

    def test_ambiguous_uses_ai_fallback(self) -> None:
        query = mock.MagicMock(__name__="service")
        fake_query = mock.MagicMock(return_value={"type": "jd"})
        found = MOD.classify_file(
            Path("blank.pdf"),
            query_service=query,
            use_cache=False,
            _read=self.reader("some ambiguous prose with no signals"),
            _query=fake_query,
        )
        self.assertEqual(MOD.JD, found)
        fake_query.assert_called_once()

    def test_unreadable_pdf_is_unsupported(self) -> None:
        reader = mock.MagicMock(side_effect=ValueError("no text"))
        found = MOD.classify_file(Path("image_only.pdf"), _read=reader)
        self.assertEqual(MOD.UNSUPPORTED, found)


# __END__
