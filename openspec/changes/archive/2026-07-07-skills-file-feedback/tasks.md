# Tasks: Skills-File Feedback Loop

## 1. Aggregation module

- [x] 1.1 Promote `_supported_canonical_ids` to public `supported_canonical_ids` in `jobjob/apply/generate/ats.py` (update internal callers)
- [x] 1.2 Create `jobjob/skills/suggest.py`: `SkillSuggestion` structure, application-directory scan, `aggregate_candidates()` (evidenced + canonical + undeclared, deduped by canonical id, evidence citations)

## 2. CLI

- [x] 2.1 Add `suggest` CLI (`parse_args` with subcommand, report rendering, `--root`, `--apply` with honesty-gate validation, append via `ingest.save.save_skills(mode="append")`)
- [x] 2.2 Register `skills` in `jobjob/__main__.py` COMMANDS

## 3. Webapp endpoint

- [x] 3.1 Add `GET /skills/suggestions` to `webapp/backend/routers/static_content.py` returning aggregated suggestions; 400 when no applications mirror is configured

## 4. Tests

- [x] 4.1 Aggregation: dedupe across apps, declared exclusion, non-canonical skip, incomplete-directory skip
- [x] 4.2 Apply path: appended entry derives from cloud entry; formatting/comments preserved; invalid id aborts without write; no write without `--apply`
- [x] 4.3 Endpoint: suggestions JSON; unconfigured mirror → 400

## 5. Verify

- [x] 5.1 Full pytest run green
