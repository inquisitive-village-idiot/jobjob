#!/usr/bin/env python3
"""Test."""

import json
import logging
from unittest import TestCase, mock

import jobjob.enrich.parse as MOD
from jobjob.structure.profile import LinkedInProfile
from tests.fixtures import fixture_path

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_service(self, payload: dict) -> mock.MagicMock:
        service = mock.MagicMock(__name__="service")
        service.return_value = json.dumps(payload)
        return service


class TestParseProfile(ThisTestCase):
    """Test function. Uses a real example PDF as input (query is mocked)."""

    def test_builds_profile_from_model_json(self) -> None:
        payload = {
            "name": "Jane Doe",
            "role": "VP Engineering",
            "company": "Acme Bio",
            "location": "Boston, MA",
            "linkedin_url": "linkedin.com/in/janedoe",
        }
        service = self.make_service(payload)
        # NOTE: any real PDF works as input — the model call is mocked.
        path = fixture_path("job_description_acme")

        result = MOD.parse_profile(path, service, use_cache=False)

        with self.subTest("is LinkedInProfile"):
            self.assertIsInstance(result, LinkedInProfile)
        with self.subTest("maps fields"):
            self.assertEqual("Jane Doe", result.name)
            self.assertEqual("Acme Bio", result.company)
            self.assertEqual("linkedin.com/in/janedoe", result.linkedin_url)
        with self.subTest("defaults missing field to empty"):
            self.assertEqual("", result.headline)


# __END__
