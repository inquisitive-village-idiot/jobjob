# Quantitative Fit Scoring

> **Depends on:** the `skill-cloud` change (canonical skill taxonomy + JD/profile
> normalization). Implement that first.

## Why

The per-application README shows only a qualitative fit band (Strong/Moderate/Weak)
with a one-line summary. The TODO at `jobjob/structure/fit.py:19` calls for a
quantitative two-axis fit — (1) how well the candidate fits the role and (2) how
well the role fits what the applicant is looking for — each broken into scored
categories. With the skill cloud in place, role fit can be computed deterministically
from the canonical skill join, making scores traceable and comparable across
applications (a usable batch-triage sort key, not decoration).

## What Changes

- **Role fit is computed, not judged**: category scores are arithmetic over the
  skills-analysis buckets (supported/gap × severity), grouped by the canonical
  cloud's category weights. The README can show exactly which skills moved each
  number.
- **Preference fit stays model-judged**: the skills-analysis call additionally
  returns preference-fit categories `{name, score, note}` judged against the
  background document (no structured preference data exists). No new API call.
- `Fit` gains structured category tuples; the placeholder `role_fit` /
  `preference_fit` floats (0.0-1.0) are populated (weight-aware means).
- The README DOCX renders both axes: role-fit categories with contributing skills,
  preference-fit categories with notes — below the existing band line.
- The qualitative band derivation stays deterministic and unchanged; scores are
  additive, never a replacement. Role-fit scores derive from the same evidence as
  the band, so they cannot incoherently contradict it.
- Older cached analyses and UNMAPPED-heavy or non-canonical-heavy matches degrade
  gracefully (scores `None` or computed over the canonical subset, stated in the
  README).

## Capabilities

### New Capabilities

- `quantitative-fit`: Two-axis, category-scored fit assessment — deterministic role
  axis over the canonical skill join; model-judged preference axis — rendered in
  the application README.

### Modified Capabilities

<!-- None — existing band/summary behavior is unchanged; this is additive. -->

## Impact

- `jobjob/structure/fit.py`: `FitCategory`; category tuples on `Fit`; axis scores.
- `jobjob/apply/generate/readme.py`: deterministic role-fit computation from the
  canonical join; parsing of the model's preference-fit block.
- `jobjob/prompts/skills_analysis.txt`: preference-fit block only (role fit needs
  no prompt change).
- `jobjob/apply/output/readme_docx.py`: two-axis rendering.
- `tests/`: scoring arithmetic, degradation paths, rendering.
- No new dependencies; no new API calls.
