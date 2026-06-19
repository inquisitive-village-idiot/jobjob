#!/usr/bin/env python3
"""Test."""

from tests.fixtures import fixture_dir, fixture_path
import json
import logging
from unittest import TestCase, mock

import jobjob.apply.generate.parse as MOD
from jobjob.loader import location
from jobjob.structure.job_decription import JobDescription

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_service(self, payload: dict) -> mock.MagicMock:
        service = mock.MagicMock(__name__="service")
        service.return_value = json.dumps(payload)
        return service


class TestParseJobDescription(ThisTestCase):
    """Test function. Builds the prompt from a real example PDF."""

    def test_builds_job_description_from_model_json(self) -> None:
        payload = {
            "company_name": "Acme",
            "role_title": "Science Correspondent",
            "key_requirements": ["Python", "FDA"],
            "seniority_level": "principal",
        }
        service = self.make_service(payload)
        path = fixture_path("job_description_acme")

        result = MOD.parse_job_description(path, service, use_cache=False)

        with self.subTest("is JobDescription"):
            self.assertIsInstance(result, JobDescription)
        with self.subTest("maps provided fields"):
            self.assertEqual("Acme", result.company_name)
            self.assertEqual(("Python", "FDA"), tuple(result.key_requirements))
        with self.subTest("defaults missing string field to empty"):
            self.assertEqual("", result.summary)
        with self.subTest("defaults missing iterable field to empty"):
            self.assertEqual((), result.technical_skills)


# __END__
