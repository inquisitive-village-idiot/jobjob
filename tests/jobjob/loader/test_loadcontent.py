#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase, mock

import jobjob.loader.loadcontent as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestLoadHighlights(ThisTestCase):
    """Test function. Uses the real static/content/highlights.toml."""

    def setUp(self) -> None:
        self.result = MOD.load_highlights()

    def test_loads_selection_defaults(self) -> None:
        expected = (6, 900, 600)
        found = (
            self.result.default_number,
            self.result.max_characters,
            self.result.min_characters,
        )
        self.assertEqual(expected, found)

    def test_loads_highlights(self) -> None:
        self.assertGreater(len(self.result.highlights), 0)

    def test_includes_python_engineering_after_toml_fix(self) -> None:
        # NOTE: guards the [[higlight]] -> [[tool.highlights.highlight]] typo fix.
        contexts = set(self.result.by_context())
        self.assertIn("half_life_column", contexts)

    def test_enabled_excludes_disabled(self) -> None:
        enabled = self.result.enabled()
        self.assertTrue(all(x.enabled for x in enabled))
        self.assertLessEqual(len(enabled), len(self.result.highlights))

    def test_text_is_stripped(self) -> None:
        sample = self.result.highlights[0].text
        self.assertEqual(sample, sample.strip())


class TestLoadTemplates(ThisTestCase):
    """Test function."""

    def test_loads_templates_from_static_toml(self) -> None:
        result = MOD.load_templates()
        names = set(result.names())
        self.assertIn("print_correspondent", names)
        self.assertIn("features_writer", names)
        self.assertEqual("print_correspondent", result.default)

    def test_attaches_sections_to_each_template(self) -> None:
        result = MOD.load_templates()
        sections = result.by_name("print_correspondent").sections
        kinds = {s.section for s in sections}
        headings = {s.heading.casefold() for s in sections}
        self.assertEqual({"objective", "highlights"}, kinds)
        self.assertIn("objective", headings)

    def test_fallback_to_single_default_when_no_toml(self) -> None:
        # NOTE: simulate a missing templates.toml to exercise the env-id fallback.
        with mock.patch.object(MOD, "get_content_path", side_effect=ValueError):
            result = MOD.load_templates(fallback_doc_id="ENVID")

        self.assertEqual(("default",), result.names())
        self.assertEqual("ENVID", result.by_name("default").doc_id)


class TestLoadSkills(ThisTestCase):
    """Test function. Uses the real static/content/skills.toml."""

    def setUp(self) -> None:
        self.result = MOD.load_skills()

    def test_loads_default_number(self) -> None:
        self.assertEqual(12, self.result.default_number)

    def test_loads_skills_with_label_and_text(self) -> None:
        self.assertGreater(len(self.result.skills), 0)
        first = self.result.skills[0]
        self.assertTrue(first.label)
        self.assertTrue(first.text)


class TestLoadExperience(ThisTestCase):
    """Test function. Uses the real static/example/content/experience.toml."""

    def setUp(self) -> None:
        self.result = MOD.load_experience()

    def test_loads_roles(self) -> None:
        self.assertGreater(len(self.result.roles), 0)

    def test_groups_adjacent_same_company_roles(self) -> None:
        # The example persona has two adjacent Lattice Review roles (a promotion),
        # which must collapse into one company block of two roles.
        blocks = [(b.company, len(b.roles)) for b in self.result.grouped()]
        self.assertIn(("The Lattice Review", 2), blocks)

    def test_strips_description_whitespace(self) -> None:
        sample = self.result.roles[0].description
        self.assertEqual(sample, sample.strip())

    def test_missing_file_returns_empty_set(self) -> None:
        with mock.patch.object(
            MOD, "get_content_path", side_effect=ValueError("not found")
        ):
            found = MOD.load_experience()
        self.assertEqual((), found.roles)


# __END__
