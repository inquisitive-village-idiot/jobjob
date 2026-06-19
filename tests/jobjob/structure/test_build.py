#!/usr/bin/env python3
"""Test."""

import dataclasses as dcs
import logging
from collections.abc import Iterable
from unittest import TestCase

import jobjob.structure.build as MOD

LOGGER = logging.getLogger(__name__)


@dcs.dataclass
class Sample:
    name: str = dcs.field(default="")
    tags: Iterable[str] = dcs.field(default_factory=list)


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestFromMapping(ThisTestCase):
    """Test function."""

    def test_maps_present_fields(self) -> None:
        result = MOD.from_mapping(Sample, {"name": "x", "tags": ["a", "b"]})
        self.assertEqual("x", result.name)
        self.assertEqual(["a", "b"], result.tags)

    def test_defaults_missing_str_to_empty(self) -> None:
        result = MOD.from_mapping(Sample, {"tags": ["a"]})
        self.assertEqual("", result.name)

    def test_defaults_missing_collection_to_empty_tuple(self) -> None:
        result = MOD.from_mapping(Sample, {"name": "x"})
        self.assertEqual((), result.tags)

    def test_coerces_scalar_string_for_collection_field(self) -> None:
        # NOTE: guards the char-by-char bug — a scalar location must wrap to a list.
        result = MOD.from_mapping(Sample, {"name": "x", "tags": "Gaithersburg, MD"})
        self.assertEqual(["Gaithersburg, MD"], result.tags)

    def test_does_not_wrap_str_field(self) -> None:
        result = MOD.from_mapping(Sample, {"name": "Acme", "tags": []})
        self.assertEqual("Acme", result.name)

    def test_ignores_unknown_keys(self) -> None:
        result = MOD.from_mapping(Sample, {"name": "x", "tags": [], "extra": 1})
        self.assertEqual("x", result.name)


# __END__
