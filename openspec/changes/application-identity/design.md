# Design – Application Identity

All decisions below were settled in the 2026-07-07 explore session
(user + assistant); this document is the record. Remaining work at
implementation time is specs/tasks detail, not direction.

## Context

Identity today is "whichever string is handy": input path while queued,
folder name once built, a different folder name after a user rename (the
status-prefix parser supports renames on purpose). Everything stored *inside*
a folder travels through renames fine; every cross-reference *by name* (run
records, Drive web-link match, rerun JD lookup) silently goes stale. The
queued→built transition has no identity continuity at all.

## Goals / Non-Goals

**Goals:** stable identity across the whole lifecycle; parse results that
survive re-execution and user correction; non-intrusive multi-execution
support; one dedup mechanism; files remain the source of truth.

**Non-Goals:** SQLite as primary store; automatic folder renames; editing
analysis outputs; entity-keyed response caching; changing the Drive folder
naming convention.

## Decisions

### D1 — Three tiers: Entity / Source / Execution

```
ENTITY      uuid4; no artifacts — connective tissue     owns: status, notes, dedup links
  │                                                     home: metadata.json (recognized, not moved)
SOURCE(s)   the posting/profile itself                  owns: file/web URIs, external_ref,
  │         parse-once fields + user corrections              company, role, description
  │                                                     home: source.json (new, entity folder root)
EXECUTION(s) one build/enrich/autofill run              owns: artifacts, summary.json, run record
                                                        key: run_id (exists since #58) + entity_id
```

Rationale: the model was designed to fix dedup timing (you cannot ask
"duplicate?" before parse, and by then an id exists) and incidentally
dissolved two other problems — re-parse clobbering of user edits (parse
fields are source-tier, written once; executions read them) and the
"which folder owns the status" ambiguity (status was always entity-level:
you applied to the job, not to execution #3).

- **Natural keys are attributes, never keys**: a JD-embedded requisition id
  is stored as `external_ref`; the key is always our uuid4. Mixed id
  namespaces would make every consumer handle both formats and risk
  cross-company collisions.
- **Parse-once**: first processing writes the source fields; later
  executions read them. Re-parse is an explicit user action with an
  overwrite warning — its only remaining purpose is picking up prompt
  improvements.
- **Editable source fields**: company, role, web URI, external_ref only —
  corrections for parse errors, not analysis edits. An edit recomputes the
  dedup signal.
- **Unprocessed files have no identity**: the input dir is a mixed drop zone
  (JDs or contacts; classified at process time). URL ingests are processed
  immediately, so the web URI is known at mint time; PDF drops attach a URL
  later via source editing.

### D2 — Physical layout: entity folder, primary at root, archive below

```
2026-07-02 - Beta - Director/          ← entity folder: named exactly as today
  metadata.json                        ← entity tier (one copy — no duplication problem)
  source.json                          ← source tier
  Resume.pdf … README.docx summary.json← PRIMARY execution's artifacts, at root, as today
  archive/2026-07-05T09.12.03/         ← only exists after an opt-out-of-overwrite build
    Resume.pdf … summary.json          ← complete, self-contained superseded execution
```

- Root = primary, **always**; "which one do I want" is answered by location,
  never memory. Default (overwrite on) is byte-for-byte today's flow — no
  `archive/`, no timestamps anywhere.
- Rejected alternatives: raw per-execution folders (timestamps become the
  browsed name — user-hostile; changes the Drive convention); symlinks (not
  OS-agnostic, not Drive-safe); mutual metadata cross-references (touch every
  sibling per execution — write amplification into a syncing mirror);
  tracker.json pointer files (path pointers break on rename — the exact
  fragility ids exist to kill); nested executions inside one summary.json
  (unbounded file growth, whole-array rewrites, every consumer must index in).
- One `summary.json` per execution, in its execution's location — the
  primary designation your nested-schema idea wanted comes free from
  location addressing.
- **Promote** (make an archived execution primary): archive the current root
  artifacts *first*, then move the promoted execution's files to root —
  strictly in that order, so no collision/overwrite window exists.
- Archive dirs are named by timestamp (seconds resolution, human-facing);
  the machine join is the `run_id` inside each `summary.json`. Never
  archive-within-archive.
- `archive/` is excluded from the artifact-completeness count (same carve-out
  `metadata.json` gets today).
- Tradeoff accepted: copying a single archived execution elsewhere does not
  carry status/notes — semantically correct, since those are entity-tier.

### D3 — Dedup: always mint, flag after parse, user resolves

Normalized company+role (contacts: first+last name) as the duplicate
*signal* — normalization (casefold, whitespace, common abbreviations) is the
substance; any hash of it is just a compact key, derived and never stored as
truth. Possible duplicates are flagged in the UI; the user merges (re-parent
sources + executions to the surviving entity, union notes) or deletes.
No launch-time prompt — parse hasn't happened yet at launch. The existing
`OverwriteConflict` same-folder check generalizes into this flow.

### D4 — Legacy: absence is the stamp

ID-less folders are legacy: they join by name exactly as today (benign
degradation preserved), and gain `entity_id`/`source.json` lazily on their
next natural write. No backfill, no mirror rewrite — same policy as the
`full-build-rename` shim, and this rides the same `schema_version` shape as
its v1→v2 step. Legacy folders are *already* layout-conformant (root
artifacts, no archive).

### D5 — Overwrite semantics

Overwrite remains the default. Drive mode is already non-destructive (Docs
revision history); non-Drive users see a destructive warning with an
"archive instead" opt-out. Archived executions support: a small user note
("why we kept this run"), purge (global or per-entity), and a per-execution
**lock** that exempts it from purge.

### D6 — SQLite only ever as a rebuildable index

The folder is the database: it syncs, restores, and survives user handling.
Any SQLite index must be derivable by scanning the mirror (drop + rescan =
identical). Not needed for phase 1 — the existing scan+cache carries current
scale.

## Risks / Trade-offs

- [Dedup signal is weak to naming variance] → it's a flag for a human, never
  an auto-merge.
- [source.json is a new file users could hand-edit badly] → tolerant read
  (same posture as metadata.json), parse errors degrade to legacy behavior.
- [Two executions racing on one entity folder] → single-user app; the jobs
  framework already serializes per-launch; archive-move happens inside the
  workflow step.

## Migration Plan

None required (D4). Rollback = revert; new fields are ignored by old code
(metadata round-trips unknown keys already).

## Open Questions

None blocking. Per-execution note storage (field in the archived
`summary.json` vs. tiny sidecar) is a spec-time detail.
