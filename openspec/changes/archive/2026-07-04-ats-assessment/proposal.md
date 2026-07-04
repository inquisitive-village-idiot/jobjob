# ATS Assessment

> **Depends on:** the `skill-cloud` change (hard — canonical ids). Pairs with
> `quantitative-fit-scoring` (soft — the fit-vs-ATS gap signal needs both).

## Why

Fit scoring answers "should I apply?" by matching the JD against the applicant's
*full documented experience*. Neither it nor anything else answers "will the
generated resume survive the machine screen?" — the ATS question, matched against
*what actually made it into the resume text*. A skill that is well-evidenced in
STARs but absent from the rendered resume is a fit strength and an ATS miss at the
same time; that gap is invisible today and directly actionable.

## What Changes

- **Keyword/skill coverage**: the generated resume's text is scored against the
  JD's canonical skills — present, missing-but-evidenced, missing-and-unevidenced.
  Deterministic over the canonical join (same foundation as role fit).
- **Parseability checks**: heuristics on the resume document structure (tables,
  unusual headings, layout patterns known to break ATS parsers). Largely
  template-level; reported per application.
- **Fix recommendations**: actionable suggestions to close coverage gaps,
  restricted to **evidenced skills only** (honesty layer — this must never become
  a keyword-stuffing tool). E.g., "Python is supported in your STARs but absent
  from the resume text."
- Results render as an "ATS assessment" section in the application README,
  including the fit-vs-ATS gap list when role-fit data is available.
- Heuristic weights and thresholds are configurable constants, **explicitly
  provisional**: calibration against prior LLM-based ATS assessments and expert
  feedback is an in-scope task, and settings should be easy to tweak without code
  archaeology.

## Capabilities

### New Capabilities

- `ats-assessment`: Coverage scoring, parseability checks, and evidence-bounded
  fix recommendations for the generated resume, rendered in the application README.

### Modified Capabilities

<!-- None — additive. -->

## Impact

- `jobjob/apply/` (new module): coverage scoring, parseability heuristics,
  recommendation derivation.
- Resume text acquisition: read the updated Google Doc body via the existing
  `gapi` layer (design decision — see design.md).
- `jobjob/apply/generate/readme.py` + `output/readme_docx.py`: ATS section.
- `tests/`: coverage arithmetic, evidence-bounding of recommendations,
  parseability heuristics, rendering.
- No new API calls to Anthropic; one additional Docs/Drive read per application.
