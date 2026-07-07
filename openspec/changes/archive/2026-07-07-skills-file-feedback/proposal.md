# Skills-File Feedback Loop

## Why

The README's "skills-file candidates" list (evidenced in STARs/highlights but
undeclared in `skills.toml`) is a dead end: the user reads it, then hand-edits
the TOML — or, realistically, doesn't. Every application recomputes the same
candidates and the declared skill set silently drifts behind the documented
evidence. The user has wanted an "evaluate and auto-update the user-defined
list based on existing content" feature since the trilogy design sessions.

## What Changes

- A candidate-aggregation step: collect skills-file candidates across
  processed applications (each already computed by the ATS assessment),
  deduplicated by canonical id with their evidence citations.
- `jobjob skills suggest` (name TBD at design time): prints the aggregated
  candidates with evidence; `--apply` appends confirmed entries to the active
  profile's `skills.toml` (label/text/keywords derived from the canonical
  cloud entry), preserving file formatting via tomlkit (already a dependency).
- **Honesty gate**: only canonical, analysis-evidenced skills are ever
  suggested; nothing is written without explicit confirmation (interactive
  prompt or `--apply` with a reviewed list). The user's file is never touched
  implicitly — this extends, not weakens, the "skills.toml is the allowlist"
  rule.
- Webapp: a backend endpoint returning the aggregated suggestions (frontend
  surface deferred to the webapp restructure).

## Capabilities

### New Capabilities

- `skills-file-feedback`: Aggregate evidence-backed skills-file candidates and
  append user-confirmed entries to the profile's skills file.

### Modified Capabilities

<!-- ats-assessment spec's "skills-file candidates" requirement may gain a
     delta: candidates become consumable, not just rendered. Assess at spec
     time. -->

## Impact

- New module under `jobjob/` (aggregation + TOML append via tomlkit).
- CLI registration in `jobjob/__main__.py`.
- Backend endpoint (router TBD — likely profiles or static content).
- `tests/`: aggregation, honesty gate, TOML append preserves comments/format.
- Depends on nothing unmerged; #53's recheck module provides per-application
  assessments to aggregate.
