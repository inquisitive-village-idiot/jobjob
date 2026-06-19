#!/usr/bin/env python3
"""Build Google Drive/Docs API service clients from credentials."""

from collections.abc import Callable
from typing import Any

from googleapiclient.discovery import build


def build_drive_service(credentials: Any, _build: Callable = build) -> Any:
    """Return a Drive v3 service client for the given credentials."""
    return _build("drive", "v3", credentials=credentials)


def build_docs_service(credentials: Any, _build: Callable = build) -> Any:
    """Return a Docs v1 service client for the given credentials."""
    return _build("docs", "v1", credentials=credentials)


def build_sheets_service(credentials: Any, _build: Callable = build) -> Any:
    """Return a Sheets v4 service client for the given credentials."""
    return _build("sheets", "v4", credentials=credentials)


# __END__
