# Docs & Tests High-Level Overview Pass

> Final-phase change: execute **after** the rest of the backlog merges and
> before (or with) the major release. Per-change PRs update tests and docs
> locally; this pass audits the whole at the new altitude.

## Why

Each change ships its own tests and doc edits, but nobody has re-read the
documentation or the test suite *as a whole* since the architecture moved:
three-tier identity, persistent run history, entities-vs-executions IA, the
Build/Apply vocabulary, model-scoped caching. Local edits accumulate into
global drift: guides that describe flows page-by-page when the pages moved,
README/CLAUDE.md altitude mismatches, test coverage that is dense where
development happened and thin at the seams between changes.

## What Changes

- **Docs audit** (jobjob + webapp): read every guide end-to-end against the
  shipped behavior; fix stale flows, unify vocabulary (Build/Re-build/Apply,
  entity/source/execution), add a short architecture overview (the tier
  model, run history, folder layout) where none exists; verify README and
  CLAUDE.md agree with docs/.
- **Test-suite review at the integration level**: identify seams the
  per-change tests don't cross (e.g., identity joins across
  tracking + run-history + frontend contract; archive/promote round-trips;
  rename shims under the schema_version reader) and add targeted integration
  tests; prune duplicated coverage if found.
- Release notes / changelog draft for the major release fall out of this
  audit.

## Capabilities

### New Capabilities

<!-- None — documentation and test coverage only. Archive with --skip-specs
     unless the audit surfaces genuine spec drift, which should be fixed as
     spec updates in this change. -->

### Modified Capabilities

<!-- Possible small corrections if the audit finds spec/behavior drift. -->

## Impact

- `docs/`, `README.md`, `CLAUDE.md`, webapp in-UI copy where stale.
- `tests/`: new integration seams; possible pruning.
- Input to the major-release notes.
