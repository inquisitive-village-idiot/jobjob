# Tasks: Model-Scoped Response Cache

## 1. Model-aware cache key

- [ ] 1.1 `CacheManager.load_from_cache`, `save_to_cache`, and
  `delete_cache_entry` accept an optional `model` argument; derive the key
  from the `(model, prompt)` pair via `_get_cache_hash`
- [ ] 1.2 Record `model` in the stored JSON payload alongside `prompt`/`response`

## 2. Thread the model through the query layer

- [ ] 2.1 `AIClient` exposes a `model` property delegating to
  `getattr(self.adapter, "model", None)`
- [ ] 2.2 `query_ai_service` derives the model from `_query_service`
  (`getattr(..., "model", None)`) and binds it into the default cache
  callables via closures; the injected `_load_cache(prompt)` /
  `_save_cache(prompt, response)` contract is unchanged

## 3. Remove the webapp bypass

- [ ] 3.1 In `_make_apply_run` (`webapp/backend/routers/jobs.py`), stop forcing
  `use_cache=False` on a model override; update/remove the docstring note about
  the bypass

## 4. Tests

- [ ] 4.1 Same prompt under two models yields two entries; each loads its own
  response; absent-model is its own namespace
- [ ] 4.2 `query_ai_service` with a model-bearing service saves/loads under the
  model-scoped key; a service without `.model` falls back to the prompt-only
  namespace
- [ ] 4.3 An apply run with a model override populates then hits its own cache
  entry on repeat (regression for the removed bypass)

## 5. Docs + verify

- [ ] 5.1 Update the caching docs/docstrings to state the key is model-scoped
  (CLAUDE.md "Local file cache" note; configuration/caching reference if present)
- [ ] 5.2 Run the cachemanager, query, and jobs test suites; confirm green
