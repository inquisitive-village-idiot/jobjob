#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase, mock

import jobjob.gapi.docs as MOD

LOGGER = logging.getLogger(__name__)


def _para(text: str) -> dict:
    return {"paragraph": {"elements": [{"textRun": {"content": text}}]}}


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_service_with_doc(self, content) -> mock.MagicMock:
        service = mock.MagicMock()
        service.documents.return_value.get.return_value.execute.return_value = {
            "body": {"content": content}
        }
        return service


class TestExtractDocText(ThisTestCase):
    """Test function."""

    def test_extracts_paragraph_and_table_text(self) -> None:
        content = [
            _para("Hello "),
            {
                "table": {
                    "tableRows": [
                        {"tableCells": [{"content": [_para("cell")]}]},
                    ]
                }
            },
        ]
        self.assertEqual("Hello cell", MOD.extract_doc_text(content))


class TestGetDocumentText(ThisTestCase):
    """Test function."""

    def test_reads_text_from_service(self) -> None:
        service = self.make_service_with_doc([_para("Resume body")])
        self.assertEqual("Resume body", MOD.get_document_text(service, "D"))


class TestApplyReplacements(ThisTestCase):
    """Test function."""

    def test_submits_replace_requests(self) -> None:
        service = mock.MagicMock()
        count = MOD.apply_replacements(service, "D", {"{OBJ}": "new", "{X}": "y"})

        with self.subTest("count"):
            self.assertEqual(2, count)
        with self.subTest("batchUpdate body"):
            _, kwargs = service.documents.return_value.batchUpdate.call_args
            requests = kwargs["body"]["requests"]
            texts = {r["replaceAllText"]["containsText"]["text"] for r in requests}
            self.assertEqual({"{OBJ}", "{X}"}, texts)

    def test_no_requests_skips_batch_update(self) -> None:
        service = mock.MagicMock()
        count = MOD.apply_replacements(service, "D", {})
        self.assertEqual(0, count)
        service.documents.return_value.batchUpdate.assert_not_called()


def _heading(text: str, style: str = "HEADING_1", start: int = 0, end: int = 0) -> dict:
    return {
        "startIndex": start,
        "endIndex": end,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": style},
            "elements": [{"textRun": {"content": text}}],
        },
    }


def _body(text: str, start: int, end: int) -> dict:
    return {
        "startIndex": start,
        "endIndex": end,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "elements": [{"textRun": {"content": text}}],
        },
    }


class TestIsHeading(ThisTestCase):
    """Test function."""

    def test_true_for_heading_style(self) -> None:
        self.assertTrue(MOD.is_heading(_heading("Objective")))

    def test_false_for_normal_text(self) -> None:
        self.assertFalse(MOD.is_heading(_body("just text", 1, 10)))


class TestFindSection(ThisTestCase):
    """Test function."""

    def _content(self) -> list:
        return [
            _heading("OBJECTIVE", start=1, end=11),
            _body("old objective\n", 11, 25),
            _heading("Key Career Highlights", start=25, end=47),
            _body("bullet one\n", 47, 58),
            _body("bullet two\n", 58, 69),
            _heading("Experience", start=69, end=80),
            _body("job\n", 80, 84),
        ]

    def test_matches_heading_case_insensitively(self) -> None:
        found = MOD.find_section(self._content(), "objective")
        self.assertIsNotNone(found)
        heading, body = found
        with self.subTest("located the heading"):
            self.assertEqual("OBJECTIVE", MOD.paragraph_text(heading).strip())
        with self.subTest("body stops at the next heading"):
            self.assertEqual(1, len(body))
            self.assertEqual("old objective", MOD.paragraph_text(body[0]).strip())

    def test_collects_all_bullets_until_next_heading(self) -> None:
        _, body = MOD.find_section(self._content(), "Key Career Highlights")
        self.assertEqual(
            ["bullet one", "bullet two"], [MOD.paragraph_text(b).strip() for b in body]
        )

    def test_returns_none_when_absent(self) -> None:
        self.assertIsNone(MOD.find_section(self._content(), "Nonexistent"))


class TestReplaceParagraphTextRequests(ThisTestCase):
    """Test function."""

    def test_deletes_text_keeps_newline_then_inserts(self) -> None:
        # Paragraph [11, 25): text occupies 11..24, the newline is at 24.
        reqs = MOD.replace_paragraph_text_requests(
            _body("old objective\n", 11, 25), "new"
        )
        with self.subTest("delete preserves the terminating newline"):
            rng = reqs[0]["deleteContentRange"]["range"]
            self.assertEqual({"startIndex": 11, "endIndex": 24}, rng)
        with self.subTest("insert at paragraph start"):
            self.assertEqual(11, reqs[1]["insertText"]["location"]["index"])
            self.assertEqual("new", reqs[1]["insertText"]["text"])

    def test_empty_paragraph_skips_delete(self) -> None:
        # An empty paragraph [5, 6) has only its newline — no text range to delete.
        reqs = MOD.replace_paragraph_text_requests(_body("\n", 5, 6), "x")
        self.assertEqual(1, len(reqs))
        self.assertIn("insertText", reqs[0])


class TestGetDocument(ThisTestCase):
    """Test function."""

    def test_returns_full_structure(self) -> None:
        service = self.make_service_with_doc([_body("x", 1, 3)])
        doc = MOD.get_document(service, "D")
        self.assertIn("body", doc)


class TestPageCount(ThisTestCase):
    """Test functions."""

    def test_estimates_pages_from_end_index(self) -> None:
        service = self.make_service_with_doc([{"endIndex": 10000}])
        self.assertEqual(2.0, MOD.estimate_page_count(service, "D"))

    def test_empty_content_returns_zero(self) -> None:
        service = self.make_service_with_doc([])
        self.assertEqual(0.0, MOD.estimate_page_count(service, "D"))

    def test_verify_true_within_limit(self) -> None:
        service = self.make_service_with_doc([{"endIndex": 5000}])
        self.assertTrue(MOD.verify_page_count(service, "D", max_pages=3))

    def test_verify_false_when_over(self) -> None:
        service = self.make_service_with_doc([{"endIndex": 30000}])
        self.assertFalse(MOD.verify_page_count(service, "D", max_pages=3))

    def test_verify_true_exactly_at_limit_with_buffer(self) -> None:
        # Exactly at max_pages + PAGE_BUFFER boundary should still pass
        # 3 pages + 0.5 buffer = 3.5; 3.5 * 5000 = 17500 chars
        service = self.make_service_with_doc([{"endIndex": 17500}])
        self.assertTrue(MOD.verify_page_count(service, "D", max_pages=3))


# __END__
