#!/usr/bin/env python3
"""Test."""

import json
import logging
from pathlib import Path
from unittest import TestCase, mock

import jobjob.ailib.extract as MOD
from jobjob.structure.profile import LinkedInProfile

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestParsePdfToDataclass(ThisTestCase):
    """Test function."""

    def test_text_path_uses_query_service_directly(self) -> None:
        service = mock.MagicMock(__name__="service")
        service.return_value = json.dumps({"name": "Jane", "role": "VP"})

        result = MOD.parse_pdf_to_dataclass(
            Path("has_text.pdf"),
            LinkedInProfile,
            "linkedin_profile",
            service,
            use_cache=False,
            _load_text=lambda p: "extracted profile text",
        )

        self.assertEqual("Jane", result.name)
        service.assert_called_once()
        service.complete_document.assert_not_called()

    def test_vision_fallback_when_no_text(self) -> None:
        service = mock.MagicMock()
        service.complete_document.return_value = json.dumps(
            {"name": "Ada", "company": "Analytical"}
        )

        result = MOD.parse_pdf_to_dataclass(
            Path("image_only.pdf"),
            LinkedInProfile,
            "linkedin_profile",
            service,
            use_cache=True,  # NOTE: vision path forces no-cache internally
            _load_text=lambda p: None,
        )

        with self.subTest("used vision document call"):
            service.complete_document.assert_called_once()
            args = service.complete_document.call_args.args
            self.assertEqual(Path("image_only.pdf"), args[1])
        with self.subTest("built the profile"):
            self.assertEqual("Ada", result.name)
            self.assertEqual("Analytical", result.company)


# __END__
