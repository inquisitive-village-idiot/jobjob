# Tasks: Full Build Rename

## 1. CLI (clean break)

- [x] 1.1 `jobjob/__main__.py` `COMMANDS`: `build` → `apply_main`, `apply` →
  `autofill_main`, drop the `autofill` key; update the module docstring to
  describe `build` (generation) and `apply` (autofill)
- [x] 1.2 `jobjob/apply/__main__.py` argparse `prog="jobjob apply"` →
  `"jobjob build"`; `jobjob/autofill/__main__.py` `prog` → `"jobjob apply"`

## 2. HTTP API (clean break)

- [x] 2.1 `webapp/backend/routers/jobs.py`: rename routes to `/jobs/build`,
  `/jobs/build/rerun`, `/jobs/build/from-url`, `/jobs/build/from-text`,
  `/jobs/build-all`; rename handlers/helpers (`launch_build`,
  `launch_build_rerun`, `_make_build_run`, `_launch_snapshot_build`,
  `launch_build_all`); document-generation runs pass `kind="build"`; remove the
  `Re-build` breadcrumb comment. Leave `jobjob.apply.workflow.apply_inputs` and
  the `jobjob/apply/` package name unchanged (out of scope; see design)

## 3. Stored status → BUILT (read-normalized)

- [x] 3.1 `application_metadata.py`: rename enum `GENERATED` → `BUILT`
  (`value="BUILT"`); `DEFAULT_STATUS = ApplicationStatus.BUILT`
- [x] 3.2 Add schema versioning: `_SCHEMA_VERSION = 2`; a `_migrate(data)` that,
  for `schema_version < 2` (absent ⇒ 0), normalizes `status: "GENERATED"` →
  `"BUILT"`; apply it in `read_metadata` (no source rewrite); writes stamp 2
- [x] 3.3 `tracking_service.py`: add `GENERATED` as a legacy alias in
  `_STATUS_PREFIX_RE` and normalize a matched `GENERATED` prefix to `BUILT`;
  update the `> GENERATED` precedence comment to `> BUILT`

## 4. Run kind → build + one-time fixup

- [x] 4.1 `run_history.py`: document-generation runs record `kind: "build"`;
  add `migrate_legacy_kinds(runs_dir)` — marker-guarded (`.kind_migrated_v1`
  sentinel) one-time rewrite of `kind: "apply"` → `"build"`; update
  `start_run` docstring kinds to `build / apply (autofill) / enrich / batch /
  schedule`
- [x] 4.2 `webapp/backend/main.py` `_startup`: invoke `migrate_legacy_kinds`
  against the runs directory (guarded so it runs at most once)

## 5. summary.json schema stamp

- [x] 5.1 `jobjob/apply/workflow.py`: stamp `schema_version` on the written
  `summary.json`

## 6. Frontend

- [x] 6.1 `types/index.ts`: `APP_STATUSES` `"GENERATED"` → `"BUILT"`;
  `JobRecord.kind` union `"apply"` → `"build"`; `> GENERATED` comment → `> BUILT`
- [x] 6.2 `hooks/useJobs.ts`: POST paths → `/jobs/build`,
  `/jobs/build/from-url`, `/jobs/build/from-text`, `/jobs/build/rerun`,
  `/jobs/build-all`; `kind: "apply"` payloads → `"build"`; kind union updated
- [x] 6.3 `ApplicationsPage.tsx`: BUILT replaces GENERATED in `STATE_STYLES`,
  `STATE_ORDER`, default fallbacks, and the display helper (BUILT → "Built");
  remove the UI-only-rename breadcrumb
- [x] 6.4 Remove UI-only-rename breadcrumbs in `AddJdPanel.tsx`,
  `LaunchConfirmModal.tsx`, `JobProgressModal.tsx`, `QueuePage.tsx`

## 7. Docs

- [x] 7.1 README + `docs/` updated: `jobjob build` (generation), `jobjob apply`
  now means autofill, `/jobs/build*` routes, BUILT status; call out the
  breaking CLI repurposing where the CLI is documented

## 8. Tests + verify

- [x] 8.1 Backend tests: CLI dispatch (`build`→generation, `apply`→autofill,
  `autofill` unknown); jobs routes respond under `/jobs/build*` and record
  `kind="build"`; metadata read migration (legacy GENERATED/unstamped → BUILT,
  source untouched; write stamps v2); prefix parser accepts legacy GENERATED;
  `migrate_legacy_kinds` rewrites once and is marker-guarded; summary.json is
  stamped
- [x] 8.2 Frontend: type-check/build green; update any tests referencing the old
  routes/kinds/GENERATED
- [x] 8.3 Run backend suite (`pytest`) and the frontend build/type-check; confirm
  green
