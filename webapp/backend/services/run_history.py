#!/usr/bin/env python3
"""Persist launched jobs as run records with their logs.

Runs are the webapp's executions (build/apply pipeline, enrich, batches,
schedules). Each run gets a JSON record and a ``.log`` file under
``<applications_input_dir>/runs/`` so failures stay inspectable after the
backend restarts — the in-memory job table only covers the current process.

Persistence must never take a job down: every write path degrades to a
warning log.
"""

import json
import logging
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

RUNS_DIRNAME = "runs"
# Retention bound: newest records kept, older ones pruned with their logs.
MAX_RUNS = 200

_LOGGER = logging.getLogger(__name__)


def runs_dir(data_dir: Path) -> Path:
    """Return (and create) the runs directory under the input root."""
    path = Path(data_dir).expanduser() / RUNS_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def record_path(runs: Path, run_id: str) -> Path:
    return Path(runs, f"{run_id}.json")


def log_path(runs: Path, run_id: str) -> Path:
    return Path(runs, f"{run_id}.log")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_record(runs: Path, record: dict, logger: logging.Logger) -> None:
    try:
        record_path(runs, record["run_id"]).write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        logger.warning("Could not persist run %s: %s", record.get("run_id"), exc)


def start_run(
    runs: Path,
    run_id: str,
    *,
    kind: str,
    label: str,
    paths: Iterable[str] = (),
    folder_name: Optional[str] = None,
    logger: logging.Logger | None = None,
) -> dict:
    """Record a newly launched run (status ``running``) and prune old ones.

    Arguments:
        runs: The runs directory (see ``runs_dir``).
        run_id: The job id (shared with the in-memory job table).
        kind: Machine kind — apply / enrich / batch / schedule. (UI copy says
            "Build"; the stored vocabulary keeps the API names.)
        label: Human-readable run label.
        paths: Input paths the run covers.
        folder_name: Target application folder when known (re-runs).
        logger: Optional logger for injection.
    Returns:
        The persisted record dict.
    """
    _logger = logger or _LOGGER
    record = {
        "run_id": run_id,
        "kind": kind,
        "label": label,
        "paths": [str(p) for p in paths],
        "folder_name": folder_name,
        "status": "running",
        "error": None,
        "started_at": _now(),
        "finished_at": None,
    }
    _write_record(runs, record, _logger)
    prune(runs, logger=_logger)
    return record


def finish_run(
    runs: Path,
    run_id: str,
    *,
    status: str,
    error: Optional[str] = None,
    logger: logging.Logger | None = None,
) -> None:
    """Mark a run finished (``completed`` / ``failed``) with its error, if any."""
    _logger = logger or _LOGGER
    record = _read_record(runs, run_id, _logger) or {"run_id": run_id}
    record.update(status=status, error=error, finished_at=_now())
    _write_record(runs, record, _logger)


def _read_record(runs: Path, run_id: str, logger: logging.Logger) -> Optional[dict]:
    path = record_path(runs, run_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Unreadable run record %s: %s", path, exc)
        return None


def read_log(runs: Path, run_id: str) -> Optional[str]:
    """Return a run's stored log text, or None when absent/unreadable."""
    path = log_path(runs, run_id)
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else None
    except OSError as exc:
        _LOGGER.warning("Unreadable run log %s: %s", path, exc)
        return None


def list_runs(runs: Path, live: Mapping[str, Mapping[str, Any]]) -> list[dict]:
    """Merged run history, newest first.

    Persisted records are the base; a live in-memory job overrides its
    record's status/error. A persisted record still marked ``running`` with no
    live counterpart belongs to a dead process and is reported as ``failed``
    (interrupted) — the exact case persistence exists for.
    """
    records: dict[str, dict] = {}
    for path in runs.glob("*.json"):
        record = _read_record(runs, path.stem, _LOGGER)
        if record and record.get("run_id"):
            records[record["run_id"]] = record

    items = []
    for run_id, record in records.items():
        entry = dict(record)
        job = live.get(run_id)
        if job is not None:
            entry["status"] = job.get("status", entry.get("status"))
            entry["error"] = job.get("error") or entry.get("error")
        elif entry.get("status") == "running":
            entry["status"] = "failed"
            entry["error"] = entry.get("error") or (
                "Interrupted — the backend restarted while this run was active."
            )
        entry["has_log"] = log_path(runs, run_id).is_file()
        items.append(entry)
    return sorted(items, key=lambda e: e.get("started_at") or "", reverse=True)


def prune(runs: Path, *, keep: int = MAX_RUNS, logger: logging.Logger | None = None):
    """Delete the oldest records (and their logs) beyond ``keep``."""
    _logger = logger or _LOGGER
    by_started = sorted(
        runs.glob("*.json"),
        key=lambda p: (_read_record(runs, p.stem, _LOGGER) or {}).get("started_at")
        or "",
    )
    for path in by_started[: max(0, len(by_started) - keep)]:
        try:
            log_path(runs, path.stem).unlink(missing_ok=True)
            path.unlink(missing_ok=True)
        except OSError as exc:
            _logger.warning("Could not prune run %s: %s", path.stem, exc)


# __END__
