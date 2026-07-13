# Webapp Restructure — Entities vs. Executions

## Why

The webapp's information architecture blurs three distinct actions (build the
application documents, re-build them, and *apply* — the future Playwright
autofill) and scatters one entity across pages: an application lives on the
Queue page while it's a pending JD, then jumps to the Dashboard once built,
with its state hidden behind tabs. Meanwhile runs are ephemeral — when a build
fails, the error dies with the in-memory job; "you need to be able to get back
to the error to see what went wrong."

Decisions were settled in the 2026-07-06 explore session (see
`webapp-restructure-decisions` memory): entities-vs-executions navigation,
"Apply" reserved for autofill, UI-only renames now, persistent run history,
and the unified two-source application model.

## What Changes

- **Navigation** becomes entity/execution pages: **Applications** (all
  application records), **Contacts** (contact entities), **Queue**
  (executions: run history + scheduling), **Profiles** (registry + active
  profile's content editors). Prompts demotes to the account menu; Settings
  stays in the account menu / gear.
- **Applications page**: ONE filterable/sortable table of all application
  records from both sources — input dir while queued (state QUEUED), output
  dir once built (BUILT/APPLIED/…; the stored GENERATED status renders as
  BUILT). State is a column with filter chips, not tabs. Row actions collapse
  into a dropdown (Build / Re-build / ATS / Notes / Drive / Delete); a
  disabled **Apply** action reserves the autofill seat (wired in a follow-up
  change). A failed latest run for a record surfaces as a derived chip
  linking to the Queue page.
- **Queue page** (executions): persistent run history — every launched job is
  recorded on disk with kind, label, timestamps, status, error, and its full
  log, viewable after restart. Scheduling stays here.
- **Contacts page**: the enrich domain — queued profile screenshots and
  completed contacts, with Enrich / Enrich-all.
- **Profiles page**: the profile registry (list, active, switch) plus the
  active profile's content editors (absorbs Static Content and resume
  import).
- **UI-only renames** with breadcrumb comments marking the future full
  rename: pipeline "Apply" → **Build**, "Re-run" → **Re-build**, status
  GENERATED → **BUILT** (display only; CLI, API routes, and stored values
  unchanged).

Explicitly deferred (follow-up changes): autofill wiring (background job,
fill-report, URL-gated Apply button), full CLI/API renames, live BUILDING
state on application rows.

## Capabilities

### New Capabilities

- `run-history`: Launched jobs persist as run records (metadata + full log)
  that survive restarts and are listable/viewable via the API and Queue page.
- `webapp-ia`: Entity-vs-execution navigation with the unified Applications
  table, Contacts page, Profiles page, and UI-only Build/Re-build/BUILT
  vocabulary.

### Modified Capabilities

<!-- application-insights: chip/sort/ATS-report requirements are satisfied by
     the Applications page (moved surface, same behavior) — no delta; the spec
     speaks of "the Dashboard's completed-applications table", which the
     design maps to the Applications table. -->

## Impact

- `webapp/backend/services/run_history.py` (new) + `routers/jobs.py`: record
  runs, tee logs to disk, list/log endpoints.
- `webapp/frontend/src`: `App.tsx` nav; new `ApplicationsPage`,
  `ContactsPage`, `ProfilesPage`; `QueuePage` rewritten as runs view;
  `DashboardPage`/`StaticContentPage` absorbed; row-action dropdown
  component; renamed copy.
- `tests/webapp/backend`: run-history service/router tests.
- `tests/webapp/frontend`: e2e updates for the new navigation and pages.
