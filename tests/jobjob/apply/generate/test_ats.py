#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase, mock

import jobjob.apply.generate.ats as MOD
from jobjob.structure.job_decription import JobDescription
from jobjob.structure.skill import Skill, SkillSet

LOGGER = logging.getLogger(__name__)


class FakeCloudSkill:
    def __init__(self, id_: str, name: str, aliases=(), categories=None) -> None:
        self.id = id_
        self.name = name
        self.aliases = tuple(aliases)
        self.categories = categories or {"technical": 1.0}


class FakeCloud:
    def __init__(self, *skills: FakeCloudSkill) -> None:
        self.skills = {s.id: s for s in skills}
        self._index = {}
        for s in skills:
            self._index[s.id.lower()] = s.id
            self._index[s.name.lower()] = s.id
            for alias in s.aliases:
                self._index[alias.lower()] = s.id

    def resolve(self, text: str):
        key = (text or "").strip().lower()
        canonical_id = self._index.get(key)
        return self.skills.get(canonical_id) if canonical_id else None


PYTHON = FakeCloudSkill("python", "Python (computer programming)", aliases=("Python",))
SQL = FakeCloudSkill("sql", "SQL")
KUBERNETES = FakeCloudSkill("kubernetes", "Kubernetes", aliases=("k8s",))


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


def make_job(**kwargs) -> JobDescription:
    defaults = {
        f: ""
        for f in (
            "company_name",
            "role_title",
            "department",
            "seniority_level",
            "salary",
            "hiring_manager",
            "summary",
        )
    }
    defaults.update(
        {
            f: ()
            for f in (
                "location",
                "key_requirements",
                "responsibilities",
                "technical_skills",
                "soft_skills",
                "keywords",
            )
        }
    )
    defaults.update(kwargs)
    return JobDescription(**defaults)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def patch_cloud(self, cloud: FakeCloud) -> None:
        patcher = mock.patch.object(MOD, "get_skill_cloud", return_value=cloud)
        patcher.start()
        self.addCleanup(patcher.stop)
        # normalize_requirements resolves via its own module-level accessor.
        patcher2 = mock.patch(
            "jobjob.structure.normalize.get_skill_cloud", return_value=cloud
        )
        patcher2.start()
        self.addCleanup(patcher2.stop)

    def declared(self, *ids: str) -> SkillSet:
        skills = tuple(
            Skill(label=i, text=i, canonical_id=i, categories={"technical": 1.0})
            for i in ids
        )
        return SkillSet(skills=skills)


class TestAssessAts(ThisTestCase):
    """Test function."""

    def test_skipped_when_no_document(self) -> None:
        result = MOD.assess_ats(None, make_job(), {})

        expected = (True, None)
        found = (result.skipped, result.coverage_score)
        self.assertEqual(expected, found)

    def test_buckets_and_coverage(self) -> None:
        self.patch_cloud(FakeCloud(PYTHON, SQL, KUBERNETES))
        job = make_job(
            key_requirements=("Python", "SQL"),  # weight 1.0 each
            technical_skills=("k8s",),  # weight 0.75, present via alias
        )
        skills = {"critical_supported": [{"skill": "SQL", "evidence": "STAR: db"}]}
        doc = make_doc("Wrote Python services. Deployed with k8s.")

        result = MOD.assess_ats(doc, job, skills, skill_set=self.declared("sql"))

        with self.subTest("present via name and alias"):
            self.assertIn("Python (computer programming)", result.present)
            self.assertIn("Kubernetes", result.present)

        with self.subTest("missing + evidenced"):
            expected = ("SQL",)
            found = result.missing_evidenced
            self.assertEqual(expected, found)

        with self.subTest("coverage = (1.0 + 0.75) / (1.0 + 1.0 + 0.75)"):
            expected = round(1.75 / 2.75, 2)
            found = result.coverage_score
            self.assertEqual(expected, found)

    def test_recommendation_requires_evidence_and_declaration(self) -> None:
        self.patch_cloud(FakeCloud(PYTHON, SQL, KUBERNETES))
        job = make_job(key_requirements=("Python", "SQL", "Kubernetes"))
        skills = {
            "critical_supported": [
                {"skill": "Python", "evidence": "STAR: automation"},
                {"skill": "SQL", "evidence": "STAR: reporting db"},
            ]
        }
        doc = make_doc("A resume that mentions none of the required skills.")
        # Only python is declared in the skills file.
        result = MOD.assess_ats(doc, job, skills, skill_set=self.declared("python"))

        with self.subTest("evidenced + declared -> recommendation with citation"):
            found = result.recommendations
            self.assertEqual(1, len(found))
            self.assertIn("Python (computer programming)", found[0])
            self.assertIn("STAR: automation", found[0])

        with self.subTest("evidenced + undeclared -> skills-file candidate"):
            expected = ("SQL",)
            found = result.skills_file_candidates
            self.assertEqual(expected, found)

        with self.subTest("unevidenced -> up-skill target, never recommended"):
            expected = ("Kubernetes",)
            found = result.upskill_targets
            self.assertEqual(expected, found)
            self.assertNotIn("Kubernetes", " ".join(result.recommendations))

    def test_unmapped_listed_but_unscored(self) -> None:
        self.patch_cloud(FakeCloud(PYTHON))
        job = make_job(key_requirements=("Python", "quantum telepathy"))
        doc = make_doc("Python everywhere.")

        result = MOD.assess_ats(doc, job, {}, skill_set=None)

        expected = (("quantum telepathy",), 1.0)  # scored over canonical only
        found = (result.unmapped, result.coverage_score)
        self.assertEqual(expected, found)

    def test_deterministic(self) -> None:
        self.patch_cloud(FakeCloud(PYTHON, SQL))
        job = make_job(key_requirements=("Python", "SQL"))
        skills = {"critical_supported": [{"skill": "SQL", "evidence": "e"}]}
        doc = make_doc("Python here.")

        expected = MOD.assess_ats(doc, job, skills, skill_set=self.declared("sql"))
        found = MOD.assess_ats(doc, job, skills, skill_set=self.declared("sql"))
        self.assertEqual(expected, found)

    def test_fit_gaps_include_supported_nonrequired_skills(self) -> None:
        self.patch_cloud(FakeCloud(PYTHON, SQL))
        job = make_job(key_requirements=("Python",))
        skills = {"strong_supporting": [{"skill": "SQL", "relevance": "adjacent"}]}
        doc = make_doc("Python only.")

        result = MOD.assess_ats(doc, job, skills, skill_set=None)

        expected = ("SQL",)
        found = result.fit_gaps
        self.assertEqual(expected, found)


class TestTermInText(ThisTestCase):
    """Test function (word-boundary matching)."""

    def test_word_boundaries(self) -> None:
        cases = [
            ("Python", "I write Python daily", True),
            ("Python", "pythonic code", False),
            ("Python", "PYTHON scripting", True),
            ("C++", "Expert in C++ and Rust", True),
            # NOTE: bare "Go" is deliberately not exercised -- word boundaries
            #   cannot save it from e.g. "go to market"; keeping ambiguous
            #   short names out of cloud aliases is a curation concern.
            ("golang", "Services written in golang", True),
            ("", "anything", False),
        ]
        for term, text, expected in cases:
            with self.subTest(term=term, text=text):
                self.assertEqual(expected, MOD._term_in_text(term, text))


# __END__
