# Full Build Rename (CLI / API / Stored Values)

> Follow-up to `webapp-restructure` (PR #58), which renamed the pipeline to
> **Build** in UI copy only and left `NOTE:` breadcrumb comments at every
> rename site. **Backlog record — input required before design** (see below).

## Why

The vocabulary is now split: users see Build / Re-build / Built, while the
CLI says `jobjob apply`, the API says `/jobs/apply` and `/jobs/apply/rerun`,
run records store `kind: "apply"`, and `metadata.json` stores
`status: GENERATED`. The breadcrumb comments mark every site; this change
retires them by completing the rename end to end.

## What Changes

- CLI: `jobjob build` as the primary subcommand (deprecation treatment for
  `jobjob apply` TBD below); `jobjob autofill` eventually presents as the
  "apply" step.
- API: `/jobs/build`, `/jobs/build/rerun` (or `/re-build`) with the old
  routes kept as aliases for one release (TBD).
- Stored values: run-record `kind` and the `GENERATED` application status
  become `build`/`BUILT` — requires a read-map or in-place migration of
  existing `metadata.json` / run records (TBD).
- Frontend types/useJobs kinds follow; breadcrumb `NOTE:` comments removed.
- Docs and README updated.

## Input Required — decide before design

- [ ] **Deprecation policy**: does `jobjob apply` stay as a permanent alias,
      warn-and-forward for a release, or break clean? Same question for the
      API routes (external callers: only the bundled frontend today).
- [ ] **Stored-value migration**: migrate `metadata.json` statuses in place
      (one-time rewrite) or map at read time forever? In-place is cleaner but
      touches user data; read-mapping keeps old folders untouched.
- [ ] **Timing**: should this wait until `autofill-apply-wiring` ships, so
      "apply" is fully freed up before the CLI grabs "build"?

## Capabilities

### New Capabilities

<!-- None expected — this renames surfaces of existing capabilities. -->

### Modified Capabilities

- `webapp-ia`: the "UI copy only, values unchanged" rename requirement is
  superseded by the full rename. Exact deltas at spec time.

## Impact

- `jobjob/__main__.py`, `jobjob/apply/` naming, `webapp/backend/routers/jobs.py`,
  `webapp/backend/services/application_metadata.py` (+ migration),
  `webapp/frontend` types/hooks, docs, and every `NOTE:` breadcrumb site
  (grep for "UI-only rename").
