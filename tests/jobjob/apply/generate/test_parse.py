#!/usr/bin/env python3
"""Test."""

import json
import logging
from unittest import TestCase, mock

import jobjob.apply.generate.parse as MOD
from jobjob.structure.job_decription import JobDescription
from tests.fixtures import fixture_path

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

    def test_parses_text_snapshot_through_query(self) -> None:
        """A Markdown snapshot (URL/paste capture) is read and sent to the model."""
        import tempfile
        from pathlib import Path

        payload = {
            "company_name": "Acme Gazette",
            "role_title": "Science Correspondent",
        }
        captured: dict = {}

        def _query(prompt, **kwargs):
            # query_ai_service returns parsed JSON (a mapping), not a raw string.
            captured["prompt"] = prompt
            return payload

        snapshot = Path(tempfile.mkdtemp()) / "jd-20260620-acme.md"
        snapshot.write_text(
            "<!-- source: https://jobs.example.com/acme -->\n\n"
            "Acme Gazette seeks a science correspondent to cover print science.",
            encoding="utf-8",
        )

        service = mock.MagicMock(__name__="service")
        result = MOD.parse_job_description(
            snapshot, service, use_cache=False, _query=_query
        )

        with self.subTest("snapshot text reached the prompt"):
            self.assertIn("science correspondent", captured["prompt"])
        with self.subTest("parsed from snapshot, not vision"):
            self.assertEqual("Acme Gazette", result.company_name)
            service.complete_document.assert_not_called()


# __END__
