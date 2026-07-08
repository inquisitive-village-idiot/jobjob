# Model-Scoped Response Cache

> Quick win identified in the 2026-07-07 explore session. Standalone —
> shippable in an afternoon, independent of `application-identity`.

## Why

The response cache is keyed on the prompt hash alone
(`jobjob/ailib/query.py` → `load_from_cache(prompt)` →
`sha256(prompt)`). The model is not part of the key, so a cached response
from model A would be served for a run requesting model B. The webapp
already works around this: `_make_apply_run` in
`webapp/backend/routers/jobs.py` **bypasses the cache entirely** whenever a
per-run model override is set (see its docstring). That means "re-run with a
better model" — a flow the user explicitly wants — gets no caching at all,
and the workaround logic is a wart carried by every launch path.

## What Changes

- The cache key incorporates the model identifier alongside the prompt:
  same prompt + different model = distinct entries; re-running with the
  configured model still hits.
- The model-override cache bypass in `_make_apply_run` is removed — overrides
  get correct per-model caching instead of none.
- Existing cache entries (prompt-only keys) simply miss and repopulate under
  the new scheme; the cache is ephemeral by design (`CLEAR_CACHE` /
  `~/.cache/job-apply`), so no migration.

## Capabilities

### New Capabilities

<!-- None — this corrects the keying of the existing response cache. -->

### Modified Capabilities

- `cache-atomic-writes` (or wherever the cache capability lives after spec
  review): key composition requirement gains the model dimension.

## Impact

- `jobjob/ailib/query.py` / `jobjob/ailib/cachemanager.py`: key derivation.
- `webapp/backend/routers/jobs.py`: delete the override bypass + docstring.
- `tests/`: same prompt across two models = two entries; override run hits
  its own entry on repeat.
