#!/usr/bin/env python3
"""Storage adapters: place/find/archive an application's execution artifacts.

See ``jobjob.storage.base`` for the ``StorageAdapter`` Protocol.
"""

from jobjob.storage.base import PlacedArtifact, StorageAdapter, archive_timestamp
from jobjob.storage.drive import DriveStorageAdapter
from jobjob.storage.local import LocalStorageAdapter

__all__ = [
    "StorageAdapter",
    "PlacedArtifact",
    "archive_timestamp",
    "LocalStorageAdapter",
    "DriveStorageAdapter",
]

# __END__
