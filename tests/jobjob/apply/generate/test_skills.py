#!/usr/bin/env python3
"""Test."""

import json
import logging
from unittest import TestCase, mock

import jobjob.apply.generate.skills as MOD
from jobjob.structure.job_decription import JobDescription

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_job(self, **kwargs) -> JobDescription:
        defaults = {f: "" for f in ("company_name", "role_title", "department",
                                     "seniority_level", "salary", "hiring_manager",
                                     "summary")}
        defaults.update({f: () for f in ("location", "key_requirements",
                                         "responsibilities", "technical_skills",
                                         "soft_skills", "keywords")})
        defaults.update(kwargs)
        return JobDescription(**defaults)


class TestAnalyzeSkills(ThisTestCase):
    """Test function."""

    def test_returns_parsed_categories(self) -> None:
        payload = {
            "critical_gaps": [{"skill": "Rust", "why_critical": "x", "mitigation": "y"}],
            "critical_supported": [],
            "important_supported": [],
            "strong_supporting": [],
        }
        service = mock.MagicMock(__name__="service")
        service.return_value = f"```json\n{json.dumps(payload)}\n```"

        result = MOD.analyze_skills(self.make_job(), service, use_cache=False)

        self.assertEqual(payload, result)


# __END__
