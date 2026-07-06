# Design: Skill Cloud

## Context

JD requirements and profile skills are matched per-application by keywords plus
model judgment; nothing canonicalizes either side, so matches (and scores built on
them) are not comparable across applications. `content/skills.toml` already gives
user skills labels + keywords; `jobjob/prompts/` establishes the pattern for
data packaged with the wheel.

## Goals / Non-Goals

**Goals:**
- Canonical, versioned, package-internal skill taxonomy mimicking ATS skill clouds.
- Deterministic JD-skill ↔ user-skill matching via a join on canonical ids.
- Fixed, cloud-defined category vocabulary with weighted membership.
- Low-maintenance: re-sync against upstream releases is rare and intentional.

**Non-Goals:**
- Skill recommendations from resume/STARs (future change).
- Static Content UI for canonical mapping (future change).
- Continuous/automatic upstream sync or web scraping.
- Per-skill proficiency ratings (unanchored self-assessment conflicts with the
  honesty layer; evidence checks stay per-application).

## Decisions

### Decision 1: Seed from ESCO

ESCO over O*NET and Lightcast: it is skills-first with a broader/narrower hierarchy
(curate granularity by picking tree depth), versioned major releases (regen is a
rare, deliberate re-sync), multilingual (useful for EU applications), and licensed
for free reuse with attribution — redistributable inside the wheel with a notice.
O*NET is occupation-first (high reshaping cost); Lightcast is JD-native but
continuously churning and vendor-controlled. Verify exact reuse terms during
implementation and bundle the attribution notice with the data file.

### Decision 2: Fixed six-category vocabulary, weighted membership

Categories: communication, collaboration, leadership, creativity, technical,
domain. Rationale: managerial framings ship collaboration+teamwork as near
duplicates (merged here) and let "technical" become a mega-bucket for IC roles
(split: `technical` = craft/tools/methods, `domain` = field knowledge). Skills may
belong to multiple categories with weights summing to 1.0, so a multi-category
skill contributes fractionally instead of multiply. The vocabulary is defined by
the cloud (versioned with jobjob), not by users — users define skills, which
inherit categories through canonical mapping. ESCO's transversal-skill groups seed
the initial weights; curation adjusts.

### Decision 3: Model proposes, code resolves

The cloud (~thousands of entries after curation) cannot be inlined into prompts.
Normalization is split: the model proposes a canonical name per JD requirement
(cheap — one field per requirement); code resolves the proposal against
name/alias lookup. Resolution failures become `UNMAPPED`, never a silent nearest
match — consistent with the honesty layer (a gap is flagged, not bridged) and
doubling as the taxonomy-maintenance signal.

### Decision 4: Curation script, committed output

A script downloads an ESCO release, prunes to curated branches, maps transversal
groups onto the six categories, and emits `jobjob/data/skill_cloud.toml`. The
generated TOML is committed and shipped; the script is tooling, not a runtime
dependency. Regeneration = run script against a new release, review the diff.

## Open Questions

- Curated size target: enough leaf coverage for real JDs without bloating alias
  lookup; start with ESCO's technical + transversal branches and iterate.
- Whether `label` collisions between skills.toml entries and cloud aliases need a
  precedence rule (likely: exact label match wins, then alias).

## Notes from implementation

- **Per-root budgets, not a single global cap.** The first generation let S1
  (communication) consume the entire budget in traversal order — 1600 entries,
  zero technical skills, `Python` unresolvable. Each root now carries its own
  entry budget (S5 500, K 500, S1 300, S4 200, S2/transversal 150) with the
  global cap as a safety net, technical branches traversed first.
- **en-us preferred labels are aliases.** ESCO's `en` label is often the
  parenthesized form ("Python (computer programming)"); the plain form JDs use
  ("Python") is the `en-us` preferred label, so it is folded into aliases.
- The bundled demo persona's journalism skills split 5/12 canonical — the rest
  exercise the free-form path deliberately.
- **Keyword-based profile resolution is loose.** Exact string matching on
  keywords can over-resolve semantically (`embargo_management` → `journalism`
  via the keyword "press"). Label/text matching is precise; keywords are the
  fallback. If over-resolution bites, restrict profile resolution to
  label/text — revisit after real use.
- **Skills outside the group hierarchy need seeding.** Some high-value ESCO
  skills (e.g. `project management`) have no broader group and are unreachable
  by tree traversal; the script maintains a seed list (searched directly) and a
  curated-alias table for JD-common terms ESCO lacks (e.g. "machine learning"
  → data mining).
