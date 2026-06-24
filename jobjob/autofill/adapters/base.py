#!/usr/bin/env python3
"""The adapter contract every ATS adapter implements.

An adapter is two things: a cheap ``matches`` test (does this URL look like my ATS?)
and a ``fill`` pass that maps the application data onto the page and returns a
``FillReport``. Playwright is an optional runtime dependency, so the ``Page`` type is
referenced only for type-checking — adapters never import Playwright themselves.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from jobjob.autofill.data import ApplicationData
from jobjob.autofill.report import FillReport

if TYPE_CHECKING:
    from playwright.sync_api import Page


@runtime_checkable
class Adapter(Protocol):
    """An ATS-specific auto-fill adapter."""

    #: Short, stable adapter name used in reports and logs (e.g. "workday").
    name: str

    def matches(self, url: str) -> bool:
        """Return True if this adapter recognizes ``url`` as its ATS."""
        ...

    def fill(self, page: "Page", data: ApplicationData) -> FillReport:
        """Fill the form on ``page`` from ``data`` and return what happened.

        Implementations must never submit the form and must *flag, not invent*:
        anything that cannot be mapped confidently is recorded as a flagged field
        rather than guessed at.
        """
        ...


# __END__
