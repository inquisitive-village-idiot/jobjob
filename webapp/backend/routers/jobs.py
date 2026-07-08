#!/usr/bin/env python3
"""Jobs API: launch build/enrich jobs with SSE progress streaming.

Runs each job in a background thread and streams log records as SSE events.
The cost guard is checked before launch; successful runs are moved to the
appropriate completed subdirectory and their cost recorded.
"""

import asyncio
import json
import logging
import queue
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from budget import calculate_cost, check_budget, record_run
from jobjob.ingest.jd_source import (
    JDIngestError,
    snapshot_from_text,
    snapshot_from_url,
)
from security import safe_path
from services import run_history
from services.application_metadata import read_entity_id
from services.tracking_service import list_queue

router = APIRouter()

_jobs: dict[str, dict] = {}


class _OverwriteConflictJob(Exception):
    """Apply failed because the target folder exists (overwrite not allowed)."""

    def __init__(self, folder_name: str, message: str) -> None:
        self.folder_name = folder_name
        super().__init__(message)


def _run_inputs_over(process, paths, **kwargs) -> dict:
    """Run a ``*_inputs`` entry point over each existing path and merge summaries.

    Lets a batch process inputs from ``data/`` (the canonical drop location) plus
    the legacy ``data/jobs`` or ``data/profiles`` subdir without double-counting
    (``*_inputs`` only scans a directory's top-level files).
    """
    merged: dict = {"processed": 0, "skipped": 0, "failed": 0, "items": []}
    for path in paths:
        if not path.is_dir():
            continue
        summary = process(path, **kwargs)
        for key in ("processed", "skipped", "failed"):
            merged[key] += summary.get(key, 0)
        merged["items"].extend(summary.get("items", []))
    return merged


class _QueueHandler(logging.Handler):
    def __init__(self, q: queue.Queue) -> None:
        super().__init__()
        self.q = q

    def emit(self, record: logging.LogRecord) -> None:
        self.q.put_nowait(
            {
                "level": record.levelname,
                "message": self.format(record),
                "ts": record.created,
            }
        )


class ApplyRequest(BaseModel):
    jd_path: str
    skip_drive: bool = False
    template: Optional[str] = None
    no_cache: bool = False
    clear_cache: bool = False
    allow_overwrite: bool = False


class UrlApplyRequest(BaseModel):
    url: str
    skip_drive: bool = False
    template: Optional[str] = None
    no_cache: bool = False
    clear_cache: bool = False
    allow_overwrite: bool = False


class TextApplyRequest(BaseModel):
    text: str
    skip_drive: bool = False
    template: Optional[str] = None
    no_cache: bool = False
    clear_cache: bool = False
    allow_overwrite: bool = False


class RerunRequest(BaseModel):
    folder_name: str
    skip_drive: bool = False
    model: Optional[str] = None  # per-run override; not persisted to config/.env
    entity_id: Optional[str] = None  # prefer id resolution when the caller has one


class EnrichRequest(BaseModel):
    profile_path: str
    dry_run: bool = False


class ScheduleRequest(BaseModel):
    mode: Literal["sync", "async"] = "sync"
    concurrency: int = 1
    interval_minutes: int = 0
    start_at: str  # ISO datetime string
    paths: list[str]


def _app_settings(request: Request) -> dict:
    return request.app.state.settings


def _runs_dir(settings: dict) -> Path:
    return run_history.runs_dir(Path(settings["applications_input_dir"]))


