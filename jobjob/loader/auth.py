#!/usr/bin/env python3
"""."""

import os
import pickle
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google credentials
# ======================================================================

ENV_GOOGLE_TOKEN_FILE = "GOOGLE_TOKEN_FILE"
ENV_GOOGLE_CREDENTIALS_FILE = "GOOGLE_CREDENTIALS_FILE"
GOOGLE_API_SCOPES = (
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
)  # NOTE: adding a scope requires re-auth (delete the token file) to take effect.

# Helper functions
# ----------------------------------


def _get_google_credentials_file(env_name: str = ENV_GOOGLE_CREDENTIALS_FILE) -> Path:
    """Return path from env var."""
    try:
        path = Path(os.environ[env_name])
    except KeyError:
        # Although Path will raise TypeError for invalid input, environ should always
        # be strings when set. So only care about catching a KeyError.
        raise ValueError(f"Env not set: {env_name}")

    if not path.is_file():
        raise FileNotFoundError(str(path))

    return path


def _get_google_token_file(env_name: str = ENV_GOOGLE_TOKEN_FILE) -> Path:
    """Return path to pickled google cred token."""
    try:
        path = Path(os.environ[env_name])
    except KeyError:
        # Although Path will raise TypeError for invalid input, environ should always
        # be strings when set. So only care about catching a KeyError.
        raise ValueError(f"Env not set: {env_name}")

    if not path.is_file():
        raise FileNotFoundError(str(path))

    return path


def _load_google_pickled_token(path: Optional[Path] = None) -> Credentials:
    """Load given pickled credentials."""
    path = path or _get_google_token_file()
    if not path:
        raise ValueError("No valid token file.")
    elif not path.is_file():
        raise FileNotFoundError(str(path))
    with open(path, "rb") as token:
        creds = pickle.load(token)
    return creds


def save_pickled_token(creds: Credentials, path: Path) -> None:
    """Persist ``creds`` to ``path`` (pickle), creating parent dirs as needed.

    ``get_google_credentials`` only writes the token on the full-flow path; a
    refreshed token is not persisted there. Callers that want a refresh to stick
    (e.g. the ``auth`` command) save it explicitly with this.

    Arguments:
        creds: The credentials to persist.
        path: Destination token-file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        pickle.dump(creds, handle)


def _load_google_credentials(
    path: Optional[Path] = None,
    scopes: Iterable[str] = GOOGLE_API_SCOPES,
    token_file: Optional[Path] = None,
    _flow_class: Callable = InstalledAppFlow,
) -> Credentials:
    """Run the OAuth installed-app flow to obtain new credentials.

    Arguments:
        path: Path to the client-secrets JSON. Defaults to GOOGLE_CREDENTIALS_FILE.
        scopes: OAuth scopes to request.
        token_file: If given, the obtained credentials are pickled here so future
            runs can reuse them without re-prompting.
        _flow_class: Injection point for InstalledAppFlow (testing).
    Returns:
        The obtained Credentials.
    Raises:
        FileNotFoundError: If the client-secrets file is missing.
        ValueError: If no credentials path could be resolved.
    """
    path = path or _get_google_credentials_file()
    if not path:
        raise ValueError("No valid credentials file.")
    elif not path.is_file():
        raise FileNotFoundError(
            f"Credentials file not found: {path}\n"
            "Download from Google Cloud Console and set GOOGLE_CREDENTIALS_FILE env var"
        )

    flow = _flow_class.from_client_secrets_file(str(path), scopes)
    creds = flow.run_local_server(port=0)

    if token_file is not None:
        with open(token_file, "wb") as handle:
            pickle.dump(creds, handle)

    return creds


def _refresh_creds(creds: Credentials) -> Credentials | None:
    """Refreshes credentials or returns None if unable."""
    try:
        creds.refresh(Request())
    except RefreshError:
        return None
    else:
        return creds


# Primary Google Credentials Function
# ----------------------------------


def get_google_credentials(
    credentials_file: Optional[Path] = None,
    token_file: Optional[Path] = None,
    force_reauth: bool = False,
    _load_token: Callable[[Path], Credentials] = _load_google_pickled_token,
    _load_creds: Callable[[Path], Credentials] = _load_google_credentials,
    _flow_class: Callable = InstalledAppFlow,
) -> Credentials:
    """Return google credentials.

    Will attempt to load from pickle first. If expired, will attempt to refresh.
    Otherwis, will retrieve a new token.

    Arguments:
        credentials_file: Path to the credentials.json.
            Will default to Path in GOOGLE_CREDENTIALS_FILE.
        token_file: Path to pickled token.
            Will default to Path in GOOGLE_CREDENTIALS_FILE.
        force_reauth: Ignore any existing token and run the OAuth consent flow.
            Use after the requested scopes change (the cached token is unaware of
            a scope change and would otherwise be reused).
    Returns:
        A loaded Credentials instance.
    Raises:
        FileNotFoundError if no credentials file found.
        ValueError if unable to load credentials file.
    """
    creds = None

    if not force_reauth:
        try:
            creds = _load_token(token_file)
        except (FileNotFoundError, ValueError):
            pass

        if not creds:
            pass  # don't have a ny creds -- handle below
        elif creds.valid:
            pass  # current creds are good
        elif creds.expired and creds.refresh_token:
            creds = _refresh_creds(creds)  # type: Credentials | None
        else:
            creds = None  # current creds are bad

    if not creds:
        creds = _load_creds(
            credentials_file, token_file=token_file, _flow_class=_flow_class
        )
    return creds


# __END__
