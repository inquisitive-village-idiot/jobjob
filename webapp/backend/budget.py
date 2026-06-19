#!/usr/bin/env python3
"""Cost guard: per-run and daily budget enforcement.

Accumulated spend is persisted to ``~/.cache/jobjob/budget.json`` (one entry per
calendar day). ``check_budget`` is called before launching any job; ``record_run``
is called after a job completes.
"""

import json
from datetime import date
from pathlib import Path
from typing import Optional

_BUDGET_FILE = Path.home() / ".cache" / "jobjob" / "budget.json"

# Per-model cost rates in USD per token.
_MODEL_RATES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {
        "input": 3.0 / 1_000_000,
        "cache_write": 3.75 / 1_000_000,
        "cache_read": 0.30 / 1_000_000,
        "output": 15.0 / 1_000_000,
    },
    "claude-opus-4-8": {
        "input": 5.0 / 1_000_000,
        "cache_write": 6.25 / 1_000_000,
        "cache_read": 0.50 / 1_000_000,
        "output": 25.0 / 1_000_000,
    },
}
_DEFAULT_RATES = _MODEL_RATES["claude-sonnet-4-6"]


def calculate_cost(token_usage: dict, model: str = "claude-sonnet-4-6") -> float:
    """Return the USD cost for ``token_usage`` dict from a job result.

    Arguments:
        token_usage: Dict with input_tokens, output_tokens,
            cache_creation_input_tokens, cache_read_input_tokens.
        model: Claude model id.
    Returns:
        Estimated cost in USD.
    """
    rates = _MODEL_RATES.get(model, _DEFAULT_RATES)
    return (
        token_usage.get("input_tokens", 0) * rates["input"]
        + token_usage.get("cache_creation_input_tokens", 0) * rates["cache_write"]
        + token_usage.get("cache_read_input_tokens", 0) * rates["cache_read"]
        + token_usage.get("output_tokens", 0) * rates["output"]
    )


def _load() -> dict:
    if not _BUDGET_FILE.is_file():
        return {}
    try:
        return json.loads(_BUDGET_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _save(data: dict) -> None:
    _BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
    _BUDGET_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_daily_spent() -> float:
    """Return the accumulated USD spend for today."""
    return _load().get(str(date.today()), {}).get("spent", 0.0)


def record_run(cost: float) -> None:
    """Add ``cost`` to today's accumulated spend.

    Arguments:
        cost: USD cost of the completed run.
    """
    data = _load()
    today = str(date.today())
    data.setdefault(today, {"spent": 0.0})
    data[today]["spent"] += cost
    _save(data)


def check_budget(
    per_run_budget: float = 2.0,
    daily_budget: float = 20.0,
) -> Optional[str]:
    """Return an error message if launching would exceed a budget, else None.

    Arguments:
        per_run_budget: Maximum expected cost per single run (USD).
        daily_budget: Maximum accumulated daily spend (USD).
    Returns:
        A human-readable reason string if blocked, else None.
    """
    spent = get_daily_spent()
    if spent >= daily_budget:
        return (
            f"Daily budget of ${daily_budget:.2f} exceeded "
            f"(${spent:.2f} spent today)."
        )
    remaining = daily_budget - spent
    if per_run_budget > remaining:
        return (
            f"Insufficient daily budget: ${remaining:.2f} remaining, "
            f"${per_run_budget:.2f} estimated for this run."
        )
    return None