def _start_job(
    fn,
    *,
    runs_dir: Optional[Path] = None,
    kind: str = "build",
    label: str = "",
    paths: tuple[str, ...] = (),
    folder_name: Optional[str] = None,
) -> str:
    """Run ``fn`` in a background thread with SSE logs and a persisted run.

    The run record + log file land under ``runs_dir`` (see
    ``services.run_history``) so failures survive restarts; ``runs_dir=None``
    keeps the job in-memory only (tests). Persistence problems never fail the
    job.
    """
    job_id = str(uuid.uuid4())
    log_q: queue.Queue = queue.Queue()
    _jobs[job_id] = {
        "status": "running",
        "log_queue": log_q,
        "result": None,
        "error": None,
        "overwrite_conflict": False,
        "folder_name": None,
    }
    if runs_dir is not None:
        run_history.start_run(
            runs_dir,
            job_id,
            kind=kind,
            label=label,
            paths=paths,
            folder_name=folder_name,
        )

    def run() -> None:
        formatter = logging.Formatter("%(name)s: %(message)s")
        handler = _QueueHandler(log_q)
        handler.setFormatter(formatter)
        root = logging.getLogger("jobjob")
        root.addHandler(handler)
        # Tee the same records into the run's log file (persisted history).
        file_handler: Optional[logging.Handler] = None
        if runs_dir is not None:
            try:
                file_handler = logging.FileHandler(
                    run_history.log_path(runs_dir, job_id), encoding="utf-8"
                )
                file_handler.setFormatter(formatter)
                root.addHandler(file_handler)
            except OSError as exc:
                logging.getLogger(__name__).warning(
                    "Run log unavailable for %s: %s", job_id, exc
                )
        try:
            result = fn()
            _jobs[job_id]["result"] = result
            _jobs[job_id]["status"] = "completed"
        except _OverwriteConflictJob as exc:
            _jobs[job_id]["error"] = str(exc)
            _jobs[job_id]["overwrite_conflict"] = True
            _jobs[job_id]["folder_name"] = exc.folder_name
            _jobs[job_id]["status"] = "failed"
        except Exception as exc:
            _jobs[job_id]["error"] = str(exc)
            _jobs[job_id]["status"] = "failed"
        finally:
            root.removeHandler(handler)
            if file_handler is not None:
                root.removeHandler(file_handler)
                file_handler.close()
            if runs_dir is not None:
                # entity_id (application-identity, phase 1): the workflow stamps it
                # onto the result dict once the build/enrich mints or reuses it, so
                # it's only ever present here on a real (build/enrich) completion —
                # batch/schedule results and failures naturally omit it (legacy).
                completed_result = _jobs[job_id].get("result")
                entity_id = (
                    completed_result.get("entity_id")
                    if isinstance(completed_result, dict)
                    else None
                )
                run_history.finish_run(
                    runs_dir,
                    job_id,
                    status=_jobs[job_id]["status"],
                    error=_jobs[job_id]["error"],
                    entity_id=entity_id,
                )
            log_q.put(None)

    threading.Thread(target=run, daemon=True).start()
    return job_id


# ── Single-item endpoints ──────────────────────────────────────────────────────


