#!/usr/bin/env python3
"""Test loadcontent using explicit TOML paths to bypass the get_root_dir bug.

NOTE: Tests in test_loadcontent.py that call load_*() without arguments fail
because get_root_dir() returns the wrong path when the repo is named the same
as the Python package ("jobjob"). These tests use explicit paths directly to
the static TOML files so they run regardless of the location-resolution bug.
"""

import logging
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import jobjob.loader.loadcontent as MOD

LOGGER = logging.getLogger(__name__)

# Absolute path to the bundled example content dir in this repo (the fallback).
_STATIC_CONTENT = (
    Path(__file__).parent.parent.parent.parent / "static" / "example" / "content"
)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def get_tmpdir(self) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)


class TestLoadTomlTable(ThisTestCase):
    """Test private helper."""

    def test_returns_expected_table(self) -> None:
        p = Path(self.get_tmpdir(), "sample.toml")
        p.write_text('[tool.highlights]\ndefault_number = 5\n')
        result = MOD._load_toml_table(p, "highlights")
        self.assertEqual(5, result["default_number"])

    def test_raises_for_missing_table(self) -> None:
        p = Path(self.get_tmpdir(), "sample.toml")
        p.write_text('[tool.other]\nfoo = 1\n')
        with self.assertRaisesRegex(ValueError, r"\[tool\.highlights\]"):
            MOD._load_toml_table(p, "highlights")


class TestLoadHighlightsExplicit(ThisTestCase):
    """Test load_highlights using real static TOML."""

    def setUp(self) -> None:
        self.path = _STATIC_CONTENT / "highlights.toml"
        self.result = MOD.load_highlights(path=self.path)

    def test_returns_highlight_set(self) -> None:
        from jobjob.structure.highlight import HighlightSet
        self.assertIsInstance(self.result, HighlightSet)

    def test_loads_at_least_one_highlight(self) -> None:
        self.assertGreater(len(self.result.highlights), 0)

    def test_loads_selection_defaults(self) -> None:
        expected = (6, 900, 600)
        found = (
            self.result.default_number,
            self.result.max_characters,
            self.result.min_characters,
        )
        self.assertEqual(expected, found)

    def test_text_is_stripped(self) -> None:
        sample = self.result.highlights[0].text
        self.assertEqual(sample, sample.strip())

    def test_enabled_excludes_disabled(self) -> None:
        enabled = self.result.enabled()
        self.assertTrue(all(h.enabled for h in enabled))

    def test_by_context_indexes_highlights(self) -> None:
        contexts = self.result.by_context()
        self.assertGreater(len(contexts), 0)
        for h in self.result.highlights:
            self.assertIn(h.context, contexts)


class TestLoadHighlightsFromToml(ThisTestCase):
    """Test load_highlights with a hand-crafted TOML for edge cases."""

    def _write_toml(self, text: str) -> Path:
        p = Path(self.get_tmpdir(), "highlights.toml")
        p.write_text(text)
        return p

    def test_highlights_with_no_keywords_default_to_empty_tuple(self) -> None:
        p = self._write_toml(
            '[tool.highlights]\n'
            '[[tool.highlights.highlight]]\n'
            'context = "x"\n'
            'text = "some text"\n'
        )
        result = MOD.load_highlights(path=p)
        self.assertEqual((), result.highlights[0].keywords)

    def test_disabled_highlight_is_loaded_but_marked(self) -> None:
        p = self._write_toml(
            '[tool.highlights]\n'
            '[[tool.highlights.highlight]]\n'
            'context = "x"\ntext = "text"\nenabled = false\n'
        )
        result = MOD.load_highlights(path=p)
        self.assertFalse(result.highlights[0].enabled)

    def test_overrides_default_number(self) -> None:
        p = self._write_toml(
            '[tool.highlights]\ndefault_number = 3\n'
        )
        result = MOD.load_highlights(path=p)
        self.assertEqual(3, result.default_number)

    def test_loads_topic_when_present(self) -> None:
        p = self._write_toml(
            '[tool.highlights]\n'
            '[[tool.highlights.highlight]]\n'
            'context = "x"\ntext = "text"\ntopic = "Technical"\n'
        )
        result = MOD.load_highlights(path=p)
        self.assertEqual("Technical", result.highlights[0].topic)

    def test_topic_defaults_to_empty_string(self) -> None:
        p = self._write_toml(
            '[tool.highlights]\n'
            '[[tool.highlights.highlight]]\n'
            'context = "x"\ntext = "text"\n'
        )
        result = MOD.load_highlights(path=p)
        self.assertEqual("", result.highlights[0].topic)


