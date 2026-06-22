#!/usr/bin/env python3
"""Test."""

import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import jobjob.loader.auth as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def setUp(self) -> None:
        self.freeze_environ()

    def freeze_environ(self) -> None:
        env = tuple(os.environ.items())
        self.addCleanup(self.thaw_environ, env=env)

    def thaw_environ(self, env: tuple[str, str]) -> None:
        os.environ = dict(env)

    def mock_google_app(self) -> mock.Mock:
        patch = mock.patch.object(MOD, "InstalledAppFlow", wraps=MOD.InstalledAppFlow)
        mobj = patch.start()
        mobj.return_value = mock.Mock(return_value=mock.Mock(spec_set=Credentials))
        self.addCleanup(patch.stop)
        return mobj


class TestGetGoogleCredentialsFile(ThisTestCase):
    """Test function."""

    def test_raises_if_env_var_not_set(self) -> None:
        with self.assertRaises(ValueError):
            MOD._get_google_credentials_file(env_name="FOO_BAR")

    def test_raises_if_env_var_path_is_not_a_file(self) -> None:
        os.environ[MOD.ENV_GOOGLE_CREDENTIALS_FILE] = "foo.json"
        with self.assertRaises(FileNotFoundError):
            MOD._get_google_credentials_file()

    def test_returns_expected(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "foo.json")
            path.touch()
            os.environ[MOD.ENV_GOOGLE_CREDENTIALS_FILE] = str(path)

            expected = path
            found = MOD._get_google_credentials_file()
            self.assertEqual(expected, found)


class TestGetGoogleTokenFile(ThisTestCase):
    """Test function."""

    def test_raises_if_env_var_not_set(self) -> None:
        with self.assertRaises(ValueError):
            MOD._get_google_token_file(env_name="FOO_BAR")

    def test_raises_if_env_var_path_is_not_a_file(self) -> None:
        os.environ[MOD.ENV_GOOGLE_TOKEN_FILE] = "foo.json"
        with self.assertRaises(FileNotFoundError):
            MOD._get_google_token_file()

    def test_returns_expected(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir, "foo.json")
            path.touch()
            os.environ[MOD.ENV_GOOGLE_TOKEN_FILE] = str(path)

            expected = path
            found = MOD._get_google_token_file()
            self.assertEqual(expected, found)


class TestGetGoogleCredentials(ThisTestCase):
    """Test function."""

    def setUp(self) -> None:
        super().setUp()

    def get_fake_credentials_file(self) -> Path:
        creds = {
            "installed": {
                "client_id": "ID.apps.googleusercontent.com",
                "project_id": "name-INT",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "SECRET",
                "redirect_uris": ["http://localhost"],
            }
        }
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)

        path = Path(tmpdir.name, "creds.json")
        path.write_text(json.dumps(creds))
        return path

    def test_raises_if_no_credentials_file(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)

        # NOTE: Requires missing or expired token pickle
        os.environ[MOD.ENV_GOOGLE_CREDENTIALS_FILE] = "foo.json"
        with self.assertRaises(FileNotFoundError):
            MOD.get_google_credentials(_flow_class=mock_flow)

    def test_raises_if_credentials_file_not_set(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)
        mock_load = mock.Mock(side_effect=ValueError)  # mimic behavior

        # NOTE: Requires missing or expired token pickle
        with self.assertRaises(ValueError):
            MOD.get_google_credentials(_flow_class=mock_flow, _load_creds=mock_load)

    def test_returns_pickled_token(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)

        mock_load = mock.Mock(spec_set=MOD._load_google_pickled_token)
        mock_token = mock.MagicMock(
            spec_set=Credentials, valid=False, expired=True, refresh_token="foo"
        )
        mock_load.return_value = mock_token

        found = MOD.get_google_credentials(_flow_class=mock_flow, _load_token=mock_load)
        expected = mock_token
        self.assertEqual(expected, found)

    def test_refreshes_token_if_pickled_token_expired(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)

        mock_load = mock.Mock(spec_set=MOD._load_google_pickled_token)
        mock_token = mock.MagicMock(
            spec_set=Credentials, valid=False, expired=True, refresh_token="foo"
        )
        mock_load.return_value = mock_token

        with self.subTest("returns pickled token"):
            found = MOD.get_google_credentials(
                _flow_class=mock_flow, _load_token=mock_load
            )
            expected = mock_token
            self.assertEqual(expected, found)

        with self.subTest("refreshed token"):
            mock_token.refresh.assert_called_once()

    def test_retrieves_new_token_if_no_token_available(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)

        path = self.get_fake_credentials_file()
        os.environ[MOD.ENV_GOOGLE_CREDENTIALS_FILE] = str(path)

        found = MOD.get_google_credentials(_flow_class=mock_flow)
        expected = (
            mock_flow.from_client_secrets_file.return_value.run_local_server.return_value
        )
        self.assertEqual(expected, found)

    def test_pickles_new_token_when_token_file_given(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)
        # NOTE: use a picklable sentinel (a MagicMock cannot be pickled).
        run_server = mock_flow.from_client_secrets_file.return_value.run_local_server
        run_server.return_value = {"token": "abc"}

        path = self.get_fake_credentials_file()
        os.environ[MOD.ENV_GOOGLE_CREDENTIALS_FILE] = str(path)

        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        token_path = Path(tmpdir.name, "token.pickle")

        MOD.get_google_credentials(token_file=token_path, _flow_class=mock_flow)
        self.assertTrue(token_path.is_file())

    def test_force_reauth_skips_token_load_and_runs_flow(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)
        path = self.get_fake_credentials_file()
        os.environ[MOD.ENV_GOOGLE_CREDENTIALS_FILE] = str(path)

        # A valid token would normally short-circuit; force_reauth must ignore it.
        mock_load = mock.Mock(spec_set=MOD._load_google_pickled_token)
        mock_load.return_value = mock.MagicMock(spec_set=Credentials, valid=True)

        found = MOD.get_google_credentials(
            force_reauth=True, _flow_class=mock_flow, _load_token=mock_load
        )

        mock_load.assert_not_called()
        expected = (
            mock_flow.from_client_secrets_file.return_value.run_local_server.return_value
        )
        self.assertEqual(expected, found)


