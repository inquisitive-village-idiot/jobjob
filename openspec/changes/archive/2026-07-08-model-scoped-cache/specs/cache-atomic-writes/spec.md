# Cache Atomic Writes

## ADDED Requirements

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
