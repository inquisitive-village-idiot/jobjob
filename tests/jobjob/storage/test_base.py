#!/usr/bin/env python3
"""Test."""

import logging
from datetime import datetime
from unittest import TestCase

import jobjob.storage.base as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestArchiveTimestamp(ThisTestCase):
    """Test function."""

    def test_formats_seconds_resolution_with_dots(self) -> None:
        found = MOD.archive_timestamp(datetime(2026, 7, 5, 9, 12, 3))
        self.assertEqual("2026-07-05T09.12.03", found)

    def test_no_colons(self) -> None:
        # Colons are unsafe in some filesystem/Drive names.
        found = MOD.archive_timestamp(datetime(2026, 1, 1, 0, 0, 0))
        self.assertNotIn(":", found)

    def test_defaults_to_now(self) -> None:
        found = MOD.archive_timestamp()
        self.assertRegex(found, r"^\d{4}-\d{2}-\d{2}T\d{2}\.\d{2}\.\d{2}$")


class TestPlacedArtifact(ThisTestCase):
    """Test the PlacedArtifact dataclass."""

    def test_stores_name_and_location(self) -> None:
        artifact = MOD.PlacedArtifact(
            name="TilaMer_Resume", location="/x/TilaMer_Resume"
        )
        self.assertEqual("TilaMer_Resume", artifact.name)
        self.assertEqual("/x/TilaMer_Resume", artifact.location)


# __END__
