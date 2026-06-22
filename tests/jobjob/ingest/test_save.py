#!/usr/bin/env python3
"""Tests for persisting an imported draft into content TOML / reference docs."""

import pytest

from jobjob.ingest.save import save_background, save_highlights, save_skills
from jobjob.loader.loadcontent import load_highlights, load_skills
from jobjob.structure.highlight import Highlight
from jobjob.structure.skill import Skill

_HIGHLIGHTS = (
    Highlight(context="a", text="First thing.", keywords=("x",), topic="Creativity"),
    Highlight(
        context="b", text="Second thing.", keywords=("y", "z"), topic="Leadership"
    ),
)
_SKILLS = (Skill(label="fact_checking", text="Fact-Checking", keywords=("accuracy",)),)


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
