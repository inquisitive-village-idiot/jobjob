# Design: ATS Standalone Check

## Context

`assess_ats` (trilogy, #51) is a pure function; its inputs are all persisted by
the apply workflow: `summary.json` (`job_info` dict incl. canonical proposals,
`resume_id`), `skills_analysis.json`, and the profile skills file. The CLI
dispatcher registers `name -> main(argv)` in `COMMANDS`; the tracking router
already resolves application folders by name (`_resolve_app_folder`).

## Goals / Non-Goals

**Goals:**
- Edit-resume → re-check iteration loop with zero Anthropic calls.
- One shared core (load + reassess + serialize) behind both CLI and endpoint.

**Non-Goals:**
- Frontend UI (deferred to the planned webapp restructure).
- Re-running fit scoring or any generation step.
- Assessing arbitrary docs/JDs not produced by the apply workflow.

## Decisions

### Decision 1: One core module, two thin adapters

`jobjob/apply/recheck.py` owns artifact loading (`load_saved_application`),
reassessment (`reassess_application`), and the stdout report
(`render_ats_report`). The CLI main and the tracking endpoint are adapters:
argument parsing / HTTP mapping only. Serialization for the endpoint is
`dcs.asdict(assessment)` — correct here (unlike the internal freeze path)
because JSON *wants* the nested dataclasses flattened to dicts.

### Decision 2: Reconstruct JobDescription via from_mapping

`summary.json`'s `job_info` is `dcs.asdict(job)` at write time; `from_mapping`
is the existing tolerant inverse (fills gaps, coerces shapes) — no new
parsing code, and older summaries missing `canonical_skills` degrade exactly
like older cached parses do.

### Decision 3: Docs service injected, built lazily

`reassess_application` accepts an injected docs service (tests); the CLI/
endpoint build one via the existing credentials loader only when the summary
has a `resume_id`. Drive-skipped applications short-circuit to a skipped
assessment before touching Google.

### Decision 4: Endpoint lives on the tracking router

Tracking already owns per-application-folder routes and `_resolve_app_folder`
(404 on unknown). `GET .../{folder_name}/ats` fits the existing resource
shape; a new router would fragment it for no benefit. GET is right: the check
mutates nothing.
