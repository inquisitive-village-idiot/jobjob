#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.normalize as MOD
from jobjob.structure.skillcloud import CloudSkill, SkillCloud

LOGGER = logging.getLogger(__name__)


def make_cloud(*skills: CloudSkill) -> SkillCloud:
    index = {}
    for skill in skills:
        index.setdefault(skill.id.lower(), skill.id)
    for skill in skills:
        index.setdefault(skill.name.lower(), skill.id)
    for skill in skills:
        for alias in skill.aliases:
            index.setdefault(alias.lower(), skill.id)
    return SkillCloud(
        skills={s.id: s for s in skills}, esco_version="test", _index=index
    )


PYTHON = CloudSkill(
    id="python_programming",
    name="Python (computer programming)",
    aliases=("Python", "python3"),
    categories={"technical": 1.0},
)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def setUp(self) -> None:
        self.cloud = make_cloud(PYTHON)


class TestNormalizeRequirements(ThisTestCase):
    """Test function."""

    def test_resolves_via_model_proposal(self) -> None:
        requirements = ["5+ years writing Python services"]
        proposals = {"5+ years writing Python services": "Python"}

        result = MOD.normalize_requirements(
            requirements, proposals=proposals, cloud=self.cloud
        )

        with self.subTest("resolution and provenance"):
            expected = [
                "python_programming",
                {"technical": 1.0},
                "5+ years writing Python services",
                False,
            ]
            found = [
                result[0].canonical_id,
                result[0].categories,
                result[0].text,
                result[0].unmapped,
            ]
            self.assertEqual(expected, found)

    def test_falls_back_to_literal_text(self) -> None:
        # No proposal, but the raw JD phrase is itself an exact alias.
        result = MOD.normalize_requirements(["python3"], cloud=self.cloud)
        expected = "python_programming"
        found = result[0].canonical_id
        self.assertEqual(expected, found)

    def test_unresolvable_is_unmapped_with_original_text(self) -> None:
        requirements = ["experience wrangling alpacas"]
        proposals = {"experience wrangling alpacas": "alpaca wrangling"}

        result = MOD.normalize_requirements(
            requirements, proposals=proposals, cloud=self.cloud
        )

        with self.subTest("unmapped with JD phrasing preserved"):
            expected = [True, None, {}, "experience wrangling alpacas"]
            found = [
                result[0].unmapped,
                result[0].canonical_id,
                result[0].categories,
                result[0].text,
            ]
            self.assertEqual(expected, found)

    def test_handles_missing_proposals(self) -> None:
        # Older cached JD parses have no canonical_skills mapping.
        result = MOD.normalize_requirements(
            ["Python", "alpaca wrangling"], proposals=None, cloud=self.cloud
        )
        expected = ["python_programming", None]
        found = [r.canonical_id for r in result]
        self.assertEqual(expected, found)

    def test_skips_empty_requirement_strings(self) -> None:
        result = MOD.normalize_requirements(["", "Python"], cloud=self.cloud)
        expected = 1
        found = len(result)
        self.assertEqual(expected, found)


# __END__
