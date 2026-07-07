# Tasks: Fit/ATS Surfacing

## 1. Persistence

- [x] 1.1 Add `fit_summary(fit) -> dict` (band, role_fit, preference_fit) to `jobjob/structure/fit.py`
- [x] 1.2 `generate_application_readme` accepts an optional precomputed `fit` (computes when omitted); `apply/workflow.py` computes fit once, passes it through, and persists `results["fit"]`

## 2. Backend listing

- [x] 2.1 Tracking service (local-mirror path): read each folder's `summary.json` and attach `fit` + `ats_coverage` to the item; missing/unreadable degrades to absent fields

## 3. Frontend

- [x] 3.1 Types: `fit` + `ats_coverage` on `CompletedItem`; ATS report response type
- [x] 3.2 Insight chip column in the completed-applications table (band tint + available scores; placeholder when absent)
- [x] 3.3 Within-group sort control: Company (default) / Role fit / ATS coverage, missing values last
- [x] 3.4 `AtsReportModal` component: fetch `GET /tracking/applications/{folder}/ats` on open, render report sections, Re-check button refetches, 409 detail surfaced; wire an ATS action into the row

## 4. Tests

- [x] 4.1 `fit_summary` round-trip incl. null axes; workflow persists the fit block into `summary.json`
- [x] 4.2 Tracking service: insights attached from summary.json; absent/corrupt summary degrades

## 5. Verify

- [x] 5.1 Full pytest run green; frontend `tsc`/build clean
