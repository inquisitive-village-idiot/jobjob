#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase, mock

import jobjob.autofill.__main__ as MOD
from jobjob.config import Settings
from jobjob.structure.applicant import Applicant
from jobjob.structure.experience import ExperienceSet

LOGGER = logging.getLogger(__name__)


def _settings(**kwargs) -> Settings:
    defaults = {
        "applicant": Applicant(name="Ada Lovelace"),
        "anthropic_api_key": "test-key",
    }
    defaults.update(kwargs)
    return Settings(**defaults)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestParseArgs(ThisTestCase):
    """Test function."""

    def test_parses_url_and_flags(self) -> None:
        args = MOD.parse_args(
            ["https://acme.wd1.myworkdayjobs.com/job/123", "--headless"]
        )
        with self.subTest("url"):
            self.assertEqual("https://acme.wd1.myworkdayjobs.com/job/123", args.url)
        with self.subTest("headless"):
            self.assertTrue(args.headless)
        with self.subTest("assisted-detached defaults false"):
            self.assertFalse(args.assisted_detached)

    def test_parses_assisted_detached_flag(self) -> None:
        args = MOD.parse_args(["https://example.test/job", "--assisted-detached"])
        self.assertTrue(args.assisted_detached)


class TestMain(ThisTestCase):
    """Test function."""

    def _run(self, argv):
        with mock.patch.object(MOD, "load_settings", return_value=_settings()):
            with mock.patch.object(
                MOD, "load_experience", return_value=ExperienceSet()
            ):
                with mock.patch.object(MOD, "run_autofill") as mock_run:
                    retcode = MOD.main(argv)
        return retcode, mock_run

    def test_forwards_url_and_headless(self) -> None:
        retcode, mock_run = self._run(["https://example.test/job", "--headless"])
        args, kwargs = mock_run.call_args
        with self.subTest("returns 0"):
            self.assertEqual(0, retcode)
        with self.subTest("url forwarded"):
            self.assertEqual("https://example.test/job", args[0])
        with self.subTest("headless forwarded"):
            self.assertTrue(kwargs["headless"])
        with self.subTest("assisted_detached is None when flag absent"):
            self.assertIsNone(kwargs["assisted_detached"])

    def test_assisted_detached_flag_forces_true(self) -> None:
        _, mock_run = self._run(["https://example.test/job", "--assisted-detached"])
        _, kwargs = mock_run.call_args
        self.assertTrue(kwargs["assisted_detached"] is True)

    def test_no_adapter_error_returns_2(self) -> None:
        with mock.patch.object(MOD, "load_settings", return_value=_settings()):
            with mock.patch.object(
                MOD, "load_experience", return_value=ExperienceSet()
            ):
                with mock.patch.object(
                    MOD, "run_autofill", side_effect=MOD.NoAdapterError("nope")
                ):
                    retcode = MOD.main(["https://unsupported.example/job"])
        self.assertEqual(2, retcode)

    def test_playwright_unavailable_returns_1(self) -> None:
        with mock.patch.object(MOD, "load_settings", return_value=_settings()):
            with mock.patch.object(
                MOD, "load_experience", return_value=ExperienceSet()
            ):
                with mock.patch.object(
                    MOD,
                    "run_autofill",
                    side_effect=MOD.PlaywrightUnavailableError("install it"),
                ):
                    retcode = MOD.main(["https://example.test/job"])
        self.assertEqual(1, retcode)


# __END__
