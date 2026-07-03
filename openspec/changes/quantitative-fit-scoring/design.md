# Design: Quantitative Fit Scoring

## Context

`assess_fit()` (`jobjob/apply/generate/readme.py`) deterministically derives a
qualitative band from the skills-analysis JSON (severity-weighted gaps vs supported
skills). `Fit` (`jobjob/structure/fit.py`) reserves `role_fit` / `preference_fit`
as `Optional[float]` placeholders. The `skill-cloud` change (prerequisite) gives
every JD requirement and profile skill a canonical id plus weighted membership in
six categories (communication, collaboration, leadership, creativity, technical,
domain), and preserves unresolvable requirements as UNMAPPED.

## Goals / Non-Goals

**Goals:**
- Role-fit scores that are traceable (arithmetic over listed evidence) and
  comparable across applications.
- Preference-fit judgment without new API calls.
- Full backward compatibility (older cached analyses, non-canonical skills).

**Non-Goals:**
- Changing the qualitative band derivation.
- Structured applicant-preference config (`preferences.toml` is future work; the
  background doc is the preference source).
- Using fit scores to gate or rank applications automatically.

## Decisions

### Decision 1: Hybrid axes — deterministic role fit, model-judged preference fit

The skills analysis already classifies each requirement (supported vs gap ×
severity), and the skill cloud supplies category weights per requirement. That is
every input role-fit needs; having the model also emit holistic category scores
would add an opinion that can silently disagree with the evidence lists rendered in
the same README. Preference fit has no structured input — "what the applicant
wants" is prose in `background.*` — so that axis is model judgment by necessity.
The asymmetry is honest: one axis is measurement, the other is assessment, and the
README should present them as such.

### Decision 2: Role-fit arithmetic

Per requirement r with match weight m(r):

- `critical_supported` → m = 1.0
- `important_supported` → m = 0.75
- gap, severity `stretch` → m = 0.4
- gap, severity `aspirational` → excluded from scoring (listed only)
- gap, severity `blocking` → m = 0.0
- UNMAPPED / non-canonical → excluded from category scores (no category weights);
  counted in a coverage note

Category score = Σ m(r)·w(r, category) / Σ w(r, category) over scoring
requirements — the sum-to-1 category split cancels in this ratio, so splitting
never deflates a category score; it only sets each skill's relative influence
within the category. Axis score = mass-weighted mean of category scores
(= total matched mass / total mass), so a category whose entire denominator is
one 0.2-weight sliver cannot drag the axis as hard as a category backed by many
full-weight skills. Constants are module-level (tunable, visible), mirroring
`MODERATE_GAP_THRESHOLD` / `SUPPORT_RATIO` style. The band remains derived by the
existing rules; band and score share inputs, so disagreement is bounded and
explainable.

### Decision 3: Preference-fit block in the skills-analysis response

The prompt gains a `preference_fit` output: 3-5 categories `{name, score
(0.0-1.0), note}` judged against the background document. Reuses the cached
context prefix — zero new calls. Category names on this axis are model-chosen
(role type, domain interest, location, growth, etc.) because preference structure
varies per applicant; they are labels for judgment, not taxonomy.

### Decision 4: Tolerant parsing and graceful degradation

- No `fit`/`preference_fit` block (older cached analyses) → preference axis `None`.
- Malformed preference category (missing/non-numeric/out-of-range score) → skipped
  with WARNING; axis mean over the remainder; all invalid → `None`.
- Role axis with zero canonical scoring requirements → `None` with a coverage note
  in the README ("n of m requirements unmapped/non-canonical").
- README renders exactly as today whenever an axis is `None`.

### Decision 5: `FitCategory` as a frozen dataclass

`Fit` gains `role_fit_categories` / `preference_fit_categories` tuples of frozen
`FitCategory(name, score, note)` (default empty), matching the immutability style
of `jobjob/structure/`. Role-fit categories carry, in `note`, the contributing
skill names so the DOCX table shows the "why" per row.
