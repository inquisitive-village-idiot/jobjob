#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase, mock

import jobjob.gapi.service as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_credentials(self) -> mock.MagicMock:
        return mock.MagicMock(name="credentials")


class TestBuildDriveService(ThisTestCase):
    """Test function."""

    def test_calls_build_with_drive_v3(self) -> None:
        creds = self.make_credentials()
        mock_build = mock.MagicMock(return_value=mock.sentinel.service)

        result = MOD.build_drive_service(creds, _build=mock_build)

        mock_build.assert_called_once_with("drive", "v3", credentials=creds)
        self.assertIs(mock.sentinel.service, result)

    def test_passes_credentials_through(self) -> None:
        creds = self.make_credentials()
        mock_build = mock.MagicMock()

        MOD.build_drive_service(creds, _build=mock_build)

        _, kwargs = mock_build.call_args
        self.assertIs(creds, kwargs["credentials"])


class TestBuildDocsService(ThisTestCase):
    """Test function."""

    def test_calls_build_with_docs_v1(self) -> None:
        creds = self.make_credentials()
        mock_build = mock.MagicMock(return_value=mock.sentinel.service)

        result = MOD.build_docs_service(creds, _build=mock_build)

        mock_build.assert_called_once_with("docs", "v1", credentials=creds)
        self.assertIs(mock.sentinel.service, result)

    def test_passes_credentials_through(self) -> None:
        creds = self.make_credentials()
        mock_build = mock.MagicMock()

        MOD.build_docs_service(creds, _build=mock_build)

        _, kwargs = mock_build.call_args
        self.assertIs(creds, kwargs["credentials"])


class TestBuildSheetsService(ThisTestCase):
    """Test function."""

    def test_calls_build_with_sheets_v4(self) -> None:
        creds = self.make_credentials()
        mock_build = mock.MagicMock(return_value=mock.sentinel.service)

        result = MOD.build_sheets_service(creds, _build=mock_build)

        mock_build.assert_called_once_with("sheets", "v4", credentials=creds)
        self.assertIs(mock.sentinel.service, result)

    def test_passes_credentials_through(self) -> None:
        creds = self.make_credentials()
        mock_build = mock.MagicMock()

        MOD.build_sheets_service(creds, _build=mock_build)

        _, kwargs = mock_build.call_args
        self.assertIs(creds, kwargs["credentials"])


# __END__
