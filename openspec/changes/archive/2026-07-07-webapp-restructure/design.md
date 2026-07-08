# Design – Webapp Restructure (Entities vs. Executions)

## Context

Current IA: Dashboard (completed applications + completed profiles behind
tabs), Queue (pending input files + scheduling), Static Content, Prompts, and
Settings. Jobs (`webapp/backend/routers/jobs.py`) live in an in-memory `_jobs`
dict with SSE log streaming — nothing survives a restart. All decisions below
were settled with the user in the 2026-07-06 explore session.

## Goals / Non-Goals

**Goals:**
- Pages model *entities* (Applications, Contacts, Profiles) or *executions*
  (Queue); an application is one record whose state is a column, not a page.
- Runs persist with their logs; a failed build remains inspectable after
  restart.
- UI vocabulary: **Build** (today's apply pipeline), **Re-build** (re-run),
  **BUILT** (display of GENERATED); **Apply** is reserved for autofill.

**Non-Goals:**
- Autofill wiring (background job, fill-report, URL-gated Apply) — follow-up
  change; this change only reserves the disabled action.
- CLI/API renames — UI copy only, with breadcrumb comments at rename sites.
- Live BUILDING state on application rows (needs run⇄record joining beyond
  the failed-chip v1); richer run filtering/search.

## Decisions

### Run history (backend)

- **Storage**: one JSON record + one `.log` per run under
  `<applications_input_dir>/runs/` (the working root the webapp already
  owns). Record fields: `run_id`, `kind` (apply / enrich / batch / schedule),
  `label`, `paths`, `folder_name` (when known), `status`
  (running/completed/failed), `error`, `started_at`, `finished_at`.
- **Capture point**: `_start_job` — it already brackets every launched job
  and owns the log plumbing. It gains explicit `kind`/`label`/`paths` and a
  `runs_dir`; the worker adds a `FileHandler` next to the existing
  `_QueueHandler` (tee: live SSE unchanged, file gets the same records), and
  writes the record at start and again at completion. Failures to persist are
  logged, never fatal to the job (lazy error handling).
- **Endpoints**: `GET /api/jobs` returns the merged list — in-memory live
  jobs joined with persisted records by id (persisted metadata + live
  status), newest first. `GET /api/jobs/{id}/log` returns the stored log
  text (404 until a record exists). SSE progress endpoint unchanged.
- **Retention**: prune to the newest 200 records on each new run (constant in
  the service module).

### Applications page (unified table)

- **Two-source model** (confirmed): rows come from `/tracking/queue`
  (`subfolder == "jobs"` → state `QUEUED`) and `/tracking/completed`
  (`type == "jd"` → state = `app_status`, GENERATED **displayed** as BUILT;
  stored values unchanged).
- **State is a column** with filter chips (All + states present, in pipeline
  order QUEUED → BUILT → APPLIED → …); the existing sort select
  (Company / Role fit / ATS coverage) applies to the whole table. Status
  editing (the select) and insight chip carry over from the Dashboard
  implementation.
- **Row actions become a dropdown** (`RowActions` component, native
  details/summary-free: button + absolutely-positioned menu, closes on
  outside click): QUEUED rows get Build / Delete; built rows get Re-build /
  ATS / Notes / Drive / Apply-(disabled, "autofill — coming in a follow-up").
- **Failed-run chip**: the page fetches `/api/jobs`; a record whose latest
  matching run (by `folder_name`, else by `paths` containing the queue path)
  failed shows a "⚠ failed" chip linking to `#queue`.
- Add-JD panel and "Build all" live here (moved from the old Queue page).

### Queue page (executions)

- Rewritten as the runs view: scheduled section (unchanged) + run history
  from `GET /api/jobs`, each row expandable to its stored log
  (`/{id}/log`). Polls every 5s while any run is `running`. Jobs launched
  from other pages keep their live `JobProgressModal` flow.

### Contacts / Profiles pages

- **Contacts** = the enrich domain: queued profile screenshots (Enrich /
  Enrich-all) + completed contacts table (moved from the Dashboard's
  Profiles tab).
- **Profiles** = registry header (list registered profiles, active marker,
  switch via existing `/profiles` endpoints, read-only badge for the bundled
  example) above the absorbed Static Content editors (highlights / skills /
  templates / reference / import tabs, unchanged internals).
  `StaticContentPage` is renamed, not rewritten.
- **Prompts** demotes to the account menu; the gear/Settings flow is
  untouched.

### Renames

UI copy only. Each rename site carries:
`NOTE: UI-only rename — API/CLI still say "apply"/"rerun"/"GENERATED"; full rename is a future change.`

## Risks / Trade-offs

- [Two-source table can show a JD twice (queued file + built folder) during
  the build window] → acceptable v1; rows are keyed by source path/folder so
  nothing collides, and the completed cache refreshes on job settle.
- [Run files accrue] → prune-to-200 on write.
- [E2E suite pins old nav labels/headings] → tests are rewritten with the IA
  (they are small and selector-driven).
- [`_jobs` and run records can disagree if the process dies mid-run] → on
  listing, a persisted `running` record with no live counterpart is reported
  as `failed` ("interrupted") — exactly the case persistence exists for.

## Migration Plan

Additive on the backend (new dir, new endpoints; existing endpoints keep
their shapes). Frontend routes: `#dashboard`/`#static` fall back to the
Applications page via the existing unknown-hash default; no stored data
changes. Rollback = revert.

## Open Questions

None blocking — the three explore-session questions were answered by the user
(status vocabulary, persistent run history, two-source model).
