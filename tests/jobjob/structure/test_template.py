#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.template as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_set(self) -> MOD.TemplateSet:
        return MOD.make_template_set(
            [
                MOD.ResumeTemplate(name="a", archetype="A", doc_id="DA"),
                MOD.ResumeTemplate(name="b", archetype="B", doc_id="DB"),
            ],
            default="b",
        )


class TestTemplateSet(ThisTestCase):
    """Test methods."""

    def test_by_name(self) -> None:
        self.assertEqual("DA", self.make_set().by_name("a").doc_id)

    def test_by_name_missing_returns_none(self) -> None:
        self.assertIsNone(self.make_set().by_name("zzz"))

    def test_require_returns_template_when_found(self) -> None:
        result = self.make_set().require("a")
        self.assertEqual("DA", result.doc_id)

    def test_require_raises_for_unknown(self) -> None:
        with self.assertRaisesRegex(KeyError, "Unknown resume template"):
            self.make_set().require("zzz")

    def test_default_template_uses_default_name(self) -> None:
        self.assertEqual("b", self.make_set().default_template().name)

    def test_default_template_falls_back_to_first_when_default_name_not_found(
        self,
    ) -> None:
        templates = (MOD.ResumeTemplate(name="only", archetype="O", doc_id="D"),)
        result = MOD.TemplateSet(
            templates=templates, default="missing"
        ).default_template()
        self.assertEqual("only", result.name)

    def test_default_template_falls_back_to_first(self) -> None:
        templates = (MOD.ResumeTemplate(name="only", archetype="O", doc_id="D"),)
        result = MOD.TemplateSet(templates=templates).default_template()
        self.assertEqual("only", result.name)

    def test_default_template_empty_is_none(self) -> None:
        self.assertIsNone(MOD.TemplateSet(templates=()).default_template())

    def test_names_returns_all_template_names(self) -> None:
        self.assertEqual(("a", "b"), self.make_set().names())


class TestSharedSections(ThisTestCase):
    """Test that shared sections attach to every template."""

    def test_sections_attached_to_each_template(self) -> None:
        sections = [MOD.ResumeSection(heading="Objective", section="objective")]
        result = MOD.make_template_set(
            [
                MOD.ResumeTemplate(name="a", archetype="A", doc_id="DA"),
                MOD.ResumeTemplate(name="b", archetype="B", doc_id="DB"),
            ],
            sections=sections,
        )
        self.assertEqual(tuple(sections), result.by_name("a").sections)
        self.assertEqual(tuple(sections), result.by_name("b").sections)

    def test_template_keeps_its_own_sections(self) -> None:
        own = (MOD.ResumeSection(heading="Summary", section="objective"),)
        result = MOD.make_template_set(
            [MOD.ResumeTemplate(name="a", archetype="A", doc_id="DA", sections=own)],
            sections=[MOD.ResumeSection(heading="Objective", section="objective")],
        )
        self.assertEqual(own, result.by_name("a").sections)


# __END__
