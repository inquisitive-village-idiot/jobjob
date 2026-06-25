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
        # GET-only mode (use_browser=False): SPA skeleton extracts to nothing → raise.
        jobs_dir = Path(self._tmp())
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url(
                "https://linkedin.com/jobs/view/123",
                jobs_dir,
                use_browser=False,
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
                use_browser=False,
                _fetch_html=lambda url: "<html>…</html>",
                _extract=lambda html: "Apply now",  # under MIN_SNAPSHOT_CHARS
            )

    def test_get_only_fetch_failure_raises_guidance(self) -> None:
        # In GET-only mode a transport failure yields the actionable guidance message.
        def _boom(url: str) -> str:
            raise RuntimeError("connection reset")

        jobs_dir = Path(self._tmp())
        with self.assertRaises(MOD.JDIngestError) as ctx:
            MOD.snapshot_from_url(
                "https://jobs.example.com/x",
                jobs_dir,
                use_browser=False,
                _fetch_html=_boom,
            )
        self.assertIn("PDF", str(ctx.exception))
        self.assertEqual([], list(jobs_dir.iterdir()))

    def test_rejects_non_http_scheme(self) -> None:
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url("ftp://example.com/x", Path(self._tmp()))

    def test_rejects_empty_url(self) -> None:
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url("   ", Path(self._tmp()))

    def test_browser_fallback_used_when_static_is_thin(self) -> None:
        # The cheap GET returns a skeleton; the rendered HTML carries the posting.
        jobs_dir = Path(self._tmp())
        snapshot = MOD.snapshot_from_url(
            "https://acme.myworkdayjobs.com/job/123",
            jobs_dir,
            _fetch_html=lambda url: "SKELETON",
            _fetch_rendered=lambda url, **kw: "RENDERED",
            _extract=lambda html: _ACME_POSTING if html == "RENDERED" else "",
        )
        self.assertTrue(snapshot.is_file())
        self.assertIn("Acme Gazette", snapshot.read_text(encoding="utf-8"))

    def test_browser_not_called_when_static_is_sufficient(self) -> None:
        # A guard: a healthy cheap fetch must short-circuit before the browser.
        def _must_not_render(url: str, **kw: object) -> str:
            raise AssertionError("browser should not be used when static suffices")

        snapshot = MOD.snapshot_from_url(
            "https://jobs.example.com/acme",
            Path(self._tmp()),
            _fetch_html=lambda url: "<html>…</html>",
            _fetch_rendered=_must_not_render,
            _extract=lambda html: _ACME_POSTING,
        )
        self.assertTrue(snapshot.is_file())

    def test_both_paths_thin_raises_and_writes_nothing(self) -> None:
        jobs_dir = Path(self._tmp())
        with self.assertRaises(MOD.JDIngestError):
            MOD.snapshot_from_url(
                "https://acme.myworkdayjobs.com/job/123",
                jobs_dir,
                _fetch_html=lambda url: "SKELETON",
                _fetch_rendered=lambda url, **kw: "STILL_SKELETON",
                _extract=lambda html: "",
            )
        self.assertEqual([], list(jobs_dir.iterdir()))

    def test_browser_unavailable_falls_through_to_guidance(self) -> None:
        # A render error (e.g. Playwright absent) is non-fatal: fall through to the
        # actionable guidance rather than surfacing the raw render error.
        def _no_browser(url: str, **kw: object) -> str:
            raise MOD.JDIngestError("needs the browser extra")

        jobs_dir = Path(self._tmp())
        with self.assertRaises(MOD.JDIngestError) as ctx:
            MOD.snapshot_from_url(
                "https://acme.myworkdayjobs.com/job/123",
                jobs_dir,
                _fetch_html=lambda url: "SKELETON",
                _fetch_rendered=_no_browser,
                _extract=lambda html: "",
            )
        self.assertIn("PDF", str(ctx.exception))
        self.assertEqual([], list(jobs_dir.iterdir()))

    def _tmp(self) -> str:
        import tempfile

        return tempfile.mkdtemp(prefix="jd_source_test_")


class TestSafeUrl(TestCase):
    """URL validation via httpx.URL rather than a regex."""

    def test_accepts_http_and_https(self) -> None:
        for url in ("http://example.com/x", "https://jobs.example.com/acme"):
            with self.subTest(url=url):
                self.assertEqual(url, str(MOD.safe_url(url)))

    def test_strips_surrounding_whitespace(self) -> None:
        self.assertEqual(
            "https://example.com/x", str(MOD.safe_url("  https://example.com/x  "))
        )

    def test_rejects_blank(self) -> None:
        with self.assertRaises(MOD.JDIngestError):
            MOD.safe_url("   ")

    def test_rejects_non_http_scheme(self) -> None:
        with self.assertRaises(MOD.JDIngestError):
            MOD.safe_url("ftp://example.com/x")


class TestEnvDefaults(TestCase):
    """Module thresholds read from the environment with sane fallbacks."""

    def test_env_int_parses_and_falls_back(self) -> None:
        import os

        os.environ["JOBJOB_TEST_INT"] = "150"
        self.addCleanup(os.environ.pop, "JOBJOB_TEST_INT", None)
        self.assertEqual(150, MOD._env_int("JOBJOB_TEST_INT", 200))
        self.assertEqual(200, MOD._env_int("JOBJOB_UNSET_INT", 200))

    def test_env_int_bad_value_falls_back(self) -> None:
        import os

        os.environ["JOBJOB_TEST_INT"] = "not-a-number"
        self.addCleanup(os.environ.pop, "JOBJOB_TEST_INT", None)
        self.assertEqual(200, MOD._env_int("JOBJOB_TEST_INT", 200))

    def test_env_float_parses_and_falls_back(self) -> None:
        import os

        os.environ["JOBJOB_TEST_FLOAT"] = "5.5"
        self.addCleanup(os.environ.pop, "JOBJOB_TEST_FLOAT", None)
        self.assertEqual(5.5, MOD._env_float("JOBJOB_TEST_FLOAT", 20.0))
        self.assertEqual(20.0, MOD._env_float("JOBJOB_UNSET_FLOAT", 20.0))


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
