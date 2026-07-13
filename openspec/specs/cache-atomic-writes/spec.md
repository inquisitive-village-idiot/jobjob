# cache-atomic-writes Specification

## Purpose
TBD - created by archiving change atomic-cache-writes. Update Purpose after archive.
## Requirements
### Requirement: Cache entries are complete-or-absent

`CacheManager.save_to_cache()` SHALL write each cache entry atomically: content is
written to a uniquely-named temporary file inside the cache directory and then moved
onto the final `{key}.json` path via `os.replace()`. A reader SHALL never observe a
partially written cache entry at the final path.

#### Scenario: Successful save is atomic

- **WHEN** `save_to_cache(prompt, response)` completes
- **THEN** the final `{key}.json` file contains the complete JSON payload
- **AND** no temporary file remains in the cache directory

#### Scenario: Concurrent writers to the same key

- **WHEN** two writers save an entry for the same prompt concurrently
- **THEN** each writes to its own uniquely-named temporary file
- **AND** the final path always contains one complete, valid entry (last replace wins)

### Requirement: Failed writes leave no partial entry

If an error occurs before the atomic replace, the system SHALL NOT create or modify
the final cache path, and SHALL remove the temporary file on a best-effort basis.
Partial temporary files MUST NOT be resumed or recovered — the recovery path is a
cache miss followed by a fresh save with a new temporary file.

#### Scenario: Write fails mid-save

- **WHEN** an exception is raised while writing the temporary file
- **THEN** the final `{key}.json` path is unchanged (absent, or the prior valid entry)
- **AND** the temporary file is removed
- **AND** the exception propagates to the caller

#### Scenario: Orphaned temp file after hard kill

- **WHEN** a `.tmp` file remains in the cache directory (e.g., process killed before cleanup)
- **THEN** `load_from_cache()` ignores it (readers resolve only exact `{key}.json` paths)
- **AND** `purge_cache()` removes it along with other cache files

### Requirement: Cache keys are scoped by model

`CacheManager` SHALL compose each entry's key from both the prompt and the
model identifier, so that the same prompt requested under two different models
resolves to two distinct entries. The model is an optional dimension: when no
model is supplied the key is derived from the prompt together with an absent
model, forming a namespace distinct from any real model id.

`load_from_cache`, `save_to_cache`, and `delete_cache_entry` SHALL accept the
model as an optional argument and derive the key consistently, so a save under
model M is retrievable only by a load under model M.

#### Scenario: Same prompt, two models, two entries

- **WHEN** `save_to_cache(prompt, response_a, model="model-a")` and
  `save_to_cache(prompt, response_b, model="model-b")` are both called
- **THEN** `load_from_cache(prompt, model="model-a")` returns `response_a`
- **AND** `load_from_cache(prompt, model="model-b")` returns `response_b`

#### Scenario: Configured model re-run hits its own entry

- **WHEN** an entry is saved under a given model
- **AND** the same prompt is later loaded under that same model
- **THEN** the cached response is returned (a hit)

#### Scenario: Absent model is its own namespace

- **WHEN** `save_to_cache(prompt, response)` is called with no model
- **THEN** `load_from_cache(prompt)` with no model returns `response`
- **AND** `load_from_cache(prompt, model="model-a")` is a miss

### Requirement: A per-run model override caches under that model

When a run supplies a per-run model override, the response cache SHALL remain
active and be keyed by the override model, rather than being bypassed. Two runs
of the same prompt under the same override model SHALL hit the cache on the
second run.

#### Scenario: Override run is cacheable

- **WHEN** an apply run is launched with a per-run model override and caching enabled
- **AND** the same prompt is run twice under that override
- **THEN** the second run is served from the cache entry keyed by the override model

