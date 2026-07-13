# Fit/ATS Surfacing

## Why

The scoring trilogy's output is invisible where triage actually happens. The
Dashboard lists completed applications with status/notes/rerun but shows no fit
band, no role/preference scores, no ATS coverage — and underneath, the data
gap: `summary.json` persists only `ats_coverage`; the band and axis scores live
solely inside the README DOCX. "Sort my applications by role fit" — the
comparability the mass-weighted scoring was designed for — is impossible from
machine-readable outputs today.

## What Changes

- The apply workflow persists a compact `fit` block in `summary.json`
  (band, role_fit, preference_fit; optionally the category scores).
- The completed-applications listing (tracking backend) exposes those fields
  plus `ats_coverage` per application.
- Dashboard rows show a compact insight chip (e.g. "Strong · role 0.72 ·
  ATS 0.64") and support sorting by fit/coverage.
- A per-application ATS report view (modal or panel) backed by the existing
  `GET /api/tracking/applications/{folder}/ats` endpoint (#53) — the deferred
  frontend surface, including a re-check button (edit resume in Drive →
  re-check without re-running the pipeline).
- Older applications without persisted fit degrade gracefully (no chip, ATS
  view still works via the live endpoint).

## Capabilities

### New Capabilities

- `application-insights`: Fit and ATS results persisted machine-readably and
  surfaced (chips, sorting, report view) in the Dashboard.

### Modified Capabilities

<!-- Check at spec time whether quantitative-fit's spec needs a delta for the
     persistence requirement, or whether persistence is a new requirement here. -->

## Impact

- `jobjob/apply/workflow.py`: persist the fit block into `results`/summary.
- `webapp/backend/services/tracking_service.py` (+ router): completed-list
  fields.
- `webapp/frontend/src/pages/DashboardPage.tsx` + a small AtsReport component.
- `tests/`: persistence round-trip, listing fields, endpoint-driven view.
- Coordinate with the planned webapp restructure (this lands the ATS surface
  the restructure will later re-house; keep the component self-contained).
