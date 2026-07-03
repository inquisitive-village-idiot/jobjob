# Tasks: ATS Assessment

> Prerequisite: `skill-cloud` implemented. Fit-vs-ATS gap rendering additionally
> needs `quantitative-fit-scoring`.

## 1. Coverage scoring

- [ ] 1.1 New module: classify each canonical JD requirement against resume text (present / missing-evidenced / missing-unevidenced; word-boundary, case-insensitive name+alias matching); UNMAPPED listed, unscored
- [ ] 1.2 Coverage score weighted by criticality (reuse fit-scoring constants); deterministic; all tunables as documented module-level constants in one place

## 2. Document acquisition

- [ ] 2.1 Fetch the updated resume doc once via `gapi/docs.py` (`get_document`); derive text (`extract_doc_text`) and structure from the same response
- [ ] 2.2 Handle Drive-skipped runs: assessment marked skipped, README says so

## 3. Parseability checks

- [ ] 3.1 Implement the named check set over doc structure: body content in tables, non-standard section headings, images/text boxes, multi-column layout; pass/warn + one-line reason each

## 4. Recommendations

- [ ] 4.1 Derive recommendations from missing-evidenced ∩ skills-file entries only; each cites its evidence from the skills analysis; no generated resume copy; unevidenced or undeclared skills never recommended
- [ ] 4.2 Derive README-only side lists: skills-file candidates (evidenced, undeclared) and up-skill targets (missing-unevidenced); assert neither reaches generation inputs

## 5. Rendering

- [ ] 5.1 README "ATS assessment" section: coverage score, bucket lists, parseability results, recommendations, skills-file candidates, up-skill targets
- [ ] 5.2 Fit-vs-ATS gap list when role-fit data is available (skills strong on fit axis, absent from resume text)

## 6. Tests

- [ ] 6.1 Coverage: alias hit, word-boundary behavior, bucket classification, determinism, UNMAPPED exclusion
- [ ] 6.2 Recommendations: evidence citation present; unevidenced never recommended
- [ ] 6.3 Parseability: fixture docs triggering each warning; clean doc passes
- [ ] 6.4 Rendering: full section; Drive-skipped section; gap list with/without fit data

## 7. Calibration & verify

- [ ] 7.1 Compare output against prior LLM-based ATS assessments and expert feedback; tune constants (weights, thresholds, check set) and record rationale in code comments
- [ ] 7.2 Run affected suites; live check one application end-to-end
