#!/usr/bin/env python3
"""Tests for resume-import extraction (no network: the AI query is injected)."""

from pathlib import Path

import pytest

from jobjob.ingest.resume_import import (
    BACKGROUND_MODES,
    ResumeImportDraft,
    build_prompt,
    draft_to_dict,
    extract_resume,
    highlight_from_dict,
    role_from_dict,
    skill_from_dict,
)

_MODEL_JSON = {
    "identity": {
        "name": "Tila Mer",
        "email": "tila@example.com",
        "phone": "  ",  # blank -> dropped
        "linkedin": "linkedin.com/in/tilamer",
        "fax": "555-1234",  # unknown field -> ignored
    },
    "objective": "Tell true stories about cells.",
    "sections": ["Experience", "Education", ""],
    "highlights": [
        {
            "context": "Half Life column",
            "topic": "Creativity",
            "text": "Grew the Half-Life column into the second-most-clipped feature.",
            "keywords": ["writing", "audience"],
        },
        {  # no context -> derived from text; collides? no
            "text": "Saved the print science section.",
            "topic": "Leadership",
            "keywords": "leadership",  # scalar -> coerced to list
        },
        {"text": "   "},  # blank -> dropped
    ],
    "skills": [
        {"label": "Fact Checking", "text": "Fact-Checking", "keywords": ["accuracy"]},
        {"text": ""},  # dropped
    ],
    "experience": [
        {  # current role; description as a bullet list
            "company": "The Lattice Review",
            "title": "Senior Science Correspondent",
            "location": "Remote",
            "start": "2021-04",
            "end": "",
            "current": True,
            "description": ["Lead the print science desk.", "Built a data workflow."],
        },
        {  # same employer, earlier role -> kept separate (the promotion case)
            "company": "The Lattice Review",
            "title": "Science Correspondent",
            "start": "2018-06",
            "end": "2021-04",
            "current": "no",  # string flag -> coerced to False
            "description": "- Covered materials science.",
        },
        {"location": "Boston"},  # no company/title -> dropped
    ],
    "background": "Tila Mer is a print science correspondent.",
}


def _fake_query(prompt, _query_service=None, use_cache=True):
    assert "RESUME TEXT" in prompt
    return _MODEL_JSON


def _extract(**kwargs):
    return extract_resume(
        Path("resume.txt"),
        object(),
        _query=_fake_query,
        _load_text=lambda p: "Some resume text",
        **kwargs,
    )


class TestExtractResume:
    def test_builds_draft(self):
        draft = _extract()
        assert isinstance(draft, ResumeImportDraft)
        assert draft.objective == "Tell true stories about cells."
        assert draft.background.startswith("Tila Mer")

    def test_drops_blank_highlights_and_skills(self):
        draft = _extract()
        assert len(draft.highlights) == 2  # the blank one is dropped
        assert len(draft.skills) == 1

    def test_topic_and_keywords_carry(self):
        draft = _extract()
        assert draft.highlights[0].topic == "Creativity"
        assert draft.highlights[0].keywords == ("writing", "audience")
        # scalar keyword coerced to a one-element tuple
        assert draft.highlights[1].keywords == ("leadership",)

    def test_context_and_label_slugified(self):
        draft = _extract()
        assert draft.highlights[0].context == "half_life_column"
        assert draft.skills[0].label == "fact_checking"

    def test_sections_filtered(self):
        draft = _extract()
        assert draft.sections == ("Experience", "Education")

    def test_experience_extracted_and_filtered(self):
        draft = _extract()
        # The entry with neither company nor title is dropped.
        assert len(draft.experience) == 2
        assert [r.title for r in draft.experience] == [
            "Senior Science Correspondent",
            "Science Correspondent",
        ]

    def test_experience_keeps_same_employer_roles_separate(self):
        # Both roles share an employer but stay as two adjacent entries, so the
        # ExperienceSet grouping reads them as one company block of two roles.
        from jobjob.structure.experience import make_experience_set

        draft = _extract()
        blocks = [
            (b.company, len(b.roles))
            for b in make_experience_set(draft.experience).grouped()
        ]
        assert blocks == [("The Lattice Review", 2)]

    def test_experience_description_and_current_coerced(self):
        draft = _extract()
        current, prior = draft.experience
        # list-of-bullets -> one "- " line each; bullets() strips the markers
        assert current.bullets() == (
            "Lead the print science desk.",
            "Built a data workflow.",
        )
        assert current.current is True
        # string flag "no" coerces to False
        assert prior.current is False

    def test_identity_extracted_and_cleaned(self):
        draft = _extract()
        # Blank fields dropped, unknown fields ignored, known ones kept and stripped.
        assert draft.identity == {
            "name": "Tila Mer",
            "email": "tila@example.com",
            "linkedin": "linkedin.com/in/tilamer",
        }

    def test_identity_absent_is_empty(self):
        draft = extract_resume(
            Path("r.txt"),
            object(),
            _query=lambda *a, **k: {"objective": "x"},
            _load_text=lambda p: "text",
        )
        assert draft.identity == {}

    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            extract_resume(
                Path("x.pdf"), object(), _query=_fake_query, _load_text=lambda p: "   "
            )

    def test_non_dict_response_raises(self):
        with pytest.raises(ValueError):
            extract_resume(
                Path("x.txt"),
                object(),
                _query=lambda *a, **k: ["not", "a", "dict"],
                _load_text=lambda p: "text",
            )


