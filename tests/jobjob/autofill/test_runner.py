#!/usr/bin/env python3
"""Test."""

import contextlib
import io
import logging
import sys
import types
from unittest import TestCase, mock

import jobjob.autofill.runner as MOD
from jobjob.autofill.data import ApplicationData
from jobjob.autofill.report import FillReport

LOGGER = logging.getLogger(__name__)


class FakePage:
    """Minimal Playwright Page stand-in: records the URL it was sent to."""

    def __init__(self) -> None:
        self.url: str | None = None

    def goto(self, url: str) -> None:
        self.url = url


class FakeContext:
    """Minimal persistent-context stand-in: ``pages`` + a ``close()`` flag."""

    def __init__(self, pages=None, close_raises: bool = False) -> None:
        self.pages = list(pages) if pages is not None else []
        self.closed = False
        self._close_raises = close_raises

    def new_page(self) -> FakePage:
        page = FakePage()
        self.pages.append(page)
        return page

    def close(self) -> None:
        if self._close_raises:
            raise RuntimeError("already closed")
        self.closed = True


class FakeChromium:
    def __init__(self, context: FakeContext) -> None:
        self._context = context

    def launch_persistent_context(self, *args, **kwargs):
        return self._context


class FakePlaywright:
    def __init__(self, context: FakeContext) -> None:
        self.chromium = FakeChromium(context)


class _FakeSyncPlaywrightCM:
    def __init__(self, context: FakeContext) -> None:
        self._context = context

    def __enter__(self) -> FakePlaywright:
        return FakePlaywright(self._context)

    def __exit__(self, *exc_info) -> bool:
        return False


def _install_fake_playwright(context: FakeContext):
    """Patch ``sys.modules`` so ``from playwright.sync_api import sync_playwright``
    (imported lazily inside ``run_autofill``) resolves to a fake bound to ``context``.
    """
    fake_module = types.ModuleType("playwright.sync_api")
    fake_module.sync_playwright = lambda: _FakeSyncPlaywrightCM(context)
    return mock.patch.dict(
        sys.modules, {"playwright.sync_api": fake_module, "playwright": mock.Mock()}
    )


class FakeAdapter:
    name = "fake"

    def __init__(self, report: FillReport) -> None:
        self._report = report
        self.filled_page: FakePage | None = None

    def matches(self, url: str) -> bool:
        return True

    def fill(self, page, data: ApplicationData) -> FillReport:
        self.filled_page = page
        return self._report


class ThisTestCase(TestCase):
    """Base test case for the module."""


class TestWaitForWindowClose(ThisTestCase):
    """Test function."""

    def test_returns_immediately_when_no_pages(self) -> None:
        context = FakeContext(pages=[])
        wait = MOD.wait_for_window_close(context)
        with mock.patch("time.sleep") as mock_sleep:
            wait(FillReport(adapter="fake"))
        mock_sleep.assert_not_called()

    def test_polls_until_pages_close(self) -> None:
        context = FakeContext(pages=[FakePage()])

        # First poll sees a page still open; simulate the human closing it.
        def _sleep(_interval):
            context.pages.clear()

        wait = MOD.wait_for_window_close(context, poll_interval=0.01)
        with mock.patch("time.sleep", side_effect=_sleep) as mock_sleep:
            wait(FillReport(adapter="fake"))
        mock_sleep.assert_called_once()

    def test_returns_when_context_already_torn_down(self) -> None:
        class _ExplodingContext:
            @property
            def pages(self):
                raise RuntimeError("context closed")

        wait = MOD.wait_for_window_close(_ExplodingContext())
        with mock.patch("time.sleep") as mock_sleep:
            wait(FillReport(adapter="fake"))
        mock_sleep.assert_not_called()


