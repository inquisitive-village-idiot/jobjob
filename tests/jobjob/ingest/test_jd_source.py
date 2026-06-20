#!/usr/bin/env python3
"""Tests for URL/paste job-posting ingestion into a snapshot.

No network: the HTTP fetch and the extraction are injected. Examples use Tila Mer /
Acme so no PII appears.
"""

from pathlib import Path
from unittest import TestCase

import jobjob.ingest.jd_source as MOD

_ACME_POSTING = (
    "Science Correspondent — Acme Gazette\n\n"
    "Acme Gazette seeks a science correspondent to cover print science and the "
    "history of typography. You will report on Gutenberg-era printing, fact-check "
    "claims against primary sources, and file 800-word features on deadline. "
    "Requirements: five years of newsroom experience, a nose for accuracy, and the "
    "ability to translate dense research into lively prose for a general audience."
)

_SKELETON_HTML = "<html><body><div id='app'></div></body></html>"


class TestSnapshotFromUrl(TestCase):
    """URL fetch → extract → snapshot."""

    def test_writes_snapshot_from_extracted_text(self) -> None:
        jobs_dir = Path(self._tmp())
        snapshot = MOD.snapshot_from_url(
            "https://jobs.example.com/acme/science-correspondent",
            jobs_dir,
            _fetch_html=lambda url: "<html>…</html>",
            _extract=lambda html: _ACME_POSTING,
        )

        with self.subTest("file written under jobs_dir as markdown"):
            self.assertTrue(snapshot.is_file())
            self.assertEqual(jobs_dir, snapshot.parent)
            self.assertEqual(".md", snapshot.suffix)
        content = snapshot.read_text(encoding="utf-8")
        with self.subTest("posting text preserved"):
            self.assertIn("Acme Gazette", content)
            self.assertIn("science correspondent", content)
        with self.subTest("provenance recorded"):
            self.assertIn("<!-- source: https://jobs.example.com", content)

    def test_empty_skeleton_raises_and_writes_nothing(self) -> None:
        jobs_dir = Path(self._tmp())
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url(
                "https://linkedin.com/jobs/view/123",
                jobs_dir,
                _fetch_html=lambda url: _SKELETON_HTML,
                _extract=lambda html: "",  # SPA skeleton → no text
            )
        self.assertEqual([], list(jobs_dir.iterdir()))

    def test_short_extraction_below_threshold_raises(self) -> None:
        jobs_dir = Path(self._tmp())
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url(
                "https://jobs.example.com/x",
                jobs_dir,
                _fetch_html=lambda url: "<html>…</html>",
                _extract=lambda html: "Apply now",  # under MIN_SNAPSHOT_CHARS
            )

    def test_fetch_failure_raises_clean_error(self) -> None:
        def _boom(url: str) -> str:
            raise RuntimeError("connection reset")

        with self.assertRaises(MOD.JDIngestError) as ctx:
            MOD.snapshot_from_url(
                "https://jobs.example.com/x",
                Path(self._tmp()),
                _fetch_html=_boom,
            )
        self.assertIn("connection reset", str(ctx.exception))

    def test_rejects_non_http_scheme(self) -> None:
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url("ftp://example.com/x", Path(self._tmp()))

    def test_rejects_empty_url(self) -> None:
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url("   ", Path(self._tmp()))

    def _tmp(self) -> str:
        import tempfile

        return tempfile.mkdtemp(prefix="jd_source_test_")


class TestSnapshotFromText(TestCase):
    """Pasted text → snapshot."""

    def test_writes_snapshot_from_paste(self) -> None:
        import tempfile

        jobs_dir = Path(tempfile.mkdtemp(prefix="jd_source_test_"))
        snapshot = MOD.snapshot_from_text(_ACME_POSTING, jobs_dir)
        self.assertTrue(snapshot.is_file())
        self.assertIn("Acme Gazette", snapshot.read_text(encoding="utf-8"))

    def test_too_short_paste_raises(self) -> None:
        import tempfile

        jobs_dir = Path(tempfile.mkdtemp(prefix="jd_source_test_"))
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_text("too short", jobs_dir)
        self.assertEqual([], list(jobs_dir.iterdir()))


# __END__
