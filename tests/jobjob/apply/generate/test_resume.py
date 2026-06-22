#!/usr/bin/env python3
"""Test."""

from unittest import TestCase, mock

import jobjob.apply.generate.resume as MOD
from jobjob.structure.highlight import Highlight
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.template import ResumeSection


def _job(**kwargs) -> JobDescription:
    defaults = {f: "" for f in ("company_name", "role_title", "department",
                                "seniority_level", "salary", "hiring_manager", "summary")}
    defaults.update({f: () for f in ("location", "key_requirements", "responsibilities",
                                     "technical_skills", "soft_skills", "keywords")})
    defaults.update(kwargs)
    return JobDescription(**defaults)


class TestBuildObjectivePrompt(TestCase):
    """The objective prompt's company-accuracy rule is industry-configurable."""

    def test_injects_industry_when_set(self) -> None:
        prompt = MOD._build_objective_prompt(
            _job(company_name="Acme", role_title="Editor"),
            "current objective",
            "science journalism",
        )
        self.assertIn("science journalism", prompt)
        self.assertIn("actual industry", prompt)

    def test_neutral_rule_when_unset(self) -> None:
        prompt = MOD._build_objective_prompt(_job(), "current objective")
        self.assertIn("Describe the company accurately", prompt)
        self.assertNotIn("actual industry", prompt)

    def test_blank_industry_is_neutral(self) -> None:
        prompt = MOD._build_objective_prompt(_job(), "current objective", "   ")
        self.assertNotIn("actual industry", prompt)

    def test_no_hardcoded_domain_example(self) -> None:
        # The old prompt baked in a biotech/pharma example; it must be gone.
        for industry in (None, "fintech"):
            prompt = MOD._build_objective_prompt(_job(), "obj", industry)
            self.assertNotIn("biotech", prompt.lower())
            self.assertNotIn("pharma", prompt.lower())


def _heading(text: str, start: int, end: int) -> dict:
    return {
        "startIndex": start, "endIndex": end,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": "HEADING_1"},
            "elements": [{"textRun": {"content": text}}],
        },
    }


def _bullet(text: str, start: int, end: int) -> dict:
    return {
        "startIndex": start, "endIndex": end,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "bullet": {"listId": "L1"},
            "elements": [{"textRun": {"content": text}}],
        },
    }


def _body(text: str, start: int, end: int) -> dict:
    return {
        "startIndex": start, "endIndex": end,
        "paragraph": {
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "elements": [{"textRun": {"content": text}}],
        },
    }


# A resume with an Objective paragraph and two highlight bullets, plus indices.
def _content() -> list:
    return [
        _heading("OBJECTIVE", 1, 11),
        _body("To obtain a PLACEHOLDER role.\n", 11, 40),
        _heading("Key Career Highlights", 40, 62),
        _bullet("Old bullet one\n", 62, 77),
        _bullet("Old bullet two\n", 77, 92),
    ]


_SECTIONS = (
    ResumeSection(heading="Objective", section="objective"),
    ResumeSection(heading="Key Career Highlights", section="highlights"),
)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_docs(self, content) -> mock.MagicMock:
        docs = mock.MagicMock()
        get = docs.documents.return_value.get.return_value.execute
        get.return_value = {"body": {"content": content}}
        return docs

    def requests(self, docs) -> list:
        body = docs.documents.return_value.batchUpdate.call_args.kwargs["body"]
        return body["requests"]


