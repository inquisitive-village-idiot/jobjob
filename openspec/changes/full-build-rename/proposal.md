# Full Build Rename (CLI / API / Stored Values)

> Follow-up to `webapp-restructure` (PR #58), which renamed the pipeline to
> **Build** in UI copy only and left `NOTE:` breadcrumb comments at every
> rename site. This change retires those breadcrumbs by completing the rename
> end to end. **All input questions resolved 2026-07-07 — ready for design.**

## Why

The vocabulary is split: users see Build / Re-build / Built, while the CLI
says `jobjob apply`, the API says `/jobs/apply` and `/jobs/apply/rerun`, run
records store `kind: "apply"`, and `metadata.json` stores
`status: GENERATED`. With a CLI user base of one and the webapp as the front
door for new users, this is the cheapest moment that will ever exist to make
the vocabulary consistent — and it gets more expensive every release.

## What Changes

- **CLI (major version, no deprecation window)**: `jobjob build` becomes the
  document-generation command; **`jobjob apply` is repurposed** to mean the
  autofill step (today's `jobjob autofill`); the `autofill` subcommand is
  **dropped** — one word per action, no stale synonyms whose meaning could
  drift later.
- **API**: clean break — `/jobs/build`, `/jobs/build/rerun`; no aliases. The
  bundled frontend is the only consumer and ships in lockstep.
- **Stored values — shim, never rewrite user data**:
  - `metadata.json` (Drive-synced mirror = user data): map `GENERATED → BUILT`
    at read; always write `BUILT`; the folder-name prefix parser accepts both
    words. Old folders stay byte-identical; changelog note entries are
    historical facts and are never touched.
  - `runs/*.json` (local operational scratch): silent first-boot fixup —
    rewrite legacy `kind: "apply"` → `"build"` (or clear the dir). No user
    consent dialog; it's our data and pruned-to-200 anyway. Thereafter
    `kind: "apply"` cleanly means autofill.
- **Schema versioning (the growth path)**: start stamping a per-file integer
  `schema_version` on every `metadata.json` / `summary.json` write. **Absence
  is the stamp**: unstamped files are unambiguously `v0`, so the entire
  existing mirror is retroactively versioned without touching a byte. The
  GENERATED→BUILT shim is implemented as the `v0 → v1` read migration —
  deliberately the degenerate case (chain of length one; YAGNI on a full
  registry) but shaped so it can grow into lazy-migration chains
  (per-version modules with a common interface) if formats ever change
  non-trivially. Schema version is decoupled from the app version: it
  increments only on format changes, and it — not the changelog or docs — is
  the single source of truth the reader and future migrations key off.
- Frontend types/`useJobs` kinds and `APP_STATUSES` follow; every
  `NOTE: UI-only rename` breadcrumb is removed; docs/README updated.

## Decisions (2026-07-06/07 explore sessions)

1. **Repurpose `apply` now** — zero CLI-user risk; deprecation ceremony would
   protect users who don't exist. Major-version change.
2. **Read-shim over in-place migration** — the mirror is Drive-synced user
   data: a rewrite means mtime churn, re-uploads, and conflict-copy risk over
   historical applications, and the read shim is needed forever anyway (for
   backups, un-synced machines, Drive-trash restores). The shim is the whole
   cost; migration would add risk without removing code.
3. **Timing: no constraint; prefer rename-first** — so `autofill-apply-wiring`
   is born under the right names (`/jobs/apply`, `kind: "apply"` = autofill)
   instead of shipping under old names and renaming a week later.

## Out of Scope

- **Post-update "what's new + actions" modal** — considered and deferred:
  user data is never rewritten (shim) and operational data needs no consent,
  so the modal has no current customer. Record as its own proposal if a
  future migration is lossy or genuinely opt-in.

## Capabilities

### New Capabilities

<!-- None expected — this renames surfaces of existing capabilities. The
     schema_version stamp may warrant a small ADDED requirement on whichever
     capability owns application metadata; confirm at spec time. -->

### Modified Capabilities

- `webapp-ia`: the "UI copy only, values unchanged" rename requirement is
  superseded by the full rename. Exact deltas at spec time.

## Impact

- `jobjob/__main__.py` (COMMANDS: `build`, repurposed `apply`, drop
  `autofill`), `jobjob/apply/` naming, `webapp/backend/routers/jobs.py`
  (routes + run kinds + first-boot runs fixup),
  `webapp/backend/services/application_metadata.py` (read shim +
  `schema_version` stamping), `jobjob/apply/workflow.py` (`summary.json`
  stamping), `webapp/frontend` types/hooks, docs, and every breadcrumb site
  (grep for "UI-only rename").
