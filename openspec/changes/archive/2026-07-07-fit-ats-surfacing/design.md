# Design – Fit/ATS Surfacing

## Context

`assess_fit` runs inside `generate_application_readme`, so the band and axis
scores exist only in the README DOCX; `summary.json` persists just
`ats_coverage`. The Dashboard's completed list (tracking service → router →
`DashboardPage.tsx`) carries no insight fields, and the `GET
/api/tracking/applications/{folder}/ats` endpoint (#53) has no frontend
surface.

## Goals / Non-Goals

**Goals:**
- Persist a compact `fit` block in `summary.json` per application.
- Expose `fit` + `ats_coverage` on completed-list items (local mirror path).
- Dashboard: per-row insight chip, within-group sorting by fit/coverage, and a
  per-application ATS report modal with a re-check action.
- Older applications degrade gracefully (no chip; ATS modal still works via
  the live endpoint, or explains why it can't).

**Non-Goals:**
- No category-score persistence (the README carries the detail; the summary
  block stays compact and stable).
- No Drive-fallback insights (requires per-item Drive reads; mirror only).
- No re-layout of the Dashboard — the restructure will re-house this surface;
  the modal stays self-contained.

## Decisions

- **Compute fit once, in the workflow.** `apply/workflow.py` calls
  `assess_fit` and passes the result into `generate_application_readme` via a
  new optional `fit` parameter (computed internally when omitted, so existing
  callers/tests are unaffected). The workflow then persists
  `results["fit"] = fit_summary(fit)`.
- **`fit_summary` lives in `jobjob/structure/fit.py`**: `{band, role_fit,
  preference_fit}` with `None` axes preserved as `null` — consumers render
  what exists, mirroring the Fit contract.
- **Listing reads `summary.json` lazily** in the tracking service's
  local-mirror loop (one small JSON read per folder, already cached by
  `list_completed`); unreadable/missing summaries degrade to absent fields
  with a debug log, never failing the listing.
- **Chip format**: band badge (Strong/Moderate/Weak tint) plus
  `role 0.72 · ATS 0.64` (each segment only when present). No fit and no
  coverage → em-dash placeholder.
- **Sorting**: a small select on the applications table header — Company
  (default) · Role fit · ATS coverage — applied within each status group,
  score-descending, missing values last. Grouping by status is retained.
- **`AtsReportModal`** mirrors `NotesModal`: fetches the live ATS endpoint on
  open (always current — the resume may have been edited in Drive), renders
  the same sections as the CLI report, and a "Re-check" button refetches.
  A 409 (pre-ATS artifacts) renders the endpoint's detail message.

## Risks / Trade-offs

- [Per-folder summary read on refresh] → bounded by the existing cache; reads
  are local and tiny.
- [Chip crowds narrow rows] → single compact cell, `whitespace-nowrap`,
  em-dash when empty.
- [ATS modal needs Google credentials (one Docs read)] → the endpoint already
  reports failures; the modal surfaces its error detail rather than spinning.

## Migration Plan

Additive. Old applications simply lack `fit` in `summary.json` — every
consumer treats the absence as "no data". A re-run backfills.

## Open Questions

None blocking.
