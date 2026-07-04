#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.apply.generate.ats_checks as MOD

LOGGER = logging.getLogger(__name__)


def make_doc(text: str, **extra) -> dict:
    """Minimal Google Docs JSON with one paragraph of body text."""
    return {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": text}}],
                    }
                }
            ]
        },
        **extra,
    }


def make_heading(text: str) -> dict:
    return {
        "paragraph": {
            "paragraphStyle": {"namedStyleType": "HEADING_1"},
            "elements": [{"textRun": {"content": text}}],
        }
    }


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestCheckContentInTables(ThisTestCase):
    """Test function."""

    def test_passes_without_tables(self) -> None:
        result = MOD.check_content_in_tables(make_doc("plain text"))
        expected = (True, "")
        found = (result.passed, result.reason)
        self.assertEqual(expected, found)

    def test_warns_on_table(self) -> None:
        doc = make_doc("text")
        doc["body"]["content"].append({"table": {"rows": 1}})

        result = MOD.check_content_in_tables(doc)

        expected = False
        found = result.passed
        self.assertEqual(expected, found)
        self.assertIn("table", result.reason)


class TestCheckNonstandardHeadings(ThisTestCase):
    """Test function."""

    def test_passes_with_recognized_headings(self) -> None:
        doc = make_doc("text")
        doc["body"]["content"].append(make_heading("Experience"))

        result = MOD.check_nonstandard_headings(doc)

        expected = True
        found = result.passed
        self.assertEqual(expected, found)

    def test_warns_and_names_unrecognized_heading(self) -> None:
        doc = make_doc("text")
        doc["body"]["content"].append(make_heading("My Jazz Odyssey"))

        result = MOD.check_nonstandard_headings(doc)

        expected = False
        found = result.passed
        self.assertEqual(expected, found)
        self.assertIn("My Jazz Odyssey", result.reason)

    def test_heading_match_is_case_insensitive(self) -> None:
        doc = make_doc("text")
        doc["body"]["content"].append(make_heading("EXPERIENCE"))

        result = MOD.check_nonstandard_headings(doc)

        expected = True
        found = result.passed
        self.assertEqual(expected, found)


class TestCheckImagesOrTextBoxes(ThisTestCase):
    """Test function."""

    def test_passes_without_objects(self) -> None:
        result = MOD.check_images_or_text_boxes(make_doc("text"))
        expected = True
        found = result.passed
        self.assertEqual(expected, found)

    def test_warns_on_inline_objects(self) -> None:
        result = MOD.check_images_or_text_boxes(
            make_doc("text", inlineObjects={"obj1": {}})
        )
        expected = False
        found = result.passed
        self.assertEqual(expected, found)

    def test_warns_on_positioned_objects(self) -> None:
        result = MOD.check_images_or_text_boxes(
            make_doc("text", positionedObjects={"obj1": {}})
        )
        expected = False
        found = result.passed
        self.assertEqual(expected, found)


class TestCheckMultiColumnLayout(ThisTestCase):
    """Test function."""

    def test_passes_single_column(self) -> None:
        result = MOD.check_multi_column_layout(make_doc("text"))
        expected = True
        found = result.passed
        self.assertEqual(expected, found)

    def test_warns_on_multiple_columns(self) -> None:
        doc = make_doc("text")
        doc["body"]["content"].append(
            {"sectionBreak": {"sectionStyle": {"columnProperties": [{}, {}]}}}
        )

        result = MOD.check_multi_column_layout(doc)

        expected = False
        found = result.passed
        self.assertEqual(expected, found)


class TestRunParseabilityChecks(ThisTestCase):
    """Test function."""

    def test_runs_every_registered_check(self) -> None:
        result = MOD.run_parseability_checks(make_doc("plain"))
        expected = [check.__name__ for check in MOD.PARSEABILITY_CHECKS]
        found = [f"check_{c.name.replace('-', '_')}" for c in result]
        self.assertEqual(expected, found)

    def test_clean_document_passes_all(self) -> None:
        doc = make_doc("Plain paragraph")
        doc["body"]["content"].append(make_heading("Experience"))

        result = MOD.run_parseability_checks(doc)

        expected = True
        found = all(c.passed for c in result)
        self.assertEqual(expected, found)


# __END__