def _make_build_run(
    jd_path: Path,
    *,
    skip_drive: bool,
    move_data_dir: Optional[Path],
    template: Optional[str] = None,
    no_cache: bool = False,
    clear_cache: bool = False,
    allow_overwrite: bool = False,
    model: Optional[str] = None,
):
    """Build the background ``_run`` closure for a build job.

    Routes through ``apply_inputs`` (the shared CLI entry point), using the current
    configuration (``load_settings`` → model, applicant, credentials). ``move_data_dir``
    is passed straight through as ``apply_inputs``'s ``data_dir``: a real path moves
    the JD into ``<data_dir>/completed/`` on success (normal build); ``None`` skips
    the move, which is what a re-run wants since its JD already lives in
    ``completed/jobs/``.

    ``model`` is an optional per-run override (not persisted): it replaces the
    configured model for this run only. The response cache key is model-scoped, so
    the override is cached under its own entry rather than colliding with -- or
    being forced to bypass -- the configured model's cache.
    """

    def _run() -> dict:
        from jobjob.ailib.client.anthropic import AnthropicAdapter
        from jobjob.ailib.query import clear_cache as _clear_cache
        from jobjob.ailib.session import AIClient
        from jobjob.apply.workflow import apply_inputs
        from jobjob.cli import build_credentials_loader
        from jobjob.config import load_settings

        settings = load_settings()
        if clear_cache:
            _clear_cache()

        effective_model = model or settings.model
        use_cache = settings.cache_enabled and not no_cache

        client = AIClient(
            AnthropicAdapter(model=effective_model, api_key=settings.anthropic_api_key)
        )
        # We re-raise on failure to keep job-failure semantics.
        summary = apply_inputs(
            jd_path,
            query_service=client,
            applicant=settings.applicant,
            skip_drive=skip_drive,
            use_cache=use_cache,
            template_name=template,
            parent_id=settings.applications_output_drive_id,
            data_dir=move_data_dir,
            allow_overwrite=allow_overwrite,
            industry=settings.industry,
            logger=logging.getLogger("jobjob.apply"),
            _credentials_loader=build_credentials_loader(settings),
        )
        item = summary["items"][0]
        if item["status"] == "error":
            if item.get("overwrite_conflict"):
                # Surface as a typed conflict so the job state can offer an override.
                raise _OverwriteConflictJob(item.get("folder_name", ""), item["error"])
            raise RuntimeError(item["error"])
        result = item["result"]
        # Surface the model actually used so the job summary can show it.
        if isinstance(result, dict):
            result.setdefault("model", effective_model)
        if "token_usage" in result:
            record_run(calculate_cost(result["token_usage"], model=effective_model))
        return result

    return _run


@router.post("/build")
def launch_build(body: ApplyRequest, request: Request) -> dict:
    """Start a build job for one JD. Returns {job_id}."""
    s = _app_settings(request)

    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 2.0),
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    jd_path = safe_path(body.jd_path)
    if not jd_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {jd_path}")

    run = _make_build_run(
        jd_path,
        skip_drive=body.skip_drive,
        move_data_dir=Path(s["applications_input_dir"]),
        template=body.template,
        no_cache=body.no_cache,
        clear_cache=body.clear_cache,
        allow_overwrite=body.allow_overwrite,
    )
    job_id = _start_job(
        run,
        runs_dir=_runs_dir(s),
        kind="build",
        label=jd_path.name,
        paths=(str(jd_path),),
    )
    return {"job_id": job_id}


def _launch_snapshot_build(
    snapshot: Path,
    *,
    settings: dict,
    skip_drive: bool,
    template: Optional[str],
    no_cache: bool,
    clear_cache: bool,
    allow_overwrite: bool,
) -> dict:
    """Feed a freshly-written snapshot into the shared build pipeline.

    Mirrors :func:`launch_build`: the snapshot is just another JD input under
    ``data/jobs/``, so it flows through ``apply_inputs`` unchanged and is moved into
    ``completed/`` on success.
    """
    run = _make_build_run(
        snapshot,
        skip_drive=skip_drive,
        move_data_dir=Path(settings["applications_input_dir"]),
        template=template,
        no_cache=no_cache,
        clear_cache=clear_cache,
        allow_overwrite=allow_overwrite,
    )
    job_id = _start_job(
        run,
        runs_dir=_runs_dir(settings),
        kind="build",
        label=snapshot.name,
        paths=(str(snapshot),),
    )
    return {"job_id": job_id, "snapshot": str(snapshot)}


@router.post("/build/from-url")
def launch_build_from_url(body: UrlApplyRequest, request: Request) -> dict:
    """Capture a job posting from a URL, then build. Returns {job_id, snapshot}.

    A server-side GET + readability extraction writes a durable snapshot into
    ``data/jobs/``; when the cheap fetch is thin (a JS-rendered board) and the
    browser extra is installed, it falls back to a headless render before
    extracting. The snapshot then runs through the normal build pipeline. Only when
    both paths come up short is it rejected with a 422 so the user can fall back to
    PDF upload or paste-text.
    """
    s = _app_settings(request)

    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 2.0),
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    jobs_dir = Path(s["applications_input_dir"]) / "jobs"
    try:
        snapshot = snapshot_from_url(body.url, jobs_dir)
    except JDIngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return _launch_snapshot_build(
        snapshot,
        settings=s,
        skip_drive=body.skip_drive,
        template=body.template,
        no_cache=body.no_cache,
        clear_cache=body.clear_cache,
        allow_overwrite=body.allow_overwrite,
    )


