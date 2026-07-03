# Tasks: Quantitative Fit Scoring

> Prerequisite: `skill-cloud` change implemented and archived.

## 1. Structure

- [ ] 1.1 Add frozen `FitCategory` dataclass (name, score, note) to `jobjob/structure/fit.py`
- [ ] 1.2 Add `role_fit_categories` / `preference_fit_categories` tuple fields to `Fit` (default empty); update docstring and resolve the TODO

## 2. Role-fit scoring (deterministic)

- [ ] 2.1 Implement match-weight constants (module-level: 1.0 / 0.75 / 0.4 / 0.0) and the category-score computation over the canonical join (weighted by cloud category weights; aspirational + UNMAPPED/non-canonical excluded)
- [ ] 2.2 Compute `Fit.role_fit` as the mean of defined category scores; `None` on zero canonical coverage, with unmapped/non-canonical counts carried for the README; band derivation untouched
- [ ] 2.3 Attach contributing skills (name, bucket, weight) per category for rendering

## 3. Preference-fit (model-judged)

- [ ] 3.1 Extend `jobjob/prompts/skills_analysis.txt`: `preference_fit` block, 3-5 categories `{name, score (0.0-1.0), note}` judged against the background document
- [ ] 3.2 Parse the block tolerantly in `assess_fit()`: skip invalid categories with WARNING; mean over valid; `None` when absent or empty

## 4. Rendering

- [ ] 4.1 `readme_docx.py`: role-fit table (category, score, contributing skills) and preference-fit table (category, score, note) with axis scores, below the band; coverage note when requirements were excluded; omit an axis when `None`; byte-identical section when both `None`

## 5. Tests

- [ ] 5.1 Role fit: reproducibility; hand-computed category scores for a fixture mapping; aspirational/UNMAPPED exclusion; zero-coverage → `None` + counts; band unchanged
- [ ] 5.2 Preference fit: valid block parsed; missing block → `None` + today's behavior; malformed categories skipped with WARNING, all-invalid → `None`
- [ ] 5.3 Rendering: both axes present; one axis `None`; both `None` → current output

## 6. Verify

- [ ] 6.1 Run affected suites (structure, generate, output); confirm green
- [ ] 6.2 Live check: one application end-to-end; eyeball fit tables and coverage note
