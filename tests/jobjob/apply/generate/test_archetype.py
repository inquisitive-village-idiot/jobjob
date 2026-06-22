#!/usr/bin/env python3
"""Test."""

import json
import logging
from unittest import TestCase, mock

import jobjob.apply.generate.archetype as MOD
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.template import ResumeTemplate, make_template_set

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_job(self, **kwargs) -> JobDescription:
        defaults = {
            f: ""
            for f in (
                "company_name",
                "role_title",
                "department",
                "seniority_level",
                "salary",
                "hiring_manager",
                "summary",
            )
        }
        defaults.update(
            {
                f: ()
                for f in (
                    "location",
                    "key_requirements",
                    "responsibilities",
                    "technical_skills",
                    "soft_skills",
                    "keywords",
                )
            }
        )
        defaults.update(kwargs)
        return JobDescription(**defaults)

    def make_set(self):
        return make_template_set(
            [
                ResumeTemplate(name="features", archetype="Features", doc_id="DB"),
                ResumeTemplate(name="research", archetype="Research", doc_id="DR"),
            ],
            default="features",
        )

    def service_returning(self, name) -> mock.MagicMock:
        service = mock.MagicMock(__name__="service")
        service.return_value = json.dumps({"template": name})
        return service


class TestSelectTemplate(ThisTestCase):
    """Test function."""

    def test_explicit_name_is_required_to_exist(self) -> None:
        service = mock.MagicMock(__name__="service")
        result = MOD.select_template(
            self.make_job(), self.make_set(), service, name="research", use_cache=False
        )
        self.assertEqual("research", result.name)
        service.assert_not_called()

    def test_explicit_unknown_name_raises(self) -> None:
        with self.assertRaises(KeyError):
            MOD.select_template(
                self.make_job(),
                self.make_set(),
                mock.MagicMock(__name__="s"),
                name="nope",
                use_cache=False,
            )

    def test_auto_detects_when_no_name(self) -> None:
        result = MOD.select_template(
            self.make_job(role_title="PI"),
            self.make_set(),
            self.service_returning("research"),
            use_cache=False,
        )
        self.assertEqual("research", result.name)

    def test_falls_back_to_default_on_bad_detection(self) -> None:
        result = MOD.select_template(
            self.make_job(),
            self.make_set(),
            self.service_returning("does-not-exist"),
            use_cache=False,
        )
        self.assertEqual("features", result.name)


class TestDetectArchetype(ThisTestCase):
    """Test function."""

    def test_single_template_skips_api(self) -> None:
        one = make_template_set([ResumeTemplate("only", "O", "D")], default="only")
        service = mock.MagicMock(__name__="service")
        found = MOD.detect_archetype(self.make_job(), one, service, use_cache=False)
        self.assertEqual("only", found)
        service.assert_not_called()


# __END__