@router.post("/build/from-text")
def launch_build_from_text(body: TextApplyRequest, request: Request) -> dict:
    """Capture a job posting from pasted text, then build. Returns {job_id, snapshot}.

    The reliable fallback for boards a plain GET can't read: the pasted text is
    snapshotted into ``data/jobs/`` and runs through the normal build pipeline.
    """
    s = _app_settings(request)

    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 2.0),
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    jobs_dir = Path(s["applications_input_dir"]) / "jobs"
    try:
        snapshot = snapshot_from_text(body.text, jobs_dir)
    except JDIngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return _launch_snapshot_build(
        snapshot,
        settings=s,
        skip_drive=body.skip_drive,
        template=body.template,
        no_cache=body.no_cache,
        clear_cache=body.clear_cache,
        allow_overwrite=body.allow_overwrite,
    )


# The JD copy inside a Drive application folder is named JD_<Company>_<Role> (current)
# or JobDescription_<Company>_<Role> (older applications) — match both so re-run can
# find the source JD regardless of when the application was generated.
_JD_GLOBS = ("JD_*.pdf", "JobDescription_*.pdf")


def _resolve_folder_name_by_entity_id(
    applications_local_dir: Optional[str], entity_id: str
) -> Optional[str]:
    """Return the current folder name carrying ``entity_id``, if found.

    Scans the synced Drive applications mirror's metadata.json files — the
    entity tier survives a folder rename, so this is how a rerun request keyed
    by id (rather than a possibly-stale folder name) finds its target.
    """
    if not applications_local_dir:
        return None
    local = Path(applications_local_dir).expanduser()
    if not local.is_dir():
        return None
    for folder in local.iterdir():
        if not folder.is_dir():
            continue
        try:
            if read_entity_id(folder) == entity_id:
                return folder.name
        except (ValueError, OSError):
            continue
    return None


def _find_rerun_jd(
    data_dir: Path,
    applications_local_dir: Optional[str],
    folder_name: str,
    *,
    entity_id: Optional[str] = None,
) -> Optional[Path]:
    """Resolve a completed application's source JD for re-running.

    When ``entity_id`` is given, the target application folder is resolved by id
    first (survives a rename since the last run) — see
    ``_resolve_folder_name_by_entity_id``; if no folder carries that id (or none
    was given — the legacy path), falls back to ``folder_name`` unchanged.

    Looks first in ``<data_dir>/completed/jobs/<folder_name><ext>`` (where a webapp/CLI
    completion files the JD), then in the synced Drive application folder
    ``<applications_local_dir>/<folder_name>/`` (most completed applications only have
    their JD here). Returns the path, or None when neither location has it.
    """
    resolved_name = folder_name
    if entity_id:
        by_id = _resolve_folder_name_by_entity_id(applications_local_dir, entity_id)
        if by_id:
            resolved_name = by_id

    jobs_dir = Path(data_dir) / "completed" / "jobs"
    for ext in (".pdf", ".png", ".jpg", ".jpeg", ".md", ".txt"):
        candidate = jobs_dir / f"{resolved_name}{ext}"
        if candidate.is_file():
            return candidate

    if applications_local_dir:
        app_folder = Path(applications_local_dir).expanduser() / resolved_name
        if app_folder.is_dir():
            matches = sorted(
                m for pattern in _JD_GLOBS for m in app_folder.glob(pattern)
            )
            if matches:
                return matches[0]
    return None


