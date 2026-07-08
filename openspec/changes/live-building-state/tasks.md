# Tasks: Live BUILDING State on Application Rows

> Frontend-only (backend already exposes what's needed: `/jobs` run records
> carry status/kind/entity_id/folder_name/paths; running builds join to rows via
> the existing `runMatchesApplication` / `latestRunFor` helpers on
> `ApplicationsPage.tsx`). Design settled: join by entity_id (item 3), poll ~5s
> like the Queue page, BUILDING is a badge NEXT TO the status select (never
> replacing it), batch/schedule marks all covered rows.

## 1. Derive the BUILDING flag

- [x] 1.1 `webapp/frontend/src/pages/ApplicationsPage.tsx`: derive per-row
  `building` = `latestRunFor(row)` exists AND its `status === "running"` AND its
  `kind` is a document-generation kind (`build` | `batch` | `schedule`) — NOT
  `apply` (autofill) or `enrich`. Reuse the existing `latestRunFor` /
  `runMatchesApplication` join (which already covers queued rows by path and
  built/rerun rows by folder_name/entity_id, so batch runs cover all their rows).

## 2. Render BUILDING (display-only)

- [x] 2.1 Built rows: render a small **Building…** badge NEXT TO the status
  select (do not replace `app_status`), linking to the live progress
  (`setViewingJobId(run.run_id)` — the existing job modal). QUEUED rows that are
  building show a BUILDING chip/indicator. Add BUILDING to `STATE_STYLES`.
- [x] 2.2 State filter: include a **BUILDING** chip in `presentStates` when any
  row is building, and make the filter match building rows. Keep it consistent
  with the derived (not stored) nature — filtering on BUILDING selects rows whose
  derived `building` is true, independent of their stored state.

## 3. Live refresh (~5s)

- [x] 3.1 Add a 5s poll of `fetchRuns` (mirror `QueuePage`'s `POLL_MS = 5000` +
  `setInterval` + cleanup) so BUILDING appears/clears live. When a run currently
  shown as BUILDING transitions to a terminal state between polls, also refresh
  queue + completed so the row moves to its built state (reuse the existing
  `fetchQueue` / `fetchCompleted` — avoid a forced full rescan on every tick;
  trigger the completed refresh on the transition, not unconditionally).

## 4. Tests + docs

- [x] 4.1 Frontend: the repo has NO JS test runner — do NOT add one (out of
  scope). Extract the BUILDING derivation into a small pure, exported helper
  (e.g. `isRowBuilding(row, runs)`) so it is self-contained and reviewable, and
  verify via `tsc --noEmit` (through `npm run build` = `tsc && vite build`) +
  `npm run lint` (0 errors). Confirm the backend suite is unaffected:
  `uv run pytest tests -q -k "not e2e"` as its own command.
- [x] 4.2 Docs: note the live BUILDING state on the Applications page in the
  relevant docs/ page.
