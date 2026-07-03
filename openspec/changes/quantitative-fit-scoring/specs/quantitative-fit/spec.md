# Quantitative Fit

## ADDED Requirements

### Requirement: Role fit is computed deterministically from the canonical join

Role-fit category scores SHALL be computed in code from the skills-analysis
classification (supported vs gap × severity) and the skill cloud's category
weights — never model-judged. Given the same skills mapping and cloud version, the
scores MUST be identical across runs. Match weights: critical_supported 1.0,
important_supported 0.75, stretch gap 0.4, blocking gap 0.0; aspirational gaps and
UNMAPPED/non-canonical requirements are excluded from scoring. Category score is
the match-weighted mean over that category's requirements; `Fit.role_fit` is the
mean of defined category scores.

#### Scenario: Reproducible role-fit scores

- **WHEN** the same skills mapping is scored twice against the same skill cloud
- **THEN** all role-fit category scores and the axis score are identical

#### Scenario: Category scores trace to skills

- **WHEN** a role-fit category score is computed
- **THEN** each contributing requirement's canonical skill, bucket, and match
  weight are available for rendering
- **AND** the qualitative band for the same mapping is unchanged from current
  behavior

#### Scenario: Insufficient canonical coverage

- **WHEN** no scoring requirement resolves to a canonical skill
- **THEN** `Fit.role_fit` is `None`
- **AND** the README states how many requirements were unmapped or non-canonical

### Requirement: Preference fit is model-judged against the background document

The skills-analysis call SHALL additionally return a `preference_fit` block of 3-5
categories `{name, score, note}` with scores in [0.0, 1.0], judged against the
applicant's background document. `Fit.preference_fit` SHALL be the mean of valid
category scores. No additional API call may be introduced for this.

#### Scenario: Preference block parsed

- **WHEN** the analysis contains a valid `preference_fit` block
- **THEN** `Fit.preference_fit_categories` holds the categories and
  `Fit.preference_fit` equals their mean

#### Scenario: Missing preference block degrades gracefully

- **WHEN** the analysis lacks a `preference_fit` block (e.g., older cached result)
- **THEN** `Fit.preference_fit` is `None` and the category tuple is empty
- **AND** band, summary, strengths, and weaknesses are produced as today

#### Scenario: Malformed preference categories are tolerated

- **WHEN** a preference category has a missing, non-numeric, or out-of-range score
- **THEN** it is skipped with a WARNING log
- **AND** the axis mean covers the remaining valid categories, or `None` if none

### Requirement: README renders the two-axis fit

The application README SHALL render, below the existing band line: the role-fit
axis (per-category score with contributing skills) and the preference-fit axis
(per-category score with note), each with its axis score. An axis whose score is
`None` SHALL be omitted, and with both axes `None` the README MUST be identical to
current output.

#### Scenario: README with both axes

- **WHEN** role fit and preference fit are both available
- **THEN** the DOCX contains the band line, a role-fit table with contributing
  skills per category, and a preference-fit table with notes, plus both axis scores

#### Scenario: README without quantitative fit

- **WHEN** neither axis has a score
- **THEN** the DOCX contains the band, summary, and strengths/weaknesses table
  unchanged from current behavior