class TestTailorResume(ThisTestCase):
    """Test function."""

    def _run(self, *, content=None, highlights=("New one", "New two"), objective="New objective"):
        docs = self.make_docs(content if content is not None else _content())
        job = _job(company_name="Acme", role_title="Principal Engineer",
                   key_requirements=("Python",))
        text, changes, issues = MOD.tailor_resume(
            docs, "DOC", job,
            selected_highlights=[Highlight("ctx", h, ()) for h in highlights],
            query_service=mock.MagicMock(),
            sections=_SECTIONS,
            use_cache=False,
            _query=mock.MagicMock(return_value={"objective": objective}),
        )
        return docs, text, changes, issues

    def test_rewrites_objective_in_place(self) -> None:
        docs, _, changes, issues = self._run()
        reqs = self.requests(docs)
        with self.subTest("inserts the new objective at the objective paragraph start"):
            inserts = {r["insertText"]["location"]["index"]: r["insertText"]["text"]
                       for r in reqs if "insertText" in r}
            self.assertEqual("New objective", inserts[11])
        with self.subTest("objective change recorded, no issues"):
            self.assertTrue(any(c.startswith("Objective:") for c in changes))
            self.assertEqual([], issues)

    def test_places_highlights_verbatim_at_bullet_starts(self) -> None:
        docs, _, _, _ = self._run()
        reqs = self.requests(docs)
        inserts = {r["insertText"]["location"]["index"]: r["insertText"]["text"]
                   for r in reqs if "insertText" in r}
        self.assertEqual("New one", inserts[62])
        self.assertEqual("New two", inserts[77])

    def test_swaps_role_placeholder_last(self) -> None:
        docs, _, _, _ = self._run()
        reqs = self.requests(docs)
        with self.subTest("role token replaced"):
            replaces = [r for r in reqs if "replaceAllText" in r]
            self.assertEqual("PLACEHOLDER",
                             replaces[0]["replaceAllText"]["containsText"]["text"])
            self.assertEqual("Principal Engineer",
                             replaces[0]["replaceAllText"]["replaceText"])
        with self.subTest("replaceAllText comes after all index edits"):
            self.assertIn("replaceAllText", reqs[-1])

    def test_index_edits_ordered_descending(self) -> None:
        # Index-based requests must run high-index-first so they don't shift each other.
        docs, _, _, _ = self._run()
        reqs = self.requests(docs)
        anchors = [r["insertText"]["location"]["index"] for r in reqs if "insertText" in r]
        self.assertEqual(sorted(anchors, reverse=True), anchors)

    def test_appends_extra_bullets_inside_the_list(self) -> None:
        docs, _, changes, _ = self._run(highlights=("a", "b", "c"))
        reqs = self.requests(docs)
        # The third highlight is inserted before the last bullet's newline (index 91).
        appended = [r["insertText"] for r in reqs
                    if "insertText" in r and r["insertText"]["location"]["index"] == 91]
        self.assertTrue(appended and "c" in appended[0]["text"])
        self.assertTrue(any("Added 1 highlight" in c for c in changes))

    def test_removes_surplus_bullets(self) -> None:
        docs, _, changes, _ = self._run(highlights=("only one",))
        reqs = self.requests(docs)
        deletes = [r["deleteContentRange"]["range"] for r in reqs
                   if "deleteContentRange" in r]
        # The surplus second bullet [77, 92) is deleted.
        self.assertIn({"startIndex": 77, "endIndex": 92}, deletes)
        self.assertTrue(any("Removed 1 highlight" in c for c in changes))

    def test_missing_section_recorded_as_issue(self) -> None:
        # A resume without the highlights heading: that section is skipped + reported.
        content = [_heading("OBJECTIVE", 1, 11), _body("Obj.\n", 11, 17)]
        docs, _, _, issues = self._run(content=content)
        self.assertTrue(any("Key Career Highlights" in i for i in issues))

    def test_malformed_objective_output_is_skipped(self) -> None:
        docs = self.make_docs(_content())
        job = _job(company_name="Acme", role_title="Eng", key_requirements=())
        _, _, issues = MOD.tailor_resume(
            docs, "DOC", job,
            selected_highlights=[Highlight("c", "h", ())],
            query_service=mock.MagicMock(),
            sections=_SECTIONS,
            use_cache=False,
            _query=mock.MagicMock(return_value="not json"),
        )
        self.assertTrue(any("Objective" in i for i in issues))


# __END__