@router.post("/build/rerun")
def launch_build_rerun(body: RerunRequest, request: Request) -> dict:
    """Re-run build for a completed application, reusing its JD in place.

    The JD is resolved from ``folder_name`` in one of two places, then re-run with
    ``move_data_dir=None`` so it is *not* moved — it stays put. Current config and
    default options are used.

      1. ``<data_dir>/completed/jobs/<folder_name><ext>`` — where a webapp/CLI
         completion moves the JD (named after the Drive application folder).
      2. ``<applications_local_dir>/<folder_name>/JD_*.pdf`` — the JD inside the
         synced Drive application folder. Most completed applications only have
         their JD here (the move-to-completed step never ran for them).
    """
    s = _app_settings(request)

    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 2.0),
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    found = _find_rerun_jd(
        Path(s["applications_input_dir"]),
        s.get("applications_output_dir"),
        body.folder_name,
        entity_id=body.entity_id,
    )
    jd_path = safe_path(found) if found is not None else None

    if jd_path is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No source JD found for '{body.folder_name}' in completed/jobs/ "
                "or the synced Drive application folder."
            ),
        )

    run = _make_build_run(
        jd_path, skip_drive=body.skip_drive, move_data_dir=None, model=body.model
    )
    job_id = _start_job(
        run,
        runs_dir=_runs_dir(s),
        kind="build",
        label=f"Re-build: {body.folder_name}",
        paths=(str(jd_path),),
        folder_name=body.folder_name,
    )
    return {"job_id": job_id}


@router.post("/enrich")
def launch_enrich(body: EnrichRequest, request: Request) -> dict:
    """Start an enrich job for one profile. Returns {job_id}."""
    s = _app_settings(request)

    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 0.50),
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    profile_path = safe_path(body.profile_path)
    if not profile_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {profile_path}")

    data_dir = Path(s["applications_input_dir"])

    def _run() -> dict:
        from jobjob.ailib.client.anthropic import AnthropicAdapter
        from jobjob.ailib.session import AIClient
        from jobjob.cli import build_credentials_loader
        from jobjob.config import load_settings
        from jobjob.enrich.workflow import enrich_inputs

        settings = load_settings()
        client = AIClient(
            AnthropicAdapter(model=settings.model, api_key=settings.anthropic_api_key)
        )
        # Route through the shared entry point (same one the CLI uses). It processes
        # the file and, on a real completion, moves the profile into
        # data_dir/completed/ — identical to the CLI. We re-raise on failure to keep
        # job-failure semantics and return the workflow result.
        summary = enrich_inputs(
            profile_path,
            query_service=client,
            spreadsheet_id=settings.enrichment_output_sheet_id,
            dry_run=body.dry_run,
            data_dir=data_dir,
            logger=logging.getLogger("jobjob.enrich"),
            _credentials_loader=build_credentials_loader(settings),
        )
        item = summary["items"][0]
        if item["status"] == "error":
            raise RuntimeError(item["error"])
        result = item["result"]
        if "token_usage" in result:
            cost = calculate_cost(result["token_usage"], model=settings.model)
            record_run(cost)
        return result

    job_id = _start_job(
        _run,
        runs_dir=_runs_dir(s),
        kind="enrich",
        label=profile_path.name,
        paths=(str(profile_path),),
    )
    return {"job_id": job_id}


# ── Batch endpoints ────────────────────────────────────────────────────────────


