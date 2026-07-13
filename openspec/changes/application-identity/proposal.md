# Application Identity — Entity / Source / Execution

> Designed in the 2026-07-07 explore session (all decisions settled — see
> design.md). Foundation for `autofill-apply-wiring` and
> `live-building-state`; sequence this change first.

## Why

The system has no stable way to refer to one application across its life.
An application "is" an input file path while queued, then a folder name once
built, then a *different* folder name after the user renames it (which the
status-prefix parser deliberately supports). Every cross-reference — run
records, ATS/status/notes routes, the Drive web-link match — keys off
whichever string was handy, and quietly stops resolving when the string
changes. Nothing crashes; references just go stale. Each pending feature
(autofill URL gating, live BUILDING state, failed-run chips) would otherwise
re-pay this tax with its own ad-hoc join.

Separately, three adjacent gaps share the same root: parse results live in
the per-execution `summary.json` (so re-builds clobber user corrections),
re-processing silently overwrites local artifacts, and there is no honest
answer to "which folder owns the status" once an application has more than
one execution.

## What Changes

A three-tier data model, with files remaining the source of truth:

- **Entity** — one job opportunity (or one contact). A uuid4 minted at first
  processing; no artifacts of its own — connective tissue owning status,
  notes, and dedup links. `metadata.json` is recognized as this tier.
- **Source** — the posting (or profile) itself: file URI and/or web URI,
  external requisition id (attribute, never the key), and the **parse-once**
  fields (company, role, description). User-editable to correct parse errors
  (company / role / URL / external ref only); re-parse is an explicit action
  that warns it overwrites corrections. New `source.json` at the entity
  folder root.
- **Execution** — one build/enrich/autofill run. The existing run records
  (`run_id`, #58) extended with `entity_id`; `summary.json` is the
  execution's birth certificate.

Plus the physical layout that makes multiple executions non-intrusive:

- **One output dir + a storage adapter** (see design D7). A build
  materializes the entity folder `<Company> - <Role>` under the single
  user-defined output dir and places **all** of that execution's artifacts
  there — phase-1 wrote identity to the entity folder but artifacts still
  land in a tempdir/`output_dir`, so phase 2 first unifies placement. Whether
  an operation touches Drive or the local filesystem is an adapter choice
  **dispatched per file type** (Google Docs → Drive API; plain files →
  pathlib), extensible to other backends. The seam mirrors the existing
  `AIAdapter` idiom.
- The entity folder keeps **exactly today's name and root contents** — the
  primary execution's artifacts live at the folder root, always. Superseded
  executions (only when the user opts out of overwrite) move into
  `archive/<timestamp>/` as complete, self-contained snapshots. "Which one
  do I want?" is answered by location, never memory. Promote = swap an
  archive dir with the root (root archived first, then promoted files moved
  up). **Archive/promote is adapter-dispatched**: a Drive-managed Doc is
  reparented via **API move-by-id** (`files.update` add/removeParents —
  revision history preserved via the immutable doc id); a local file moves on
  the filesystem. Legacy folders are already conformant (root artifacts, no
  archive).
- **Submitted-artifact naming** (design D8): résumé/cover are named
  `FirstLast_Resume` / `FirstLast_CoverLetter` from `Applicant.name` (strip
  credentials + punctuation, keep generational suffixes); extension is
  whatever the file actually is.
- Overwrite stays the default. Non-Drive users get a destructive-overwrite
  warning (Drive users are protected by Docs revision history); a checkbox
  opts into archive-instead.
- Dedup: a normalized company+role (contacts: name) signal computed **after**
  parse — always mint, flag possible duplicates, user merges or deletes.
  Merge = re-parent sources/executions, union notes. No runtime special case;
  the `OverwriteConflict` flow generalizes into "same entity detected".
- Contacts: entity id in the profile's existing `.json` sidecar plus an ID
  column on the contacts sheet, so sheet rows join back.
- Archived-execution QoL: per-execution user note ("why we kept this run"),
  purge-archives (global or per entity), and per-execution **lock** to
  protect from purge.
- UI: entity id visible as a small subtitle (short prefix), never the primary
  name.

Explicitly **not** in scope: SQLite as a primary store (permitted later only
as a rebuildable index over the files), re-keying the response cache by
entity (see `model-scoped-cache` for the cache fix), editing
requirements/skills (bleeds into re-assessment), automatic folder renames,
and **decoupling résumé/cover/README generation from Google Docs** (tracked
separately in `provider-agnostic-generation`). The storage adapter here
places and archives whatever artifacts each mode produces today; it does not
re-platform generation.

## Phasing

1. **Identity core** (done): entity_id + `source.json` written at process
   time; run records gain `entity_id`; joins prefer id with name fallback
   (absence = legacy, exactly today's behavior); source-field editing
   (enables URL-attach for autofill); contacts sidecar id + sheet column.
2. **Storage adapter + placement + archive-on-overwrite** (D7/D8): the
   `StorageAdapter` seam with Local/Drive impls, new `gapi/drive`
   `move_to_folder`/`ensure_subfolder`, unify artifact placement into the
   entity folder, archive-on-overwrite (overwrite stays default; opt-out →
   `archive/<ts>`), `FirstLast` naming, exclude `archive/` from the
   completeness count. This materializes the D2 layout the later phases
   assume, so it lands first.
3. **Execution management**: overwrite checkbox + destructive warning,
   promote, per-execution notes, purge + lock, executions-per-entity in the
   Applications table.
4. **Dedup**: normalized signal, duplicate flagging, merge/delete flows;
   explicit re-parse action.

## Capabilities

### New Capabilities

- `application-identity`: the three-tier model, identifiers, layout, dedup,
  and archive management described above.

### Modified Capabilities

- `webapp-ia` (phase 3): the unified Applications table groups executions
  per entity. Exact deltas at spec time.

## Impact

- `jobjob/apply/workflow.py` + `jobjob/enrich/workflow.py`: mint entity ids,
  write `source.json`, place artifacts in the entity folder via the storage
  adapter, archive-on-no-overwrite.
- `jobjob/storage/` (new): `StorageAdapter` Protocol + `LocalStorageAdapter`
  / `DriveStorageAdapter`.
- `jobjob/gapi/drive.py`: new `move_to_folder` / `ensure_subfolder`
  primitives (reparent-by-id for archive/promote).
- `webapp/backend/services/` (tracking, application_metadata, run_history):
  id joins, source read/merge, archive handling, dedup signal.
- `webapp/backend/routers/`: source-edit endpoint, archive/promote/purge/lock
  endpoints.
- `webapp/frontend`: subtitle ids, source editing, duplicate badges,
  executions-per-entity view.
- `tests/`: per phase.
