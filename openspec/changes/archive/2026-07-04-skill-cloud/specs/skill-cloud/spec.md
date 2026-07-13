# Skill Cloud

## ADDED Requirements

### Requirement: Packaged canonical skill taxonomy

jobjob SHALL ship a canonical skill taxonomy as package data (TOML). Each entry
SHALL have a stable canonical id, a display name, a list of aliases, and weighted
category membership over the fixed vocabulary {communication, collaboration,
leadership, creativity, technical, domain}. Category weights per skill MUST sum to
1.0 (±0.01). The file SHALL record its source (ESCO release version) and carry the
required attribution.

#### Scenario: Cloud loads and validates

- **WHEN** the skill cloud is loaded
- **THEN** every entry has a unique canonical id, a name, and category weights over
  the fixed vocabulary summing to 1.0
- **AND** the taxonomy metadata records the ESCO release it was curated from

#### Scenario: Invalid cloud entry is rejected at load

- **WHEN** an entry has weights that do not sum to 1.0 or an unknown category
- **THEN** loading fails with a clear validation error naming the entry

### Requirement: JD requirements normalize to canonical ids

JD parsing SHALL propose a canonical skill match for each extracted requirement;
code SHALL resolve proposals against the cloud's names and aliases
(case-insensitive). A requirement whose proposal does not resolve SHALL be
preserved as `UNMAPPED` with its original phrasing — it MUST NOT be dropped or
silently bridged to a near match.

#### Scenario: Requirement resolves via alias

- **WHEN** a JD requirement's proposed match equals a cloud entry's name or alias
- **THEN** the requirement carries that entry's canonical id and category weights

#### Scenario: Unresolvable requirement is preserved

- **WHEN** the model's proposed match resolves to no cloud entry
- **THEN** the requirement is marked `UNMAPPED` and keeps its original JD phrasing
- **AND** UNMAPPED requirements are surfaced in the application README

### Requirement: Profile skills map to canonical ids

Profile `skills.toml` entries SHALL be resolved to canonical ids by the same
name/alias lookup. Entries that do not resolve SHALL remain usable as free-form
skills and be flagged as non-canonical (logged at INFO; surfaced where profile
content is reviewed). Resolution MUST NOT modify the user's file.

#### Scenario: User skill resolves to the cloud

- **WHEN** a skills.toml entry's label, text, or keyword matches a cloud entry
- **THEN** the loaded skill carries the canonical id and category weights

#### Scenario: Free-form user skill still works

- **WHEN** a skills.toml entry resolves to no cloud entry
- **THEN** it is loaded and matched as today (keywords), flagged non-canonical
- **AND** the user's file is unchanged
