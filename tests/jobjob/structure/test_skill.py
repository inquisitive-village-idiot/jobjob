#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.skill as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_skills(self) -> list[MOD.Skill]:
        return [
            MOD.Skill(label="python", text="Python", keywords=("python", "py")),
            MOD.Skill(label="sql", text="SQL", keywords=("sql",)),
            MOD.Skill(label="docker", text="Docker"),
        ]


class TestSkill(ThisTestCase):
    """Test dataclass."""

    def test_defaults_keywords_to_empty_tuple(self) -> None:
        s = MOD.Skill(label="x", text="X")
        self.assertEqual((), s.keywords)

    def test_frozen(self) -> None:
        s = MOD.Skill(label="x", text="X")
        with self.assertRaises((AttributeError, TypeError)):
            s.label = "y"  # type: ignore[misc]


class TestSkillSet(ThisTestCase):
    """Test SkillSet defaults."""

    def test_default_number_is_twelve(self) -> None:
        ss = MOD.SkillSet(skills=())
        self.assertEqual(12, ss.default_number)


class TestMakeSkillSet(ThisTestCase):
    """Test factory function."""

    def test_wraps_skills_in_tuple(self) -> None:
        ss = MOD.make_skill_set(self.make_skills())
        self.assertIsInstance(ss.skills, tuple)
        self.assertEqual(3, len(ss.skills))

    def test_uses_default_number_when_not_given(self) -> None:
        ss = MOD.make_skill_set([])
        self.assertEqual(12, ss.default_number)

    def test_applies_default_number_override(self) -> None:
        ss = MOD.make_skill_set([], default_number=8)
        self.assertEqual(8, ss.default_number)

    def test_empty_skills_list(self) -> None:
        ss = MOD.make_skill_set([])
        self.assertEqual(0, len(ss.skills))


# __END__
