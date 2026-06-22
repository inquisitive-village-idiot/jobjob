#!/usr/bin/env python3
"""Test."""

import dataclasses as dcs
import logging
from string import Template
from unittest import TestCase

import jobjob.loader.loadprompt as MOD
from jobjob.loader import loadstatic, location
from jobjob.structure.job_decription import JobDescription
from tests.fixtures import fixture_path

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestRenderPrompt(ThisTestCase):
    """The brace-safe $-substitution renderer with explicit template paths."""

    def _write(self, tmp, text):
        p = tmp / "t.txt"
        p.write_text(text, encoding="utf-8")
        return p

    def test_substitutes_dollar_placeholders(self) -> None:
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        path = self._write(tmp, "Hello ${name}, role ${role}.")
        out = MOD.render_prompt("t", {"name": "Tila", "role": "writer"}, path)
        self.assertEqual("Hello Tila, role writer.", out)

    def test_literal_braces_are_safe(self) -> None:
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        path = self._write(tmp, 'Return JSON: {"x": ${val}}')
        out = MOD.render_prompt("t", {"val": "1"}, path)
        self.assertEqual('Return JSON: {"x": 1}', out)

    def test_unknown_placeholder_left_intact(self) -> None:
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        path = self._write(tmp, "Keep ${unknown} and set ${known}.")
        out = MOD.render_prompt("t", {"known": "ok"}, path)
        self.assertEqual("Keep ${unknown} and set ok.", out)


class TestLoadPromptJobDescription(ThisTestCase):
    """Test function."""

    def test_returns_expected_prompt(self) -> None:
        job_description = fixture_path("job_description_mvp")
        prompt = location.get_prompt_path("job_description")

        fields = [
            (x.name, x.metadata.get("doc", "")) for x in dcs.fields(JobDescription)
        ]
        field_txt = "\n".join(f"- {a}: {b}" for a, b in fields)
        text = loadstatic.load_pdf_text(job_description)

        expected = Template(prompt.read_text()).safe_substitute(
            field_def=field_txt, text_content=text
        )
        found = MOD.load_prompt_job_description(job_description)
        self.assertEqual(expected, found)


# __END__
