#!/usr/bin/env python3
"""Test."""

import json
import logging
from unittest import TestCase, mock

import jobjob.apply.generate.highlights as MOD
from jobjob.structure.highlight import Highlight, make_highlight_set
from jobjob.structure.job_decription import JobDescription

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
        highlights = [
            Highlight(context="py", text="Python work", keywords=("python",)),
            Highlight(
                context="fda", text="FDA submission", keywords=("fda", "regulatory")
            ),
            Highlight(
                context="off", text="Disabled", keywords=("python",), enabled=False
            ),
            Highlight(context="misc", text="Other", keywords=("misc",)),
        ]
        return make_highlight_set(highlights, default_number=2)


class TestScoreHighlights(ThisTestCase):
    """Test function."""

    def test_counts_keyword_hits(self) -> None:
        job = self.make_job(role_title="Python engineer", technical_skills=("FDA",))
        scores = MOD.score_highlights(job, self.make_set().highlights)
        self.assertEqual(1, scores["py"])
        self.assertEqual(1, scores["fda"])
        self.assertEqual(0, scores["misc"])


class TestSelectHighlights(ThisTestCase):
    """Test function."""

    def test_returns_model_selection(self) -> None:
        job = self.make_job(role_title="Python engineer")
        service = mock.MagicMock(__name__="service")
        service.return_value = json.dumps(["fda", "py"])

        result = MOD.select_highlights(job, self.make_set(), service, use_cache=False)

        contexts = tuple(h.context for h in result)
        self.assertEqual(("fda", "py"), contexts)

    def test_excludes_disabled_and_unknown_keys(self) -> None:
        job = self.make_job(role_title="Python engineer")
        service = mock.MagicMock(__name__="service")
        # "off" is disabled, "bogus" is unknown -> both dropped; back-fill to 2.
        service.return_value = json.dumps(["off", "bogus", "py"])

        result = MOD.select_highlights(job, self.make_set(), service, use_cache=False)

        contexts = set(h.context for h in result)
        self.assertEqual(2, len(result))
        self.assertIn("py", contexts)
        self.assertNotIn("off", contexts)

    def test_backfills_when_model_returns_too_few(self) -> None:
        job = self.make_job(role_title="Python engineer")
        service = mock.MagicMock(__name__="service")
        service.return_value = json.dumps([])  # model returned nothing

        result = MOD.select_highlights(
            job, self.make_set(), service, num=2, use_cache=False
        )

        self.assertEqual(2, len(result))
        self.assertTrue(all(h.enabled for h in result))


# __END__
