#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from unittest import TestCase, mock

import jobjob.cli as MOD

LOGGER = logging.getLogger(__name__)


def _make_settings(credentials_file: str = "/tmp/creds.json", token_file: str = "/tmp/token") -> mock.MagicMock:
    google = mock.MagicMock()
    google.credentials_file = Path(credentials_file)
    google.token_file = Path(token_file)
    settings = mock.MagicMock()
    settings.google = google
    return settings


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestBuildCredentialsLoader(ThisTestCase):
    """Test factory that returns a credentials loader closure."""

    def test_returns_callable(self) -> None:
        settings = _make_settings()
        loader = MOD.build_credentials_loader(settings)
        self.assertTrue(callable(loader))

    def test_loader_calls_get_google_credentials(self) -> None:
        settings = _make_settings(
            credentials_file="/tmp/creds.json",
            token_file="/tmp/token.pickle",
        )
        with mock.patch.object(MOD, "get_google_credentials") as mock_creds:
            mock_creds.return_value = mock.sentinel.creds
            loader = MOD.build_credentials_loader(settings)
            result = loader()

        mock_creds.assert_called_once_with(
            credentials_file=settings.google.credentials_file,
            token_file=settings.google.token_file,
        )
        self.assertIs(mock.sentinel.creds, result)

    def test_loader_passes_configured_paths(self) -> None:
        settings = _make_settings(
            credentials_file="/custom/creds.json",
            token_file="/custom/token.pickle",
        )
        with mock.patch.object(MOD, "get_google_credentials") as mock_creds:
            loader = MOD.build_credentials_loader(settings)
            loader()

        kwargs = mock_creds.call_args[1]
        self.assertEqual(settings.google.credentials_file, kwargs["credentials_file"])
        self.assertEqual(settings.google.token_file, kwargs["token_file"])


class TestConfigureLogging(ThisTestCase):
    """Test configure_logging."""

    def test_calls_basicConfig(self) -> None:
        with mock.patch("logging.basicConfig") as mock_basic:
            MOD.configure_logging()
        mock_basic.assert_called_once()

    def test_sets_info_level(self) -> None:
        with mock.patch("logging.basicConfig") as mock_basic:
            MOD.configure_logging()
        _, kwargs = mock_basic.call_args
        self.assertEqual(logging.INFO, kwargs["level"])


class TestRunMain(ThisTestCase):
    """Test run_main wrapper."""

    def test_returns_zero_on_success(self) -> None:
        main = mock.MagicMock(return_value=0)
        result = MOD.run_main(main, argv=[])
        self.assertEqual(0, result)
        main.assert_called_once_with([])

    def test_returns_one_on_keyboard_interrupt(self) -> None:
        main = mock.MagicMock(side_effect=KeyboardInterrupt)
        result = MOD.run_main(main, argv=[])
        self.assertEqual(1, result)

    def test_returns_one_on_generator_exit(self) -> None:
        main = mock.MagicMock(side_effect=GeneratorExit)
        result = MOD.run_main(main, argv=[])
        self.assertEqual(1, result)

    def test_returns_one_on_unexpected_exception(self) -> None:
        main = mock.MagicMock(side_effect=RuntimeError("boom"))
        result = MOD.run_main(main, argv=[])
        self.assertEqual(1, result)

    def test_passes_argv_to_main(self) -> None:
        main = mock.MagicMock(return_value=0)
        argv = ["--foo", "bar"]
        MOD.run_main(main, argv=argv)
        main.assert_called_once_with(argv)

    def test_none_argv_passes_none_to_main(self) -> None:
        main = mock.MagicMock(return_value=0)
        MOD.run_main(main, argv=None)
        main.assert_called_once_with(None)


# __END__