class TestLoadSkillsExplicit(ThisTestCase):
    """Test load_skills using real static TOML."""

    def setUp(self) -> None:
        self.path = _STATIC_CONTENT / "skills.toml"
        self.result = MOD.load_skills(path=self.path)

    def test_returns_skill_set(self) -> None:
        from jobjob.structure.skill import SkillSet
        self.assertIsInstance(self.result, SkillSet)

    def test_loads_at_least_one_skill(self) -> None:
        self.assertGreater(len(self.result.skills), 0)

    def test_skills_have_label_and_text(self) -> None:
        for skill in self.result.skills:
            with self.subTest(skill.label):
                self.assertTrue(skill.label)
                self.assertTrue(skill.text)


class TestLoadSkillsFromToml(ThisTestCase):
    """Test load_skills edge cases via hand-crafted TOML."""

    def test_skill_with_no_keywords_defaults_to_empty_tuple(self) -> None:
        p = Path(self.get_tmpdir(), "skills.toml")
        p.write_text(
            '[tool.skills]\n'
            '[[tool.skills.skill]]\n'
            'label = "python"\ntext = "Python"\n'
        )
        result = MOD.load_skills(path=p)
        self.assertEqual((), result.skills[0].keywords)

    def test_overrides_default_number(self) -> None:
        p = Path(self.get_tmpdir(), "skills.toml")
        p.write_text('[tool.skills]\ndefault_number = 8\n')
        result = MOD.load_skills(path=p)
        self.assertEqual(8, result.default_number)


class TestLoadTemplatesExplicit(ThisTestCase):
    """Test load_templates using real static TOML."""

    def setUp(self) -> None:
        self.path = _STATIC_CONTENT / "templates.toml"
        self.result = MOD.load_templates(path=self.path)

    def test_loads_templates(self) -> None:
        self.assertGreater(len(self.result.templates), 0)

    def test_has_print_correspondent(self) -> None:
        self.assertIn("print_correspondent", self.result.names())

    def test_has_default_set(self) -> None:
        self.assertIsNotNone(self.result.default)


class TestLoadTemplatesEdgeCases(ThisTestCase):
    """Test load_templates fallback and empty path logic."""

    def test_fallback_doc_id_when_path_is_none_and_content_path_raises(self) -> None:
        with mock.patch.object(MOD, "get_content_path", side_effect=ValueError):
            result = MOD.load_templates(fallback_doc_id="FALLBACK_ID")
        self.assertEqual("FALLBACK_ID", result.by_name("default").doc_id)

    def test_returns_empty_when_no_path_and_no_fallback(self) -> None:
        with mock.patch.object(MOD, "get_content_path", side_effect=ValueError):
            result = MOD.load_templates()
        self.assertEqual(0, len(result.templates))

    def test_templates_with_no_keywords_default_to_empty_tuple(self) -> None:
        p = Path(self.get_tmpdir(), "templates.toml")
        p.write_text(
            '[tool.templates]\n'
            '[[tool.templates.template]]\n'
            'name = "default"\narchetype = "General"\ndoc_id = "D123"\n'
        )
        result = MOD.load_templates(path=p)
        self.assertEqual((), result.templates[0].keywords)

    def test_section_enabled_defaults_to_true(self) -> None:
        p = Path(self.get_tmpdir(), "templates.toml")
        p.write_text(
            '[tool.templates]\n'
            '[[tool.templates.section]]\n'
            'heading = "Objective"\nsection = "objective"\n'
            '[[tool.templates.template]]\n'
            'name = "default"\narchetype = "General"\ndoc_id = "D123"\n'
        )
        result = MOD.load_templates(path=p)
        section = result.by_name("default").sections[0]
        self.assertTrue(section.enabled)

    def test_section_enabled_false_is_loaded(self) -> None:
        p = Path(self.get_tmpdir(), "templates.toml")
        p.write_text(
            '[tool.templates]\n'
            '[[tool.templates.section]]\n'
            'heading = "Objective"\nsection = "objective"\nenabled = false\n'
            '[[tool.templates.section]]\n'
            'heading = "Key Career Highlights"\nsection = "highlights"\n'
            '[[tool.templates.template]]\n'
            'name = "default"\narchetype = "General"\ndoc_id = "D123"\n'
        )
        result = MOD.load_templates(path=p)
        sections = result.by_name("default").sections
        by_kind = {s.section: s.enabled for s in sections}
        self.assertEqual({"objective": False, "highlights": True}, by_kind)


# __END__
