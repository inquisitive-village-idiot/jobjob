# Design: Full Build Rename

## Context

`webapp-restructure` (PR #58) renamed the document-generation pipeline to
**Build** in UI copy only, leaving `NOTE: UI-only rename` breadcrumbs at every
site. This change completes the rename across the CLI, the HTTP API, and stored
value vocabulary, and retires the breadcrumbs. The proposal's decisions
(repurpose `apply`, read-shim over migration, rename-first) are settled; this
document fixes the design-level questions the proposal deferred to spec time.

## Rename boundary: surfaces, not internals

The rename touches **user-facing surfaces and stored values**, not internal
Python identifiers:

- **Renamed**: CLI verbs, HTTP route paths, the run-record `kind` value for
  document generation, the application `status` vocabulary (`GENERATED` →
  `BUILT`), frontend types/hooks/copy, and docs. Every `NOTE: UI-only rename`
  breadcrumb is removed.
- **Kept as-is (out of scope, documented)**: the `jobjob/apply/` package name,
  `jobjob.apply.workflow.apply_inputs` (the shared pipeline entry imported in
  many places), and other internal function names not tied to a surface.
  Renaming the package/pipeline would ripple through imports for no
  user-visible gain and is explicitly *not* part of this change. The router
  handlers in `jobs.py` (only referenced via their decorators) and the local
  `_make_apply_run` helper ARE renamed to `build`, because they carry the
  `kind`/route vocabulary and leaving them half-named would keep the very
  confusion the breadcrumb retirement targets.

This makes one intentional decoupling explicit: `python -m jobjob.apply` and
CLI `jobjob build` both run document generation. The module keeps its name; the
verb is `build`.

## CLI (major version, clean break)

`jobjob/__main__.py` `COMMANDS`:

- `build` → `apply_main` (document generation; today's `apply`)
- `apply` → `autofill_main` (autofill; today's `autofill`)
- **drop** the `autofill` key entirely
- `enrich`, `auth`, `ats`, `skills` unchanged

`jobjob/apply/__main__.py` argparse `prog="jobjob apply"` → `"jobjob build"`;
`jobjob/autofill/__main__.py` `prog` → `"jobjob apply"`. Update the
`jobjob/__main__.py` module docstring. No deprecation aliases — CLI user base
is one, and a deprecation window protects users who do not exist.

## HTTP API (clean break, frontend in lockstep)

`webapp/backend/routers/jobs.py`:

- `/jobs/apply` → `/jobs/build`
- `/jobs/apply/rerun` → `/jobs/build/rerun`
- `/jobs/apply/from-url` → `/jobs/build/from-url`
- `/jobs/apply/from-text` → `/jobs/build/from-text`
- `/jobs/apply-all` → `/jobs/build-all`
- Handlers renamed to match (`launch_build`, `launch_build_rerun`,
  `_make_build_run`, `_launch_snapshot_build`, `launch_build_all`); the
  `kind="apply"` passed to `_start_job` for document-generation runs becomes
  `kind="build"`. `/jobs/enrich` and its `kind="enrich"` are untouched.
- Remove the `NOTE: UI copy calls this "Re-build"…` breadcrumb.

No aliases. The bundled frontend is the only consumer and ships together.

## Stored values

### Application status: `GENERATED` → `BUILT` (read-normalized)

`webapp/backend/services/application_metadata.py`:

- `ApplicationStatus.GENERATED` becomes `ApplicationStatus.BUILT` (`value =
  "BUILT"`); `DEFAULT_STATUS = ApplicationStatus.BUILT`.
- **Read shim**: `read_metadata` normalizes a stored `status: "GENERATED"` to
  `"BUILT"` on read (see schema versioning below), so `ApplicationStatus(...)`
  never sees the retired value. Writes always emit `BUILT`.
- Old Drive-mirror folders are never rewritten in place; historical changelog
  `notes` text (e.g. "Status set to GENERATED") is a factual record and is left
  byte-identical.

`webapp/backend/services/tracking_service.py`:

- `_STATUS_PREFIX_RE` is built from the enum values, so it auto-accepts `BUILT`.
  Add `GENERATED` as a **legacy alias** in that alternation and normalize a
  matched `GENERATED` prefix to `BUILT`, so a legacy `GENERATED …` folder name
  still resolves (proposal: "accepts both words").
- The `> GENERATED` fallbacks in comments/precedence become `> BUILT`.

### Run kind: `apply` → `build` for document generation

`runs/*.json` is local operational scratch (pruned to 200), not user data.

- New document-generation runs record `kind: "build"`.
- **One-time first-boot fixup**: at app startup
  (`webapp/backend/main.py` `_startup`), a marker-guarded migration
  (`run_history.migrate_legacy_kinds(runs_dir)`) rewrites any existing
  `kind: "apply"` records to `"build"` and drops a sentinel
  (`runs/.kind_migrated_v1`) so it runs exactly once. **Marker-guarded, not a
  read-shim**: once `autofill-apply-wiring` (backlog item 4) lands, autofill
  runs will legitimately record `kind: "apply"`, so a forever read-map would
  corrupt them. After the one-time fixup, `kind: "apply"` cleanly means
  autofill.
- `run_history.start_run` docstring: kinds are `build / apply (autofill) /
  enrich / batch / schedule`.

### Schema versioning

`metadata.json` **already** stamps `schema_version` (currently `1`). The
proposal's illustrative "absence = v0, GENERATED→BUILT = v0→v1" is realized
against that reality as a bump to **v2**:

- `_SCHEMA_VERSION = 2`. Reads run a version-keyed migration: a file at
  `schema_version < 2` (absent ⇒ `0`, or `1`) has its `status` normalized
  `GENERATED → BUILT`; a `v2` file is already post-rename and skipped. Writes
  stamp `2`. The migration is a single degenerate step (YAGNI on a registry)
  but shaped as `_migrate(data) -> data` so lazy per-version chains can grow if
  a future format change is non-trivial. Absence-of-stamp remains a valid `v0`;
  the whole existing mirror is retroactively versioned without touching a byte.
- `summary.json` (`jobjob/apply/workflow.py`) starts stamping `schema_version`
  on write (new key alongside the results; no reader migration needed yet — it
  is written fresh each run).

Schema version is decoupled from the app version and is the single source of
truth the reader keys off — it increments only on format changes.

## Frontend

`webapp/frontend/src`:

- `types/index.ts`: `APP_STATUSES` `"GENERATED"` → `"BUILT"`; `JobRecord.kind`
  and `useJobs.ts` kind unions `"apply"` → `"build"` for document generation
  (keep `enrich`/`batch`); the `> GENERATED` comment → `> BUILT`.
- `hooks/useJobs.ts`: POST paths → `/jobs/build`, `/jobs/build/from-url`,
  `/jobs/build/from-text`, `/jobs/build/rerun`, `/jobs/build-all`; `kind:
  "apply"` payloads → `"build"`.
- `ApplicationsPage.tsx`: the `GENERATED → "Built"` display special-case and
  `STATE_ORDER`/`STATE_STYLES`/default fallbacks move to `BUILT` (BUILT now
  renders as "Built" directly). Remove the UI-only-rename breadcrumbs there and
  in `AddJdPanel.tsx`, `LaunchConfirmModal.tsx`, `JobProgressModal.tsx`,
  `QueuePage.tsx`.
- The `ApplicationStatus`/`APP_STATUSES` "keep in sync" contract holds: BUILT
  replaces GENERATED on both sides.

## Docs

README + `docs/` references to `jobjob apply` (document generation), `/jobs/apply`,
`GENERATED`, and the pipeline vocabulary are updated to Build/BUILT. The
`jobjob apply` = autofill repurposing is called out where the CLI is documented.

## Risks / tradeoffs

- **CLI muscle-memory**: `jobjob apply` silently changes meaning
  (generation → autofill). Accepted per proposal decision 1; the release is
  major and the change is called out in docs/changelog.
- **Module/verb decoupling** (`jobjob.apply` package runs `jobjob build`) can
  briefly confuse a maintainer; documented here and in the CLI docstring.
- **Legacy `GENERATED` prefix folders**: covered by the prefix-regex alias;
  low real incidence (GENERATED is the default, rarely prepended).
- **Schema bump interplay**: the migration keys on `schema_version < 2`, so a
  hypothetical hand-edited file already at `2` with a stray `GENERATED` would
  not be normalized. Not a real scenario (v2 is only written by post-rename
  code, which never emits GENERATED).
