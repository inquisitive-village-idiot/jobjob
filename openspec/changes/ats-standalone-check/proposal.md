# ATS Standalone Check

## Why

The ATS assessment only runs inside the full apply workflow, so verifying a
resume tweak means re-running the whole five-call pipeline. Every input the
assessment needs is already saved per application (`summary.json`,
`skills_analysis.json`, the resume Doc id), so the tighten-the-resume iteration
loop — edit the Doc in Drive, re-check coverage — can run with **zero Anthropic
calls** and one Docs read.

## What Changes

- New core module: rebuild the assessment inputs from a processed application's
  output directory and re-run `assess_ats`; render a readable plain-text report
  (coverage score, buckets, recommendations, parseability, fit-vs-ATS gaps).
- New CLI subcommand `jobjob ats <application-output-dir>` registered in
  `jobjob/__main__.py` `COMMANDS`.
- New webapp endpoint `GET /api/tracking/applications/{folder_name}/ats`
  returning the assessment as JSON (backend only; frontend surface deferred to
  the planned webapp restructure).
- Drive-skipped applications (no `resume_id`) report a skipped assessment
  rather than erroring; missing artifacts produce clear errors.

## Capabilities

### New Capabilities

- `ats-standalone-check`: Re-assess a processed application's rendered resume
  from saved artifacts, via CLI and webapp, without invoking the AI pipeline.

### Modified Capabilities

<!-- None — assess_ats and its spec are unchanged; this adds entry points. -->

## Impact

- `jobjob/apply/recheck.py` (new): artifact loading, reassessment, text report.
- `jobjob/__main__.py`: register the `ats` subcommand.
- `webapp/backend/routers/tracking.py`: the re-check endpoint (reuses
  `_resolve_app_folder`).
- `tests/`: loader/report/CLI/endpoint coverage.
- No new dependencies; no Anthropic calls (one Google Docs read per check).
