# ATS Scoring Calibration

> Trilogy follow-up (quantitative-fit #50, ats-assessment #51). **Backlog
> record — blocked on input**: needs a corpus of live applications plus the
> user's expert review; it cannot proceed autonomously.

## Why

Every weight and threshold in the scoring stack is marked PROVISIONAL in the
code and has never been checked against ground truth:

- `jobjob/apply/generate/ats.py`: `WEIGHT_KEY_REQUIREMENT` /
  `WEIGHT_TECHNICAL_SKILL` and the parseability check set.
- `jobjob/apply/generate/readme.py`: `MATCH_WEIGHT_*` bucket weights,
  `MODERATE_GAP_THRESHOLD`, `SUPPORT_RATIO`.

Until calibrated, the absolute numbers (coverage 0.64, role fit 0.72) are
ordering signals at best — the module docstrings say exactly that. Now that
fit/ATS scores drive Dashboard sorting and triage chips (#56, #58), the cost
of misleading absolutes is higher.

## What Changes

- Assemble a calibration corpus: real applications (post-live-run) with the
  persisted `summary.json` fit blocks and ATS assessments, paired with
  expert-reviewed judgments (the user's, and/or external ATS-checker output
  for the same resume/JD pairs).
- Compare computed scores/bands against the reviewed judgments; tune the
  weights/thresholds (possibly per category) and document the rationale next
  to each constant, replacing the PROVISIONAL markers.
- Possibly: a small offline harness (`tests/fixtures` corpus + a notebook or
  script) so recalibration is repeatable when the skill cloud or prompts
  change.

## Input Required — blocked until available

- [ ] **Live-run corpus**: a batch of real applications processed end-to-end
      (the "live run" trilogy item) — the example profile can't calibrate
      real-world scoring.
- [ ] **Expert review**: the user's judgment (or an external ATS tool's
      report) per application: was the band right, was the coverage score
      plausible, which recommendations were wrong?
- [ ] **Target metric**: what does "calibrated" mean here — band agreement
      rate, rank correlation on role fit, or absolute-score tolerance?

## Capabilities

### New Capabilities

<!-- Likely none — expected as MODIFIED deltas on quantitative-fit and
     ats-assessment (documented, non-provisional weights; any harness
     requirement). Confirm at spec time. -->

### Modified Capabilities

- `quantitative-fit`, `ats-assessment`: scoring-constant requirements gain
  calibrated values + provenance.

## Impact

- `jobjob/apply/generate/ats.py`, `jobjob/apply/generate/readme.py`
  (constants + docs), possibly a calibration harness under `tests/` or
  `scripts/`; spec deltas for both scoring capabilities.
