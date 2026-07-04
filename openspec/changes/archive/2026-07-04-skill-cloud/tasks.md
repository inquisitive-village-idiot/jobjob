# Tasks: Skill Cloud

## 1. Licensing & seed data

- [x] 1.1 Verify ESCO reuse/attribution terms; draft the attribution notice to ship alongside the data file
- [x] 1.2 Write the curation script: download an ESCO release, prune to curated branches (technical + transversal), map transversal groups onto the six categories, emit `jobjob/data/skill_cloud.toml`
- [x] 1.3 Generate and commit the initial `skill_cloud.toml` (id, name, aliases, category weights summing to 1.0; source-release metadata + attribution)

## 2. Cloud loader

- [x] 2.1 New structure module: load the packaged TOML; validate unique ids, known categories, weight sums (±0.01); clear errors naming the offending entry
- [x] 2.2 Canonical resolution: case-insensitive name/alias lookup returning canonical id + category weights; exact-label precedence over alias

## 3. JD normalization

- [x] 3.1 Extend the JD-parse prompt(s): propose a canonical skill name per extracted requirement
- [x] 3.2 Resolve proposals in code; carry canonical id + weights on resolved requirements; mark failures `UNMAPPED` with original phrasing
- [x] 3.3 Surface UNMAPPED requirements in the application README

## 4. Profile skill mapping

- [x] 4.1 On skills.toml load, resolve entries via the same lookup; attach canonical id + weights; flag non-canonical at INFO; never modify the user file
- [x] 4.2 Map the bundled example profile's skills to canonical entries (or confirm they exercise the non-canonical path deliberately)

## 5. Tests

- [x] 5.1 Loader: valid cloud loads; bad weights / unknown category / duplicate id fail with named entry
- [x] 5.2 Resolution: name hit, alias hit, case-insensitivity, precedence, miss → None
- [x] 5.3 JD normalization: resolved requirement carries id+weights; unresolvable → UNMAPPED with original phrasing; UNMAPPED reaches the README
- [x] 5.4 Profile mapping: canonical entry enriched; free-form entry unchanged and functional; user file untouched

## 6. Verify

- [x] 6.1 Run affected suites; confirm green
- [x] 6.2 Spot-check: parse one real JD and review canonical ids + UNMAPPED list for sanity
