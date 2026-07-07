# Design – Skills-File Feedback Loop

## Context

Each apply run's ATS assessment computes "skills-file candidates" (evidenced in
the skills analysis but undeclared in `skills.toml`) — but only renders them
into that application's README. The full assessment is not persisted
(`summary.json` keeps only `ats_coverage`), so the signal dies per-application
and the declared skill set drifts behind the documented evidence.

What IS persisted per application: `summary.json` (`job_info`) and
`skills_analysis.json`. The candidate set is derivable from those plus the
packaged skill cloud and the active profile's skills file — no Docs read, no
AI calls.

## Goals / Non-Goals

**Goals:**
- Aggregate evidence-backed, canonical, undeclared skills across all processed
  applications, deduplicated by canonical id, with evidence citations.
- `jobjob skills suggest` prints the aggregation; `--apply <id>...` appends the
  named candidates to the active profile's `skills.toml`, preserving file
  formatting (tomlkit).
- Honesty gate: only canonical, analysis-evidenced, undeclared skills are ever
  suggested or written; nothing is written without an explicit `--apply` list.
- Backend endpoint returning the aggregated suggestions as JSON.

**Non-Goals:**
- No frontend surface (deferred to the webapp restructure).
- No interactive confirmation prompt in v1 — the explicit `--apply` id list is
  the confirmation. (Interactive selection can layer on later.)
- No change to per-application ATS assessment behavior or its README section.
- No removal/pruning suggestions (append-only).

## Decisions

- **Candidate definition — resume presence is irrelevant.** The per-app README
  candidate additionally requires the skill to be absent from the rendered
  resume text. For maintaining the skills file, that filter is noise: an
  evidenced, undeclared skill that happens to appear in one resume is still
  undeclared. Aggregation therefore uses: supported canonical ids (from
  `skills_analysis.json` buckets, resolved via the skill cloud) minus declared
  canonical ids (from the loaded `SkillSet`). This is computable offline and is
  a superset of the README lists.
- **Reuse, not reimplementation.** Promote `_supported_canonical_ids` in
  `jobjob/apply/generate/ats.py` to public `supported_canonical_ids` and import
  it; append via the existing `jobjob.ingest.save.save_skills(..., mode="append")`
  (tomlkit, format-preserving).
- **New entries derive from the canonical cloud entry**: `label` = canonical
  id, `text` = canonical display name, `keywords` = the canonical aliases.
  Deterministic, and `load_skills` re-resolves them to canonical on next load.
- **Scan root** defaults to the configured local applications mirror
  (`applications_output_dir`); `--root` overrides (parity with `jobjob ats`
  taking an explicit directory). Immediate subdirectories containing both
  `summary.json` and `skills_analysis.json` count as processed applications;
  others are skipped silently.
- **CLI shape**: new package `jobjob/skills/` with `suggest.py`; registered as
  `skills` in `jobjob/__main__.py` COMMANDS with an argparse subcommand
  (`jobjob skills suggest`), leaving room for future actions (prune, sync).
- **Endpoint placement**: `GET /skills/suggestions` on the static-content
  router (`/api/static/...`) — suggestions are proposed edits to a content
  TOML, and the router already resolves the active profile's `content/` dir.

## Risks / Trade-offs

- [Aggregated candidates are a superset of README candidates] → documented in
  the report header; the definition (evidenced + canonical + undeclared) is the
  honest one for this purpose.
- [Evidence strings come from per-JD analyses and may read oddly out of
  context] → each citation names its source application directory.
- [`--apply` bypasses interactivity] → the id list must exactly match current
  candidates; unknown or already-declared ids abort with no write.

## Migration Plan

Pure addition — no schema or config changes; no rollback concerns beyond
reverting the commit.

## Open Questions

None blocking. Frontend surface intentionally deferred.