@router.post("/build-all")
def launch_build_all(request: Request) -> dict:
    """Start build jobs for every JD in the queue, sequentially (returns
    ``{job_id, count}``)."""
    s = _app_settings(request)
    data_dir = Path(s["applications_input_dir"])
    items = [i for i in list_queue(data_dir) if i["subfolder"] == "jobs"]

    if not items:
        raise HTTPException(status_code=400, detail="No JDs in queue")

    count = len(items)
    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 2.0) * count,
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    def _run_all() -> dict:
        from jobjob.ailib.client.anthropic import AnthropicAdapter
        from jobjob.ailib.session import AIClient
        from jobjob.apply.workflow import apply_inputs
        from jobjob.cli import build_credentials_loader
        from jobjob.config import load_settings

        settings = load_settings()
        _logger = logging.getLogger("jobjob.apply")
        client = AIClient(
            AnthropicAdapter(model=settings.model, api_key=settings.anthropic_api_key)
        )
        # Shared entry point (same as the CLI): classifies + processes JDs from
        # data/ (and the legacy data/jobs), moving each into completed/.
        summary = _run_inputs_over(
            apply_inputs,
            (data_dir, data_dir / "jobs"),
            query_service=client,
            applicant=settings.applicant,
            skip_drive=False,
            use_cache=settings.cache_enabled,
            parent_id=settings.applications_output_drive_id,
            data_dir=data_dir,
            industry=settings.industry,
            logger=_logger,
            _credentials_loader=build_credentials_loader(settings),
        )
        # Record cost per completed application (webapp-only budget tracking).
        for entry in summary["items"]:
            result = entry.get("result")
            if isinstance(result, dict) and "token_usage" in result:
                record_run(calculate_cost(result["token_usage"], model=settings.model))
        return summary

    job_id = _start_job(
        _run_all,
        runs_dir=_runs_dir(s),
        kind="batch",
        label=f"Build all JDs ({count})",
        paths=tuple(i["path"] for i in items),
    )
    return {"job_id": job_id, "count": count}


@router.post("/enrich-all")
def launch_enrich_all(request: Request) -> dict:
    """Start enrich jobs for every profile in the queue, sequentially (returns
    ``{job_id, count}``)."""
    s = _app_settings(request)
    data_dir = Path(s["applications_input_dir"])
    items = [i for i in list_queue(data_dir) if i["subfolder"] == "profiles"]

    if not items:
        raise HTTPException(status_code=400, detail="No profiles in queue")

    count = len(items)
    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 0.50) * count,
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    def _run_all() -> dict:
        from jobjob.ailib.client.anthropic import AnthropicAdapter
        from jobjob.ailib.session import AIClient
        from jobjob.cli import build_credentials_loader
        from jobjob.config import load_settings
        from jobjob.enrich.workflow import enrich_inputs

        settings = load_settings()
        _logger = logging.getLogger("jobjob.enrich")
        client = AIClient(
            AnthropicAdapter(model=settings.model, api_key=settings.anthropic_api_key)
        )
        # Shared entry point (same as the CLI): classifies + enriches profiles from
        # data/ (and the legacy data/profiles), moving each into completed/.
        summary = _run_inputs_over(
            enrich_inputs,
            (data_dir, data_dir / "profiles"),
            query_service=client,
            spreadsheet_id=settings.enrichment_output_sheet_id,
            data_dir=data_dir,
            logger=_logger,
            _credentials_loader=build_credentials_loader(settings),
        )
        # Record cost per completed profile (webapp-only budget tracking).
        for entry in summary["items"]:
            result = entry.get("result")
            if isinstance(result, dict) and "token_usage" in result:
                record_run(calculate_cost(result["token_usage"], model=settings.model))
        return summary

    job_id = _start_job(
        _run_all,
        runs_dir=_runs_dir(s),
        kind="batch",
        label=f"Enrich all profiles ({count})",
        paths=tuple(i["path"] for i in items),
    )
    return {"job_id": job_id, "count": count}


# ── Schedule endpoint ──────────────────────────────────────────────────────────


