#!/usr/bin/env python3
"""Test."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import jobjob.structure.skillcloud as MOD

LOGGER = logging.getLogger(__name__)

VALID_CLOUD = """
[cloud]
esco_version = "v1.2.1"
retrieved = "2026-07-02"
categories = [
    "communication", "collaboration", "leadership",
    "creativity", "technical", "domain",
]

[[cloud.skill]]
id = "python_programming"
name = "Python (computer programming)"
aliases = ["Python", "python3"]
categories = { technical = 1.0 }
esco_uri = "http://data.europa.eu/esco/skill/ccd0a1d9"

[[cloud.skill]]
id = "technical_writing"
name = "technical writing"
aliases = ["documentation writing"]
categories = { communication = 0.6, technical = 0.4 }
esco_uri = "http://data.europa.eu/esco/skill/aaaa0001"
"""


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def write_cloud(self, content: str) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name, "cloud.toml")
        path.write_text(content, encoding="utf-8")
        return path


class TestLoadSkillCloud(ThisTestCase):
    """Test function."""

    def test_loads_valid_cloud(self) -> None:
        path = self.write_cloud(VALID_CLOUD)
        cloud = MOD.load_skill_cloud(path)

        with self.subTest("entry count"):
            expected = 2
            found = len(cloud)
            self.assertEqual(expected, found)

        with self.subTest("records esco version"):
            expected = "v1.2.1"
            found = cloud.esco_version
            self.assertEqual(expected, found)

        with self.subTest("entry fields"):
            skill = cloud.skills["technical_writing"]
            self.assertEqual("technical writing", skill.name)
            self.assertEqual(("documentation writing",), skill.aliases)
            self.assertEqual({"communication": 0.6, "technical": 0.4}, skill.categories)

    def test_raises_on_bad_weight_sum(self) -> None:
        content = VALID_CLOUD.replace(
            "{ communication = 0.6, technical = 0.4 }",
            "{ communication = 0.6, technical = 0.6 }",
        )
        path = self.write_cloud(content)
        with self.assertRaisesRegex(ValueError, "technical_writing"):
            MOD.load_skill_cloud(path)

    def test_raises_on_unknown_category(self) -> None:
        content = VALID_CLOUD.replace("{ technical = 1.0 }", "{ wizardry = 1.0 }")
        path = self.write_cloud(content)
        with self.assertRaisesRegex(ValueError, "wizardry"):
            MOD.load_skill_cloud(path)

    def test_raises_on_duplicate_id(self) -> None:
        content = VALID_CLOUD.replace(
            'id = "technical_writing"', 'id = "python_programming"'
        )
        path = self.write_cloud(content)
        with self.assertRaisesRegex(ValueError, "python_programming"):
            MOD.load_skill_cloud(path)

    def test_raises_on_missing_name(self) -> None:
        content = VALID_CLOUD.replace('name = "technical writing"\n', "")
        path = self.write_cloud(content)
        with self.assertRaisesRegex(ValueError, "missing id or name"):
            MOD.load_skill_cloud(path)

    def test_loads_packaged_cloud(self) -> None:
        # The shipped data file must always validate.
        cloud = MOD.load_skill_cloud()
        assert len(cloud) > 0


class TestSkillCloudResolve(ThisTestCase):
    """Test method."""

    def setUp(self) -> None:
        super().setUp()
        self.cloud = MOD.load_skill_cloud(self.write_cloud(VALID_CLOUD))

    def test_resolves_by_name_case_insensitive(self) -> None:
        expected = "python_programming"
        found = self.cloud.resolve("PYTHON (Computer Programming)")
        self.assertEqual(expected, found.id)

    def test_resolves_by_alias(self) -> None:
        expected = "python_programming"
        found = self.cloud.resolve("python3")
        self.assertEqual(expected, found.id)

    def test_resolves_by_id(self) -> None:
        expected = "technical_writing"
        found = self.cloud.resolve("technical_writing")
        self.assertEqual(expected, found.id)

    def test_id_precedence_over_alias(self) -> None:
        # An alias colliding with another entry's id must not shadow the id.
        content = VALID_CLOUD.replace(
            'aliases = ["documentation writing"]',
            'aliases = ["documentation writing", "python_programming"]',
        )
        cloud = MOD.load_skill_cloud(self.write_cloud(content))
        expected = "python_programming"
        found = cloud.resolve("python_programming")
        self.assertEqual(expected, found.id)

    def test_returns_none_on_miss(self) -> None:
        expected = None
        found = self.cloud.resolve("underwater basket weaving")
        self.assertEqual(expected, found)

    def test_returns_none_on_empty(self) -> None:
        expected = None
        found = self.cloud.resolve("")
        self.assertEqual(expected, found)


class TestNormalizeRequirements(ThisTestCase):
    """Test function."""

    def setUp(self) -> None:
        super().setUp()
        self.cloud = MOD.load_skill_cloud(self.write_cloud(VALID_CLOUD))

    def test_resolves_via_model_proposal(self) -> None:
        requirements = ["5+ years writing Python services"]
        proposals = {"5+ years writing Python services": "Python"}

        result = MOD.normalize_requirements(
            requirements, proposals=proposals, cloud=self.cloud
        )

        with self.subTest("canonical id attached"):
            expected = "python_programming"
            found = result[0].canonical_id
            self.assertEqual(expected, found)

        with self.subTest("category weights attached"):
            expected = {"technical": 1.0}
            found = result[0].categories
            self.assertEqual(expected, found)

        with self.subTest("original phrasing preserved"):
            expected = "5+ years writing Python services"
            found = result[0].text
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

        with self.subTest("unmapped"):
            assert result[0].unmapped
            self.assertIsNone(result[0].canonical_id)

        with self.subTest("keeps JD phrasing"):
            expected = "experience wrangling alpacas"
            found = result[0].text
            self.assertEqual(expected, found)

        with self.subTest("no categories"):
            expected = {}
            found = result[0].categories
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