class TestSavePickledToken(ThisTestCase):
    """Test function."""

    def test_writes_token_and_creates_parent_dirs(self) -> None:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        token_path = Path(tmpdir.name, "nested", "token.pickle")

        MOD.save_pickled_token({"token": "abc"}, token_path)

        self.assertTrue(token_path.is_file())
        with open(token_path, "rb") as handle:
            import pickle

            self.assertEqual({"token": "abc"}, pickle.load(handle))


class TestLoadGooglePickledToken(ThisTestCase):
    """Test _load_google_pickled_token edge cases."""

    def test_raises_file_not_found_for_nonexistent_explicit_path(self) -> None:
        with self.assertRaises(FileNotFoundError):
            MOD._load_google_pickled_token(Path("/nonexistent/token.pickle"))

    def test_raises_file_not_found_when_env_token_path_does_not_exist(self) -> None:
        os.environ[MOD.ENV_GOOGLE_TOKEN_FILE] = "/nonexistent/token.pickle"
        with self.assertRaises(FileNotFoundError):
            MOD._get_google_token_file()


class TestLoadGoogleCredentials(ThisTestCase):
    """Test _load_google_credentials edge cases."""

    def test_raises_file_not_found_for_nonexistent_path(self) -> None:
        with self.assertRaises(FileNotFoundError):
            MOD._load_google_credentials(path=Path("/nonexistent/creds.json"))


class TestRefreshCreds(ThisTestCase):
    """Test _refresh_creds."""

    def test_returns_none_on_refresh_error(self) -> None:
        from google.auth.exceptions import RefreshError

        mock_creds = mock.MagicMock(spec_set=Credentials)
        mock_creds.refresh.side_effect = RefreshError("token expired")

        result = MOD._refresh_creds(mock_creds)

        self.assertIsNone(result)

    def test_returns_creds_on_successful_refresh(self) -> None:
        mock_creds = mock.MagicMock(spec_set=Credentials)

        result = MOD._refresh_creds(mock_creds)

        mock_creds.refresh.assert_called_once()
        self.assertIs(mock_creds, result)


class TestGetGoogleCredentialsExtraCases(ThisTestCase):
    """Test get_google_credentials branches not covered by existing tests."""

    def test_returns_valid_cached_token_without_calling_flow(self) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)

        mock_load = mock.Mock(spec_set=MOD._load_google_pickled_token)
        valid_token = mock.MagicMock(spec_set=Credentials, valid=True)
        mock_load.return_value = valid_token

        result = MOD.get_google_credentials(
            _flow_class=mock_flow, _load_token=mock_load
        )

        mock_flow.from_client_secrets_file.assert_not_called()
        self.assertIs(valid_token, result)

    def test_falls_through_to_flow_when_creds_not_expired_and_no_refresh_token(
        self,
    ) -> None:
        mock_flow = mock.MagicMock(spec_set=InstalledAppFlow)

        mock_load = mock.Mock(spec_set=MOD._load_google_pickled_token)
        bad_token = mock.MagicMock(
            spec_set=Credentials,
            valid=False,
            expired=False,
            refresh_token=None,
        )
        mock_load.return_value = bad_token

        mock_load_creds = mock.Mock(spec_set=MOD._load_google_credentials)
        mock_load_creds.return_value = mock.MagicMock(spec_set=Credentials)

        MOD.get_google_credentials(
            _flow_class=mock_flow,
            _load_token=mock_load,
            _load_creds=mock_load_creds,
        )

        mock_load_creds.assert_called_once()


# __END__
