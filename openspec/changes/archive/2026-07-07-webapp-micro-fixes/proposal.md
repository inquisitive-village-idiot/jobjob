# Webapp Micro-Fixes

## Why

Three small frictions surfaced during the codebase survey — none worth its own
change, together worth one small PR.

## What Changes

- **Misleading error copy**: `_resolve_app_folder`'s 400 detail says "status
  writes unavailable", but the helper now backs read-only routes too (notes,
  ats). Reword to describe the actual condition (local applications mirror not
  configured).
- **`jobjob ats` documentation**: add the subcommand to
  `docs/guide/usage-applications.rst` (post-#53; the CLI exists but the user
  guide doesn't mention it).
- **Playwright dependency disambiguation**: `playwright>=1.40` appears twice
  in `pyproject.toml` — the `autofill` optional extra (runtime feature) and
  the `test` dependency group (frontend e2e). Both are correct; neither says
  why. Add clarifying comments so the double entry reads as intent, not
  accident.

## Capabilities

### New Capabilities

<!-- None — copy, docs, and comments only; no behavioral requirements. -->

### Modified Capabilities

<!-- None. -->

## Impact

- `webapp/backend/routers/tracking.py`: one string.
- `docs/guide/usage-applications.rst`: one section.
- `pyproject.toml`: two comments.
- Tests: none beyond existing (no behavior changes); update any test asserting
  the old error string.
