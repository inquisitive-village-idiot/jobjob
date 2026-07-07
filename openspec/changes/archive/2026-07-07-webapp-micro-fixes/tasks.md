# Tasks: Webapp Micro-Fixes

## 1. Error copy

- [x] 1.1 Reword `_resolve_app_folder`'s 400 detail in `webapp/backend/routers/tracking.py` to describe the actual condition (local applications mirror not configured) instead of "status writes unavailable"
- [x] 1.2 Update any tests asserting the old error string

## 2. Docs

- [x] 2.1 Add a `jobjob ats` section to `docs/guide/usage-applications.rst` covering the standalone re-check subcommand (post-#53)

## 3. pyproject comments

- [x] 3.1 Add clarifying comments to both `playwright>=1.40` entries in `pyproject.toml` (autofill runtime extra vs. frontend e2e test group)

## 4. Verify

- [x] 4.1 Run the webapp backend test suite and docs build (if configured) to confirm nothing regressed