class TestBuildPrompt:
    def test_modes_change_guidance(self):
        conservative = build_prompt("resume", background_mode="conservative")
        fuller = build_prompt("resume", background_mode="fuller")
        assert "conservative" in conservative.lower()
        assert "fuller" in fuller.lower()

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            build_prompt("resume", background_mode="bogus")

    def test_resume_text_with_braces_is_safe(self):
        # Braces in the resume text must not break str.format substitution.
        prompt = build_prompt("salary {expectations} are {flexible}")
        assert "salary {expectations} are {flexible}" in prompt

    def test_voice_anchor_only_in_fuller(self, tmp_path):
        (tmp_path / "writing_style.md").write_text(
            "Wry, plain-spoken.", encoding="utf-8"
        )
        fuller = build_prompt(
            "resume", background_mode="fuller", reference_dir=tmp_path
        )
        conservative = build_prompt(
            "resume", background_mode="conservative", reference_dir=tmp_path
        )
        assert "VOICE SAMPLES" in fuller
        assert "Wry, plain-spoken." in fuller
        assert "VOICE SAMPLES" not in conservative

    def test_all_modes_constant(self):
        assert set(BACKGROUND_MODES) == {"conservative", "fuller"}


class TestFromDictHelpers:
    def test_highlight_dedupes_contexts(self):
        seen: set[str] = set()
        a = highlight_from_dict({"context": "dup", "text": "one"}, seen)
        b = highlight_from_dict({"context": "dup", "text": "two"}, seen)
        assert a.context == "dup"
        assert b.context == "dup_2"

    def test_skill_default_label_from_text(self):
        s = skill_from_dict({"text": "Data Analysis"})
        assert s.label == "data_analysis"

    def test_role_from_dict_coerces_fields(self):
        role = role_from_dict(
            {
                "company": "  Acme  ",
                "title": "Engineer",
                "current": "present",  # string -> True
                "description": ["Shipped things", "  ", "Mentored peers"],
            }
        )
        assert role.company == "Acme"
        assert role.current is True
        # blank bullet dropped; markers added then stripped by bullets()
        assert role.bullets() == ("Shipped things", "Mentored peers")

    def test_draft_to_dict_roundtrips_shape(self):
        draft = _extract()
        out = draft_to_dict(draft)
        assert set(out) >= {
            "identity",
            "objective",
            "sections",
            "background",
            "highlights",
            "skills",
            "experience",
        }
        assert out["highlights"][0]["topic"] == "Creativity"
        assert out["skills"][0]["label"] == "fact_checking"
        assert out["identity"]["name"] == "Tila Mer"
        assert out["experience"][0]["company"] == "The Lattice Review"
        assert out["experience"][0]["current"] is True
