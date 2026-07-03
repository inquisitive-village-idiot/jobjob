# Skill Cloud

## Why

Every application re-does fuzzy matching between JD phrasing and the user's
`skills.toml` phrasing (keywords + per-run model judgment), so match results and any
scores derived from them are not comparable across applications. Commercial ATSes
solve this with a proprietary canonical skill taxonomy; jobjob needs its own,
packaged with the library, so both JD requirements and user skills normalize onto
canonical ids and matching becomes a deterministic join.

## What Changes

- A canonical skill taxonomy ("skill cloud") ships inside the package (TOML, same
  pattern as `jobjob/prompts/`): canonical id, name, aliases, and weighted category
  membership. Seeded from **ESCO** (skills-first, hierarchical, versioned releases,
  reuse-with-attribution licensing), curated down to relevant branches.
- Fixed category vocabulary, defined by the cloud: `communication`, `collaboration`,
  `leadership`, `creativity`, `technical`, `domain`. Skills may belong to multiple
  categories; weights sum to 1 per skill. ESCO's transversal-skill groups seed the
  weights.
- JD parsing normalizes extracted requirements onto canonical ids: the model
  proposes a canonical match per requirement; code resolves the proposal against
  the cloud's names/aliases. Unresolvable requirements are preserved as `UNMAPPED`
  (signal: either a real gap or a taxonomy hole).
- Profile `skills.toml` entries map to canonical ids the same way; free-form
  (non-canonical) entries remain allowed and are flagged.
- A curation/sync script regenerates the packaged cloud from an ESCO release —
  re-sync is an intentional, versioned event, not continuous scraping.

Deferred (future changes): skill recommendations from resume/STARs; Static Content
UI for canonical mapping; upstream auto-sync.

## Capabilities

### New Capabilities

- `skill-cloud`: Packaged canonical skill taxonomy with weighted categories, plus
  normalization of JD requirements and profile skills onto canonical ids.

### Modified Capabilities

<!-- None — existing matching keeps working for non-canonical entries. -->

## Impact

- `jobjob/data/skill_cloud.toml` (new): packaged taxonomy + ESCO attribution notice.
- `jobjob/structure/` (new module): cloud loader, canonical-id resolution
  (name/alias lookup), category weights.
- `jobjob/prompts/job_description*.txt`: JD parse additionally proposes canonical
  skill names per requirement.
- `jobjob/loaders/` (skills.toml loading): resolve entries to canonical ids; flag
  non-canonical.
- `scripts/` (new): ESCO download/curate/regenerate script.
- Downstream: the `quantitative-fit-scoring` change consumes the canonical join for
  deterministic role-fit scoring. **That change depends on this one.**
- Licensing: verify ESCO reuse terms; include attribution in the package.
