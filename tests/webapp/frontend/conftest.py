#!/usr/bin/env python3
"""End-to-end browser-test harness for the built frontend.

These tests drive the real React UI in a headless browser against a live instance of
the app. The app is launched once per session (``jobjob-app`` serving the Vite ``dist``
from a scaffolded temp working dir); each test gets a fresh browser.

Everything under this directory is auto-marked ``e2e`` (see the collection hook), so the
default ``pytest`` run skips it — it runs only in the dedicated CI job or via
``pytest -m e2e``. Requires Chrome (Selenium Manager fetches the driver) and a built
``webapp/frontend/dist``; a missing browser/launcher skips rather than errors.
"""

import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FRONTEND_DIST = _REPO_ROOT / "webapp" / "frontend" / "dist"
_HEALTH_TIMEOUT = 45  # seconds to wait for the server to answer /api/health


def pytest_collection_modifyitems(items):
    """Mark every test in this package ``e2e`` so the default run skips them."""
    here = Path(__file__).parent
    for item in items:
        if here in Path(item.fspath).parents:
            item.add_marker(pytest.mark.e2e)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_for_health(base_url: str, timeout: float = _HEALTH_TIMEOUT) -> bool:
    """Poll ``/api/health`` until it answers 200 or the timeout elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    return True
        except OSError:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def live_app(tmp_path_factory) -> str:
    """Launch the app on a free port and yield its base URL.

    Scaffolds an isolated working dir, then serves the built frontend. Skips the e2e
    suite when the launcher or the built ``dist`` is unavailable.
    """
    if shutil.which("jobjob-app") is None:
        pytest.skip("jobjob-app launcher not on PATH")
    if not _FRONTEND_DIST.is_dir():
        pytest.skip("frontend not built (run: cd webapp/frontend && npm run build)")

    home = tmp_path_factory.mktemp("jj_e2e_home")
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    # Scaffold config/data first (mirrors the CI smoke test), then serve.
    subprocess.run(
        ["jobjob-app", "--dir", str(home), "--setup-only"],
        check=True,
        capture_output=True,
        text=True,
    )
    # Pre-dismiss the first-run setup wizard (a ``.setup_dismissed`` marker beside the
    # app config) so tests drive the real UI instead of the auto-opening modal.
    config_dir = home / "config"
    config_dir.mkdir(exist_ok=True)
    (config_dir / ".setup_dismissed").write_text("", encoding="utf-8")
    proc = subprocess.Popen(
        [
            "jobjob-app",
            "--dir",
            str(home),
            "--no-browser",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        # New session so we can signal the whole process group on teardown.
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not _wait_for_health(base_url):
            raise RuntimeError(f"app did not become healthy at {base_url}")
        yield base_url
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            proc.kill()


@pytest.fixture
def driver(live_app):
    """Yield a fresh headless-Chrome WebDriver (skips if Chrome is unavailable)."""
    pytest.importorskip("selenium")
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver import Chrome, ChromeOptions

    options = ChromeOptions()
    for arg in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage"):
        options.add_argument(arg)
    options.add_argument("--window-size=1280,900")

    try:
        drv = Chrome(options=options)
    except WebDriverException as exc:  # no browser/driver on this host
        pytest.skip(f"Chrome WebDriver unavailable: {exc}")
    drv.implicitly_wait(5)  # auto-wait for elements as the SPA mounts
    try:
        yield drv
    finally:
        drv.quit()
