# Autofill Apply Wiring

> Follow-up to `webapp-restructure` (PR #58), which reserved the disabled
> **Apply** action in the Applications row menu. Decisions below were settled
> in the 2026-07-06 explore session; this change is ready for design/specs
> once #58 merges.

## Why

"Apply" is now reserved vocabulary for the Playwright autofill step, but only
the CLI (`jobjob autofill`) can run it. The webapp row action is a disabled
placeholder. Wiring it in closes the entities-vs-executions loop: build the
documents, then apply to the posting, both from the Applications table with
runs recorded in the Queue history.

## What Changes

- **Posting-URL persistence**: the application record persists its source
  posting URL (URL/text ingests know it; PDF drops don't). `summary.json`
  field + tracking-listing exposure. This is the gate: the Apply action
  enables **only** when the record carries a URL.
- **Backend launch endpoint**: start autofill as a background job through the
  existing jobs framework (so it lands in the persistent run history),
  **non-blocking** — `wait_for_human` in `jobjob/autofill/runner.py` is the
  injection point so a page waiting on the human never wedges a worker
  thread.
- **Fill report** surfaces through job progress/logs: which fields were
  filled, which were left for the human.
- **Frontend**: enable the row-menu Apply action when the URL is present
  (tooltip explains when absent); launch + watch via the existing job modal;
  the run appears on the Queue page.
- **Scope bounds (unchanged from CLI autofill)**: contact basics only —
  resume upload, custom questions, and submit are explicitly left to the
  human; no multi-page automation; the persistent Chromium profile keeps ATS
  logins.

## Capabilities

### New Capabilities

- `autofill-apply`: Launch the autofill step for a built application from the
  webapp, gated on a persisted posting URL, running as a recorded background
  job with a fill report.

### Modified Capabilities

- `webapp-ia`: the reserved Apply action becomes conditionally enabled
  (delta on the row-actions requirement).

## Impact

- `jobjob/apply/workflow.py` (persist posting URL when known) +
  `jobjob/ingest/jd_source.py` (carry the URL through snapshots).
- `webapp/backend/routers/jobs.py` (+ possibly a small autofill service):
  launch endpoint, run-history kind.
- `webapp/frontend`: ApplicationsPage row actions, job modal reuse.
- `tests/`: URL persistence round-trip, gating, launch wiring (runner mocked).
