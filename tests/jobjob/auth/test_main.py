#!/usr/bin/env python3
"""Test the `jobjob auth` sub-command."""

import logging
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

import jobjob.auth.__main__ as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def patch_settings(self, token_file):
        google = SimpleNamespace(
            credentials_file=Path("creds.json"), token_file=token_file
        )
        settings = SimpleNamespace(google=google)
        return mock.patch.object(MOD, "load_settings", return_value=settings)


class TestMain(ThisTestCase):
    """Test function."""

    def test_authorizes_and_persists_token(self) -> None:
        creds = mock.MagicMock()
        token = Path("/tmp/token.pickle")
        with (
            self.patch_settings(token),
            mock.patch.object(MOD, "get_google_credentials", return_value=creds) as get,
            mock.patch.object(MOD, "save_pickled_token") as save,
        ):
            code = MOD.main([])
        self.assertEqual(0, code)
        get.assert_called_once_with(
            credentials_file=Path("creds.json"), token_file=token, force_reauth=False
        )
        save.assert_called_once_with(creds, token)

    def test_force_flag_passes_through(self) -> None:
        with (
            self.patch_settings(Path("/tmp/token.pickle")),
            mock.patch.object(MOD, "get_google_credentials") as get,
            mock.patch.object(MOD, "save_pickled_token"),
        ):
            MOD.main(["--force"])
        self.assertTrue(get.call_args.kwargs["force_reauth"])

    def test_no_token_path_returns_2(self) -> None:
        with (
            self.patch_settings(None),
            mock.patch.object(MOD, "get_google_credentials") as get,
            mock.patch.object(MOD, "save_pickled_token") as save,
        ):
            code = MOD.main([])
        self.assertEqual(2, code)
        get.assert_not_called()
        save.assert_not_called()


# __END__
