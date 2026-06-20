#!/usr/bin/env python3
"""Test."""

import logging
from unittest import TestCase

import jobjob.structure.highlight as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def make_highlights(self) -> list[MOD.Highlight]:
        return [
            MOD.Highlight(context="a", text="Alpha", keywords=("alpha",), enabled=True),
            MOD.Highlight(context="b", text="Beta", keywords=("beta",), enabled=False),
            MOD.Highlight(context="c", text="Gamma", keywords=(), enabled=True),
        ]


class TestHighlight(ThisTestCase):
    """Test dataclass."""

    def test_defaults_keywords_to_empty_tuple(self) -> None:
        h = MOD.Highlight(context="x", text="X")
        self.assertEqual((), h.keywords)

    def test_defaults_enabled_to_true(self) -> None:
        h = MOD.Highlight(context="x", text="X")
        self.assertTrue(h.enabled)

    def test_defaults_topic_to_empty_string(self) -> None:
        h = MOD.Highlight(context="x", text="X")
        self.assertEqual("", h.topic)

    def test_carries_topic(self) -> None:
        h = MOD.Highlight(context="x", text="X", topic="Technical")
        self.assertEqual("Technical", h.topic)


class TestHighlightSet(ThisTestCase):
    """Test HighlightSet methods."""

    def test_enabled_returns_only_enabled(self) -> None:
        hs = MOD.HighlightSet(highlights=tuple(self.make_highlights()))
        enabled = hs.enabled()
        self.assertEqual(2, len(enabled))
        self.assertTrue(all(h.enabled for h in enabled))

    def test_enabled_returns_all_when_all_enabled(self) -> None:
        highlights = tuple(
            MOD.Highlight(context=str(i), text=str(i), enabled=True) for i in range(3)
        )
        hs = MOD.HighlightSet(highlights=highlights)
        self.assertEqual(3, len(hs.enabled()))

    def test_enabled_returns_empty_when_all_disabled(self) -> None:
        highlights = tuple(
            MOD.Highlight(context=str(i), text=str(i), enabled=False) for i in range(3)
        )
        hs = MOD.HighlightSet(highlights=highlights)
        self.assertEqual(0, len(hs.enabled()))

    def test_by_context_returns_mapping(self) -> None:
        hs = MOD.HighlightSet(highlights=tuple(self.make_highlights()))
        index = hs.by_context()
        self.assertIn("a", index)
        self.assertIn("b", index)
        self.assertIn("c", index)

    def test_by_context_includes_disabled(self) -> None:
        hs = MOD.HighlightSet(highlights=tuple(self.make_highlights()))
        index = hs.by_context()
        self.assertFalse(index["b"].enabled)

    def test_disabling_a_topic_group_excludes_it_from_enabled(self) -> None:
        # Mirrors the per-topic toggle: flipping every highlight in a topic off
        # removes the whole group from selection (which filters on enabled()).
        highlights = (
            MOD.Highlight(context="a", text="A", topic="Technical", enabled=False),
            MOD.Highlight(context="b", text="B", topic="Technical", enabled=False),
            MOD.Highlight(context="c", text="C", topic="Leadership", enabled=True),
        )
        hs = MOD.HighlightSet(highlights=highlights)
        enabled = hs.enabled()
        self.assertEqual({"c"}, {h.context for h in enabled})
        self.assertTrue(all(h.topic != "Technical" for h in enabled))


class TestMakeHighlightSet(ThisTestCase):
    """Test factory function."""

    def test_wraps_highlights_in_tuple(self) -> None:
        hs = MOD.make_highlight_set(self.make_highlights())
        self.assertIsInstance(hs.highlights, tuple)
        self.assertEqual(3, len(hs.highlights))

    def test_uses_defaults_when_overrides_are_none(self) -> None:
        hs = MOD.make_highlight_set([])
        self.assertEqual(6, hs.default_number)
        self.assertEqual(900, hs.max_characters)
        self.assertEqual(600, hs.min_characters)

    def test_applies_default_number_override(self) -> None:
        hs = MOD.make_highlight_set([], default_number=10)
        self.assertEqual(10, hs.default_number)

    def test_applies_max_characters_override(self) -> None:
        hs = MOD.make_highlight_set([], max_characters=1200)
        self.assertEqual(1200, hs.max_characters)

    def test_applies_min_characters_override(self) -> None:
        hs = MOD.make_highlight_set([], min_characters=400)
        self.assertEqual(400, hs.min_characters)

    def test_applies_multiple_overrides(self) -> None:
        hs = MOD.make_highlight_set(
            self.make_highlights(),
            default_number=4,
            max_characters=500,
            min_characters=200,
        )
        self.assertEqual(4, hs.default_number)
        self.assertEqual(500, hs.max_characters)
        self.assertEqual(200, hs.min_characters)


# __END__
