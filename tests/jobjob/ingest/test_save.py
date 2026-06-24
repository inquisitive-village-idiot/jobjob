#!/usr/bin/env python3
"""Tests for persisting an imported draft into content TOML / reference docs."""

import pytest

from jobjob.ingest.save import (
    save_background,
    save_experience,
    save_highlights,
    save_skills,
)
from jobjob.loader.loadcontent import load_experience, load_highlights, load_skills
from jobjob.structure.experience import Role
from jobjob.structure.highlight import Highlight
from jobjob.structure.skill import Skill

_HIGHLIGHTS = (
    Highlight(context="a", text="First thing.", keywords=("x",), topic="Creativity"),
    Highlight(
        context="b", text="Second thing.", keywords=("y", "z"), topic="Leadership"
    ),
)
_SKILLS = (Skill(label="fact_checking", text="Fact-Checking", keywords=("accuracy",)),)
_ROLES = (
    Role(
        company="The Lattice Review",
        title="Senior Correspondent",
        location="Remote",
        start="2021-04",
        current=True,
        description="- Led the desk.\n- Built a workflow.",
    ),
    Role(
        company="The Lattice Review",
        title="Correspondent",
        start="2018-06",
        end="2021-04",
        description="- Covered science.",
    ),
)


class TestSaveHighlights:
    def test_replace_into_new_file_roundtrips(self, tmp_path):
        path = tmp_path / "content" / "highlights.toml"
        n = save_highlights(path, _HIGHLIGHTS, mode="replace")
        assert n == 2
        loaded = load_highlights(path)
        assert [h.context for h in loaded.highlights] == ["a", "b"]
        # topic + keywords survive the round trip
        assert loaded.highlights[0].topic == "Creativity"
        assert loaded.highlights[1].keywords == ("y", "z")

    def test_append_adds_without_dropping(self, tmp_path):
        path = tmp_path / "highlights.toml"
        save_highlights(path, _HIGHLIGHTS, mode="replace")
        save_highlights(path, _HIGHLIGHTS[:1], mode="append")
        assert len(load_highlights(path).highlights) == 3

    def test_replace_clears_previous_items(self, tmp_path):
        path = tmp_path / "highlights.toml"
        save_highlights(path, _HIGHLIGHTS, mode="replace")
        save_highlights(path, _HIGHLIGHTS[:1], mode="replace")
        assert len(load_highlights(path).highlights) == 1

    def test_replace_preserves_tool_config(self, tmp_path):
        path = tmp_path / "highlights.toml"
        path.write_text("[tool.highlights]\ndefault_number = 9\n", encoding="utf-8")
        save_highlights(path, _HIGHLIGHTS, mode="replace")
        assert load_highlights(path).default_number == 9

    def test_unknown_mode_raises(self, tmp_path):
        with pytest.raises(ValueError):
            save_highlights(tmp_path / "h.toml", _HIGHLIGHTS, mode="bogus")


class TestSaveSkills:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "skills.toml"
        save_skills(path, _SKILLS, mode="replace")
        loaded = load_skills(path)
        assert [s.label for s in loaded.skills] == ["fact_checking"]
        assert loaded.skills[0].text == "Fact-Checking"


class TestSaveExperience:
    def test_replace_roundtrips_and_groups(self, tmp_path):
        path = tmp_path / "content" / "experience.toml"
        n = save_experience(path, _ROLES, mode="replace")
        assert n == 2
        loaded = load_experience(path)
        assert [r.title for r in loaded.roles] == [
            "Senior Correspondent",
            "Correspondent",
        ]
        # The two adjacent same-employer roles read back as one company block.
        blocks = [(b.company, len(b.roles)) for b in loaded.grouped()]
        assert blocks == [("The Lattice Review", 2)]

    def test_current_flag_and_bullets_survive(self, tmp_path):
        path = tmp_path / "experience.toml"
        save_experience(path, _ROLES, mode="replace")
        loaded = load_experience(path)
        assert loaded.roles[0].current is True
        assert loaded.roles[0].bullets() == ("Led the desk.", "Built a workflow.")

    def test_append_adds_without_dropping(self, tmp_path):
        path = tmp_path / "experience.toml"
        save_experience(path, _ROLES, mode="replace")
        save_experience(path, _ROLES[:1], mode="append")
        assert len(load_experience(path).roles) == 3

    def test_unknown_mode_raises(self, tmp_path):
        with pytest.raises(ValueError):
            save_experience(tmp_path / "e.toml", _ROLES, mode="bogus")


class TestSaveBackground:
    def test_replace_overwrites(self, tmp_path):
        path = tmp_path / "reference" / "background.md"
        save_background(path, "One.", mode="replace")
        save_background(path, "Two.", mode="replace")
        assert path.read_text(encoding="utf-8") == "Two.\n"

    def test_append_concatenates(self, tmp_path):
        path = tmp_path / "background.md"
        save_background(path, "One.", mode="replace")
        save_background(path, "Two.", mode="append")
        assert path.read_text(encoding="utf-8") == "One.\n\nTwo.\n"

    def test_append_to_missing_file_just_writes(self, tmp_path):
        path = tmp_path / "background.md"
        save_background(path, "Only.", mode="append")
        assert path.read_text(encoding="utf-8") == "Only.\n"
