#!/usr/bin/env python3
"""Tests for the blank-profile skeleton builder."""

import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from jobjob.loader import skeleton
from jobjob.loader.loadcontent import load_highlights, load_skills, load_templates


class TestCreateBlankProfile(TestCase):
    def _build(self, root: Path) -> Path:
        return skeleton.create_blank_profile(root / "prof")

    def test_creates_full_structure(self) -> None:
        with TemporaryDirectory() as d:
            dest = self._build(Path(d))
            for rel in (
                "content/highlights.toml",
                "content/skills.toml",
                "content/templates.toml",
                "reference/background.md",
                "reference/writing_style.md",
                "config/.profile",
            ):
                self.assertTrue((dest / rel).is_file(), rel)
            self.assertTrue((dest / "reference" / "cover_letters").is_dir())
            self.assertTrue((dest / "reference" / "stars").is_dir())

    def test_content_loads_to_empty_sets(self) -> None:
        with TemporaryDirectory() as d:
            dest = self._build(Path(d))
            self.assertEqual(
                (), load_highlights(dest / "content" / "highlights.toml").highlights
            )
            self.assertEqual(
                (), load_skills(dest / "content" / "skills.toml").skills
            )
            templates = load_templates(dest / "content" / "templates.toml")
            # A default template + the two standard sections exist, but no content.
            self.assertTrue(len(templates.templates) >= 1)

    def test_no_example_persona_content(self) -> None:
        with TemporaryDirectory() as d:
            dest = self._build(Path(d))
            blob = "\n".join(
                p.read_text() for p in dest.rglob("*") if p.is_file()
            ).lower()
            for token in ("tila", "telomere", "half_life", "inkstained"):
                self.assertNotIn(token, blob)

    def test_profile_config_is_blank_but_valid_keys(self) -> None:
        with TemporaryDirectory() as d:
            dest = self._build(Path(d))
            text = (dest / "config" / ".profile").read_text()
            self.assertIn("APPLICANT_NAME", text)
            self.assertIn("RESUME_TEMPLATE_ID", text)
            self.assertIn('APPLICANT_NAME=""', text)

    def test_idempotent_preserves_edits(self) -> None:
        with TemporaryDirectory() as d:
            dest = self._build(Path(d))
            edited = dest / "content" / "skills.toml"
            edited.write_text('[tool.skills]\ndefault_number = 99\n')
            skeleton.create_blank_profile(dest)
            self.assertEqual(
                99, tomllib.loads(edited.read_text())["tool"]["skills"]["default_number"]
            )


# __END__
