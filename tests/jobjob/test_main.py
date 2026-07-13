#!/usr/bin/env python3
"""Test the top-level CLI dispatcher."""

import logging
from unittest import TestCase, mock

import jobjob.__main__ as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestDispatch(TestCase):
    """Test function."""

    def test_routes_to_subcommand_with_remaining_args(self) -> None:
        handler = mock.MagicMock(return_value=0)
        with mock.patch.dict(MOD.COMMANDS, {"apply": handler}, clear=True):
            code = MOD.main(["apply", "jd.pdf", "--skip-drive"])
        self.assertEqual(0, code)
        handler.assert_called_once_with(["jd.pdf", "--skip-drive"])

    def test_unknown_command_returns_2(self) -> None:
        self.assertEqual(2, MOD.main(["bogus"]))

    def test_no_args_returns_2(self) -> None:
        self.assertEqual(2, MOD.main([]))

    def test_help_returns_0(self) -> None:
        self.assertEqual(0, MOD.main(["--help"]))


class TestFullBuildRenameCommands(TestCase):
    """`build`/`apply`/dropped-`autofill` wiring (full-build-rename)."""

    def test_build_dispatches_to_document_generation(self) -> None:
        result = MOD.COMMANDS["build"]
        expected = MOD.apply_main
        found = result
        self.assertIs(expected, found)

    def test_apply_dispatches_to_autofill(self) -> None:
        result = MOD.COMMANDS["apply"]
        expected = MOD.autofill_main
        found = result
        self.assertIs(expected, found)

    def test_autofill_is_no_longer_a_command(self) -> None:
        result = "autofill" in MOD.COMMANDS
        expected = False
        found = result
        self.assertEqual(expected, found)

    def test_autofill_command_returns_2(self) -> None:
        result = MOD.main(["autofill"])
        expected = 2
        found = result
        self.assertEqual(expected, found)


# __END__
