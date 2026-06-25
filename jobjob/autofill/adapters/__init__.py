#!/usr/bin/env python3
"""ATS-specific auto-fill adapters and the registry that selects one for a URL."""

from collections.abc import Sequence

from jobjob.autofill.adapters.ashby import AshbyAdapter
from jobjob.autofill.adapters.base import Adapter
from jobjob.autofill.adapters.generic import GenericAdapter
from jobjob.autofill.adapters.greenhouse import GreenhouseAdapter
from jobjob.autofill.adapters.lever import LeverAdapter
from jobjob.autofill.adapters.smartrecruiters import SmartRecruitersAdapter
from jobjob.autofill.adapters.workable import WorkableAdapter
from jobjob.autofill.adapters.workday import WorkdayAdapter

# Ordered registry: the first adapter whose ``matches`` returns True wins. The generic
# fallback matches any URL, so it MUST stay LAST — every named adapter takes priority.
ADAPTERS: tuple[Adapter, ...] = (
    WorkdayAdapter(),
    GreenhouseAdapter(),
    LeverAdapter(),
    AshbyAdapter(),
    WorkableAdapter(),
    SmartRecruitersAdapter(),
    GenericAdapter(),
)


def select_adapter(
    url: str,
    adapters: Sequence[Adapter] = ADAPTERS,
) -> Adapter | None:
    """Return the first adapter that recognizes ``url``, or None if none match."""
    for adapter in adapters:
        if adapter.matches(url):
            return adapter
    return None


# __END__
