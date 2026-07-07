# Design – Webapp Micro-Fixes

## Context

Three cosmetic frictions found during the 2026-07-06 codebase survey: a stale
error detail in `_resolve_app_folder`, a missing `jobjob ats` section in the
user guide, and an unexplained duplicate `playwright` pin in `pyproject.toml`.
No behavior changes.

## Goals / Non-Goals

**Goals:**
- Error copy describes the actual failure condition (local applications mirror
  not configured), not "status writes".
- `docs/guide/usage-applications.rst` documents the `jobjob ats` subcommand.
- Both `playwright` entries in `pyproject.toml` carry a comment stating why
  each exists.

**Non-Goals:**
- No API, schema, or behavior changes; no new capabilities or spec deltas.
- No consolidation of the playwright pins — both are intentional.

## Decisions

- **Error wording**: say what is missing and how to fix it
  ("Local applications mirror is not configured (set APPLICATIONS_OUTPUT_DIR)")
  rather than which caller failed — the helper backs multiple routes.
- **Docs placement**: add the `jobjob ats` section to
  `usage-applications.rst` alongside the existing apply workflow docs, since
  the ATS re-check operates on application output directories.
- **Comments over restructuring** for pyproject: TOML comments are the
  lightest way to record intent.

## Risks / Trade-offs

- Tests asserting the old error string would break → update them in the same
  commit (search before merge).
