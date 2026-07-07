# Tasks: ATS Standalone Check

## 1. Core

- [x] 1.1 `jobjob/apply/recheck.py`: `load_saved_application(output_dir)` — job via `from_mapping` from `summary.json` `job_info`, skills from `skills_analysis.json`, `resume_id`; clear errors naming missing files
- [x] 1.2 `reassess_application(output_dir, *, docs_service=None, logger=None)` — skipped assessment when no `resume_id`; otherwise one `get_document` + `assess_ats` with `load_skills()`; zero Anthropic calls
- [x] 1.3 `render_ats_report(assessment)` — plain-text report: coverage, buckets, recommendations, candidates, up-skill targets, parseability, fit-vs-ATS gaps; skipped variant

## 2. CLI

- [x] 2.1 `parse_args` + `main(argv)` in recheck.py; register `"ats"` in `jobjob/__main__.py` `COMMANDS`; exit 0 incl. skipped, nonzero + message on missing artifacts

## 3. Webapp

- [x] 3.1 `GET /api/tracking/applications/{folder_name}/ats` on the tracking router — `_resolve_app_folder` (404), `dcs.asdict` serialization, 4xx with detail on missing artifacts

## 4. Tests

- [x] 4.1 Core: round-trip from fixture summary/skills files; skipped (no resume_id); missing-file errors; injected fake docs service; no AI client anywhere
- [x] 4.2 Report: sections present; skipped variant
- [x] 4.3 CLI: exit codes and stdout via main(argv)
- [x] 4.4 Endpoint: 200 shape, 404 unknown folder, 4xx missing artifacts

## 5. Verify

- [x] 5.1 Full suite green; lint clean; run pytest as its own command before any push
