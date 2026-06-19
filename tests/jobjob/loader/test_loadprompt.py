#!/usr/bin/env python3
"""Test."""

from tests.fixtures import fixture_dir, fixture_path
import dataclasses as dcs
import logging
from unittest import TestCase

import jobjob.loader.loadprompt as MOD
from jobjob.loader import loadstatic, location
from jobjob.structure.job_decription import JobDescription

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestLoadPromptJobDescription(ThisTestCase):
    """Test function."""

    def test_returns_expected_prompt(self) -> None:
        job_description = fixture_path("job_description_mvp")
        prompt = location.get_prompt_path("job_description")

        fields = [(x.name, x.metadata.get("doc", "")) for x in dcs.fields(JobDescription)]
        field_txt = "\n".join(f"- {a}: {b}" for a, b in fields)
        text = loadstatic.load_pdf_text(job_description)

        expected = prompt.read_text().format(field_def=field_txt, text_content=text)
        found = MOD.load_prompt_job_description(job_description)
        self.assertEqual(expected, found)


# __END__
