#!/usr/bin/env python3
"""Test."""

import copy
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import jobjob.structure.skillcloud as MOD

LOGGER = logging.getLogger(__name__)

# Fixture as data: tests mutate copies of this mapping and encode to TOML,
# rather than string-replacing a TOML literal.
VALID_CLOUD = {
    "esco_version": "v1.2.1",
    "retrieved": "2026-07-02",
    "skill": [
        {
            "id": "python_programming",
            "name": "Python (computer programming)",
            "aliases": ["Python", "python3"],
            "categories": {"technical": 1.0},
            "esco_uri": "http://data.europa.eu/esco/skill/ccd0a1d9",
        },
        {
            "id": "technical_writing",
            "name": "technical writing",
            "aliases": ["documentation writing"],
            "categories": {"communication": 0.6, "technical": 0.4},
            "esco_uri": "http://data.europa.eu/esco/skill/aaaa0001",
        },
    ],
}


def encode_cloud_toml(cloud: dict) -> str:
    """Encode the fixture mapping as skill-cloud TOML."""
    lines = [
        "[cloud]",
        f'esco_version = "{cloud["esco_version"]}"',
        f'retrieved = "{cloud["retrieved"]}"',
        "",
    ]
    for entry in cloud["skill"]:
        lines.append("[[cloud.skill]]")
        for key in ("id", "name", "esco_uri"):
            if key in entry:
                lines.append(f'{key} = "{entry[key]}"')
        aliases = ", ".join(f'"{a}"' for a in entry.get("aliases", []))
        lines.append(f"aliases = [{aliases}]")
        cats = ", ".join(f"{k} = {v}" for k, v in entry.get("categories", {}).items())
        lines.append(f"categories = {{ {cats} }}")
        lines.append("")
    return "\n".join(lines)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def write_cloud(self, cloud: dict) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name, "cloud.toml")
        path.write_text(encode_cloud_toml(cloud), encoding="utf-8")
        return path

    def make_cloud(self, **overrides) -> dict:
        """Deep copy of the valid fixture, with optional per-entry overrides."""
        cloud = copy.deepcopy(VALID_CLOUD)
        cloud.update(overrides)
        return cloud


class TestLoadSkillCloud(ThisTestCase):
    """Test function."""

    def test_loads_valid_cloud(self) -> None:
        path = self.write_cloud(self.make_cloud())
        result = MOD.load_skill_cloud(path)

        with self.subTest("entry count"):
            expected = 2
            found = len(result)
            self.assertEqual(expected, found)

        with self.subTest("records esco version"):
            expected = "v1.2.1"
            found = result.esco_version
            self.assertEqual(expected, found)

        with self.subTest("entry fields"):
            skill = result.skills["technical_writing"]
            expected = [
                "technical writing",
                ("documentation writing",),
                {"communication": 0.6, "technical": 0.4},
            ]
            found = [skill.name, skill.aliases, skill.categories]
            self.assertEqual(expected, found)

    def test_raises_on_bad_weight_sum(self) -> None:
        cloud = self.make_cloud()
        cloud["skill"][1]["categories"] = {"communication": 0.6, "technical": 0.6}
        path = self.write_cloud(cloud)
        with self.assertRaisesRegex(ValueError, "technical_writing"):
            MOD.load_skill_cloud(path)

    def test_raises_on_unknown_category(self) -> None:
        cloud = self.make_cloud()
        cloud["skill"][0]["categories"] = {"wizardry": 1.0}
        path = self.write_cloud(cloud)
        with self.assertRaisesRegex(ValueError, "wizardry"):
            MOD.load_skill_cloud(path)

    def test_raises_on_duplicate_id(self) -> None:
        cloud = self.make_cloud()
        cloud["skill"][1]["id"] = "python_programming"
        path = self.write_cloud(cloud)
        with self.assertRaisesRegex(ValueError, "python_programming"):
            MOD.load_skill_cloud(path)

    def test_raises_on_missing_name(self) -> None:
        cloud = self.make_cloud()
        del cloud["skill"][1]["name"]
        path = self.write_cloud(cloud)
        with self.assertRaisesRegex(ValueError, "missing id or name"):
            MOD.load_skill_cloud(path)

    def test_loads_packaged_cloud(self) -> None:
        # The shipped data file must always validate.
        result = MOD.load_skill_cloud()
        assert len(result) > 0


class TestSkillCloudResolve(ThisTestCase):
    """Test method."""

    def setUp(self) -> None:
        super().setUp()
        self.cloud = MOD.load_skill_cloud(self.write_cloud(self.make_cloud()))

    def test_resolves_by_name_case_insensitive(self) -> None:
        result = self.cloud.resolve("PYTHON (Computer Programming)")
        expected = "python_programming"
        found = result.id
        self.assertEqual(expected, found)

    def test_resolves_by_alias(self) -> None:
        result = self.cloud.resolve("python3")
        expected = "python_programming"
        found = result.id
        self.assertEqual(expected, found)

    def test_resolves_by_id(self) -> None:
        result = self.cloud.resolve("technical_writing")
        expected = "technical_writing"
        found = result.id
        self.assertEqual(expected, found)

    def test_id_precedence_over_alias(self) -> None:
        # An alias colliding with another entry's id must not shadow the id.
        cloud = self.make_cloud()
        cloud["skill"][1]["aliases"] = ["documentation writing", "python_programming"]
        loaded = MOD.load_skill_cloud(self.write_cloud(cloud))

        result = loaded.resolve("python_programming")
        expected = "python_programming"
        found = result.id
        self.assertEqual(expected, found)

    def test_returns_none_on_miss(self) -> None:
        expected = None
        found = self.cloud.resolve("underwater basket weaving")
        self.assertEqual(expected, found)

    def test_returns_none_on_empty(self) -> None:
        expected = None
        found = self.cloud.resolve("")
        self.assertEqual(expected, found)


# __END__