@router.post("/schedule")
def launch_schedule(body: ScheduleRequest, request: Request) -> dict:
    """Schedule selected files with given mode, concurrency, interval, and start time.

    Returns {job_id, count}.  Schedule metadata is stored in
    ``_jobs[job_id]["schedule"]``
    so ``GET /scheduled`` can surface it for the Queue page.
    """
    s = _app_settings(request)
    data_dir = Path(s["applications_input_dir"])

    valid_paths: list[Path] = []
    for raw in body.paths:
        try:
            p = safe_path(raw)
            if p.is_file():
                valid_paths.append(p)
        except Exception:
            pass

    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid files in paths")

    count = len(valid_paths)

    # Pre-classify via queue so we don't need a model call here.
    queue_map = {item["path"]: item["subfolder"] for item in list_queue(data_dir)}

    def _get_subfolder(p: Path) -> str:
        sf = queue_map.get(str(p))
        if sf:
            return sf
        from jobjob.classify.classify import JD, classify_file

        return "jobs" if classify_file(p) == JD else "profiles"

    subfolder_map = {str(p): _get_subfolder(p) for p in valid_paths}

    # Parse start time; fall back to now if unparseable.
    try:
        start_dt = datetime.fromisoformat(body.start_at.replace("Z", "+00:00"))
        if start_dt.tzinfo is None:
            start_dt = start_dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        start_dt = datetime.now(timezone.utc)

    concurrency = max(1, body.concurrency) if body.mode == "async" else 1
    interval_secs = max(0, body.interval_minutes) * 60

    # Expected start time per path (item i starts at start_at + i * interval).
    expected_times = {
        str(p): (start_dt + timedelta(seconds=i * interval_secs)).isoformat()
        for i, p in enumerate(valid_paths)
    }

    budget_error = check_budget(
        per_run_budget=s.get("per_run_budget", 2.0) * count,
        daily_budget=s.get("daily_budget", 20.0),
    )
    if budget_error:
        raise HTTPException(status_code=402, detail=budget_error)

    def _run_scheduled() -> dict:
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from jobjob.ailib.client.anthropic import AnthropicAdapter
        from jobjob.ailib.session import AIClient
        from jobjob.cli import build_credentials_loader
        from jobjob.config import load_settings

        settings = load_settings()
        client = AIClient(
            AnthropicAdapter(model=settings.model, api_key=settings.anthropic_api_key)
        )
        _logger = logging.getLogger("jobjob")
        creds_loader = build_credentials_loader(settings)

        delay = (start_dt - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            _logger.info("Schedule: waiting %.0f s until start time.", delay)
            time.sleep(delay)

        results: list[dict] = []

        def _process(p: Path) -> dict:
            sf = subfolder_map[str(p)]
            if sf == "profiles":
                from jobjob.enrich.workflow import enrich_inputs

                summary = enrich_inputs(
                    p,
                    query_service=client,
                    spreadsheet_id=settings.enrichment_output_sheet_id,
                    data_dir=data_dir,
                    logger=_logger,
                    _credentials_loader=creds_loader,
                )
            else:
                from jobjob.apply.workflow import apply_inputs

                summary = apply_inputs(
                    p,
                    query_service=client,
                    applicant=settings.applicant,
                    skip_drive=False,
                    use_cache=settings.cache_enabled,
                    parent_id=settings.applications_output_drive_id,
                    data_dir=data_dir,
                    logger=_logger,
                    _credentials_loader=creds_loader,
                )
            for entry in summary.get("items", []):
                result = entry.get("result")
                if isinstance(result, dict) and "token_usage" in result:
                    record_run(
                        calculate_cost(result["token_usage"], model=settings.model)
                    )
            return summary

        if concurrency == 1:
            for i, p in enumerate(valid_paths):
                if i > 0 and interval_secs > 0:
                    _logger.info(
                        "Schedule: waiting %d min before next job.",
                        body.interval_minutes,
                    )
                    time.sleep(interval_secs)
                try:
                    summary = _process(p)
                    results.append(
                        {"path": str(p), "status": "completed", "summary": summary}
                    )
                except Exception as exc:
                    results.append(
                        {"path": str(p), "status": "failed", "error": str(exc)}
                    )
        else:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures: dict = {}
                for i, p in enumerate(valid_paths):
                    if i > 0 and interval_secs > 0:
                        time.sleep(interval_secs)
                    futures[executor.submit(_process, p)] = str(p)

                for future in as_completed(futures):
                    path = futures[future]
                    try:
                        summary = future.result()
                        results.append(
                            {"path": path, "status": "completed", "summary": summary}
                        )
                    except Exception as exc:
                        results.append(
                            {"path": path, "status": "failed", "error": str(exc)}
                        )

        return {"processed": len(results), "items": results}

    job_id = _start_job(
        _run_scheduled,
        runs_dir=_runs_dir(s),
        kind="schedule",
        label=f"Schedule ({count})",
        paths=tuple(str(p) for p in valid_paths),
    )
    _jobs[job_id]["schedule"] = {
        "mode": body.mode,
        "concurrency": concurrency,
        "interval_minutes": body.interval_minutes,
        "start_at": start_dt.isoformat(),
        "paths": [str(p) for p in valid_paths],
        "expected_times": expected_times,
        "count": count,
    }
    return {"job_id": job_id, "count": count}


@router.get("/scheduled")
def list_scheduled() -> list[dict]:
    """Return all scheduled batch jobs with their schedule metadata."""
    return [
        {"job_id": jid, "status": job["status"], **job["schedule"]}
        for jid, job in reversed(list(_jobs.items()))
        if "schedule" in job
    ]


# ── Progress / status endpoints ────────────────────────────────────────────────


@router.get("/{job_id}/progress")
async def job_progress(job_id: str) -> StreamingResponse:
    """SSE stream: log records, then a final done/error event."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def _generate():
        job = _jobs[job_id]
        log_q = job["log_queue"]
        while True:
            try:
                record = log_q.get_nowait()
                if record is None:
                    break
                yield f"data: {json.dumps({'type': 'log', **record})}\n\n"
            except queue.Empty:
                if job["status"] != "running" and log_q.empty():
                    break
                await asyncio.sleep(0.05)

        final: dict[str, Any] = {"type": job["status"]}
        if job.get("result"):
            final["result"] = job["result"]
        if job.get("error"):
            final["message"] = job["error"]
        if job.get("overwrite_conflict"):
            final["overwrite_conflict"] = True
            final["folder_name"] = job.get("folder_name")
        yield f"data: {json.dumps(final)}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{job_id}/status")
def job_status(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job_id,
        "status": job["status"],
        "has_result": job.get("result") is not None,
        "error": job.get("error"),
        "overwrite_conflict": job.get("overwrite_conflict", False),
        "folder_name": job.get("folder_name"),
    }


@router.get("")
def list_jobs(request: Request) -> list[dict]:
    """Merged run history: persisted records + live in-memory jobs, newest first.

    Live jobs that never persisted (e.g. the runs dir was unwritable) are
    appended from the in-memory table so nothing running ever hides.
    """
    runs = _runs_dir(_app_settings(request))
    items = run_history.list_runs(runs, _jobs)
    listed = {i["run_id"] for i in items}
    items.extend(
        {
            "run_id": jid,
            "kind": "build",
            "label": "",
            "paths": [],
            "folder_name": j.get("folder_name"),
            "status": j["status"],
            "error": j.get("error"),
            "started_at": None,
            "finished_at": None,
            "has_log": False,
        }
        for jid, j in reversed(list(_jobs.items()))
        if jid not in listed
    )
    return items


@router.get("/{job_id}/log")
def job_log(job_id: str, request: Request) -> dict:
    """Return a persisted run's stored log text."""
    runs = _runs_dir(_app_settings(request))
    log_text = run_history.read_log(runs, job_id)
    if log_text is None:
        raise HTTPException(status_code=404, detail="No stored log for this run.")
    return {"run_id": job_id, "log": log_text}