class TestRunAutofillWaitSelection(ThisTestCase):
    """Test function."""

    def setUp(self) -> None:
        self.report = FillReport(adapter="fake")
        self.adapter = FakeAdapter(self.report)
        self.data = ApplicationData()
        patcher = mock.patch.object(MOD, "select_adapter", return_value=self.adapter)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_tty_stdin_uses_prompt_to_close(self) -> None:
        context = FakeContext()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=True):
                with mock.patch.object(MOD, "_prompt_to_close") as mock_prompt:
                    report = MOD.run_autofill("https://example.test/job", self.data)
        mock_prompt.assert_called_once_with(self.report)
        self.assertIs(self.report, report)
        self.assertTrue(context.closed)

    def test_non_tty_stdin_uses_window_close_wait(self) -> None:
        context = FakeContext()
        fake_wait = mock.Mock()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                with mock.patch.object(
                    MOD, "wait_for_window_close", return_value=fake_wait
                ) as mock_wait_factory:
                    MOD.run_autofill("https://example.test/job", self.data)
        mock_wait_factory.assert_called_once_with(context)
        fake_wait.assert_called_once_with(self.report)
        self.assertTrue(context.closed)

    def test_assisted_detached_true_forces_window_close_on_a_tty(self) -> None:
        context = FakeContext()
        fake_wait = mock.Mock()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=True):
                with mock.patch.object(
                    MOD, "wait_for_window_close", return_value=fake_wait
                ) as mock_wait_factory:
                    MOD.run_autofill(
                        "https://example.test/job",
                        self.data,
                        assisted_detached=True,
                    )
        mock_wait_factory.assert_called_once_with(context)
        fake_wait.assert_called_once_with(self.report)

    def test_assisted_detached_false_forces_prompt_when_not_a_tty(self) -> None:
        context = FakeContext()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                with mock.patch.object(MOD, "_prompt_to_close") as mock_prompt:
                    MOD.run_autofill(
                        "https://example.test/job",
                        self.data,
                        assisted_detached=False,
                    )
        mock_prompt.assert_called_once_with(self.report)

    def test_explicit_wait_for_human_overrides_auto_selection(self) -> None:
        context = FakeContext()
        custom_wait = mock.Mock()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                MOD.run_autofill(
                    "https://example.test/job",
                    self.data,
                    wait_for_human=custom_wait,
                )
        custom_wait.assert_called_once_with(self.report)

    def test_sentinel_printed_on_detached_non_tty_path(self) -> None:
        # The sentinel is printed just before the wait; stub the wait factory so
        # the real page-polling loop doesn't run (run_autofill opens a page, so
        # a real wait_for_window_close would block).
        context = FakeContext()
        buffer = io.StringIO()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                with mock.patch.object(
                    MOD, "wait_for_window_close", return_value=mock.Mock()
                ):
                    with contextlib.redirect_stdout(buffer):
                        MOD.run_autofill("https://example.test/job", self.data)
        self.assertIn(MOD.FILL_COMPLETE_SENTINEL, buffer.getvalue())

    def test_sentinel_printed_when_assisted_detached_forced_on_a_tty(self) -> None:
        context = FakeContext()
        buffer = io.StringIO()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=True):
                with mock.patch.object(
                    MOD, "wait_for_window_close", return_value=mock.Mock()
                ):
                    with contextlib.redirect_stdout(buffer):
                        MOD.run_autofill(
                            "https://example.test/job",
                            self.data,
                            assisted_detached=True,
                        )
        self.assertIn(MOD.FILL_COMPLETE_SENTINEL, buffer.getvalue())

    def test_sentinel_not_printed_on_tty_path(self) -> None:
        context = FakeContext()
        buffer = io.StringIO()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=True):
                with mock.patch.object(MOD, "_prompt_to_close"):
                    with contextlib.redirect_stdout(buffer):
                        MOD.run_autofill("https://example.test/job", self.data)
        output = buffer.getvalue()
        # The report is still printed for the human; the sentinel is not.
        self.assertIn("Auto-fill report", output)
        self.assertNotIn(MOD.FILL_COMPLETE_SENTINEL, output)

    def test_sentinel_not_printed_when_explicit_wait_for_human(self) -> None:
        context = FakeContext()
        buffer = io.StringIO()
        with _install_fake_playwright(context):
            with mock.patch.object(sys.stdin, "isatty", return_value=False):
                with contextlib.redirect_stdout(buffer):
                    MOD.run_autofill(
                        "https://example.test/job",
                        self.data,
                        wait_for_human=mock.Mock(),
                    )
        self.assertNotIn(MOD.FILL_COMPLETE_SENTINEL, buffer.getvalue())

    def test_stdout_flushed_before_wait_is_invoked(self) -> None:
        context = FakeContext()
        calls: list[str] = []

        def _wait(report):
            calls.append("wait")

        with _install_fake_playwright(context):
            with mock.patch.object(
                sys.stdout, "flush", side_effect=lambda: calls.append("flush")
            ):
                MOD.run_autofill(
                    "https://example.test/job", self.data, wait_for_human=_wait
                )
        self.assertEqual(["flush", "wait"], calls)

    def test_context_close_is_idempotent(self) -> None:
        context = FakeContext(close_raises=True)
        with _install_fake_playwright(context):
            # Should not raise even though context.close() blows up.
            MOD.run_autofill(
                "https://example.test/job",
                self.data,
                wait_for_human=lambda report: None,
            )

    def test_no_adapter_raises(self) -> None:
        with mock.patch.object(MOD, "select_adapter", return_value=None):
            with self.assertRaises(MOD.NoAdapterError):
                MOD.run_autofill("https://unsupported.example/job", self.data)


# __END__
