#!/usr/bin/env python3
"""Browser e2e for the headless JD render path (fetch_rendered_html).

Renders a local JS-injected posting fixture and asserts the rendered HTML carries
text a plain read would miss. Marked ``e2e`` so the default suite skips it; run with
``pytest -m e2e``. No live site is contacted.
"""

from pathlib import Path

import pytest

import jobjob.ingest.jd_source as MOD

# Skip the whole module (and avoid a collection-time ImportError) when the optional
# Playwright extra is not installed.
pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e

_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "jd_js_rendered.html"


def test_rendered_html_includes_js_injected_posting():
    # A plain read of the fixture sees only the empty skeleton; rendering it runs the
    # injected script, so the posting text appears in the extracted main text.
    skeleton_text = MOD.extract_main_text(_FIXTURE.read_text(encoding="utf-8"))
    assert "science correspondent" not in skeleton_text

    html = MOD.fetch_rendered_html(_FIXTURE.as_uri())
    text = MOD.extract_main_text(html)
    assert "Acme Gazette" in text
    assert "science correspondent" in text


# __END__
