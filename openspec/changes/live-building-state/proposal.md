# Live BUILDING State on Application Rows

> Follow-up to `webapp-restructure` (PR #58). The approved status vocabulary
> is QUEUED → **BUILDING** → BUILT → APPLIED → …, but #58 shipped without the
> BUILDING display state. **Backlog record — design required** (see below).

## Why

An application row only shows build activity when the run was launched from
the current page session (the local "Building…" button) — a build started
from a schedule, a batch, or another tab renders as plain QUEUED/BUILT until
refresh. The run history (persisted in #58) already knows what is running;
the Applications table should reflect it as a real BUILDING state, completing
the approved vocabulary.

## What Changes

- Applications rows whose record has an active run display state **Building**
  (derived, never stored) with a link/affordance to the live progress.
- The state filter gains a Building chip when applicable.
- Derivation uses the merged run listing (`GET /api/jobs`) joined to records;
  refresh keeps rows current without a manual reload.

## Design Required — resolve before implementation

- [ ] **Join semantics**: a fresh build's run knows only the queued input
      path; the output folder name doesn't exist until the JD is parsed. When
      the run finishes, the queued row disappears and a built row appears —
      define the identity across that transition (path → folder mapping,
      or persist the eventual folder onto the run record at completion).
- [ ] **Batch/schedule runs** cover many records: does every covered row show
      Building for the whole batch, or only the item currently processing
      (requires per-item progress the batch summary doesn't expose today)?
- [ ] **Transport**: poll `/api/jobs` on the Applications page (interval?) vs.
      a lightweight SSE/subscription; interaction with the completed-list
      cache invalidation.
- [ ] **Interplay with the status column**: BUILDING is display-only and must
      not fight the user-editable status select (a built row can be re-built
      while its stored status is APPLIED — what shows?).

## Capabilities

### New Capabilities

<!-- Likely none — expected as deltas on webapp-ia's unified-table and
     failed-run requirements. Confirm at spec time. -->

### Modified Capabilities

- `webapp-ia`: unified Applications table requirement gains the derived
  BUILDING state; the failed-run-chip requirement may generalize to a
  latest-run status indicator.

## Impact

- `webapp/frontend/src/pages/ApplicationsPage.tsx` (derivation, chip,
  polling); possibly `webapp/backend/services/run_history.py` (persist the
  resolved folder name at completion) and the jobs router.
- `tests/`: derivation unit coverage + e2e.
