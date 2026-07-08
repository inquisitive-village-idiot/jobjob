# Design: Model-Scoped Response Cache

## Context

`CacheManager` keys entries on `sha256(prompt)` alone (`cachemanager.py` →
`_get_cache_hash(prompt)`). The model is not part of the key, so a response
produced by model A is served for a run requesting model B. The webapp works
around this by disabling the cache entirely whenever a per-run model override
is set (`_make_apply_run` in `webapp/backend/routers/jobs.py`), so the
"re-run with a better model" flow gets no caching at all.

## Goals

- Same prompt + different model ⇒ distinct cache entries.
- Same prompt + configured model ⇒ still a hit on re-run.
- Remove the model-override cache bypass in `_make_apply_run`.
- No changes to the ~13 `query_ai_service` call sites.

## Decisions

### Where the model enters the key

The model identifier is known at the `_query_service` boundary: every call
site passes an `AIClient` (which wraps an adapter carrying `.model`) as the
query service. Rather than thread a `model` argument through all 13 call
sites, `query_ai_service` reads the model off its `_query_service` and binds
it into the default cache callables.

- `AIClient` gains a `model` property delegating to `getattr(self.adapter,
  "model", None)`. The `AIAdapter` protocol is not widened; the read is
  tolerant so non-Anthropic / fake services return `None` (prompt-only key,
  today's behavior).
- `query_ai_service` derives `model = getattr(_query_service, "model", None)`
  and, when wiring the *default* cache callables, captures it in closures.
  The injected-callable contract is unchanged: `_load_cache(prompt)` /
  `_save_cache(prompt, response)` still take only the prompt, so existing
  test injections keep working.

### Key derivation lives in CacheManager

`CacheManager` owns key composition (per the proposal's Impact). The
model becomes a first-class, optional dimension:

- `load_from_cache(prompt, model=None)`,
  `save_to_cache(prompt, response, model=None)`,
  `delete_cache_entry(prompt, model=None)`.
- Key material is the pair `(model, prompt)` fed to `_get_cache_hash`, which
  already `str()`-ifies its input — `str((model, prompt))` is deterministic.
  `model=None` reproduces a distinct namespace from any real model id; it does
  **not** need to equal the old prompt-only hash (see migration).
- The stored payload records `model` alongside `prompt`/`response` for
  debuggability.

### Migration: none

Existing prompt-only entries miss under the new key and repopulate. The cache
is ephemeral by design (`~/.cache/job-apply`, `CLEAR_CACHE`), so no migration
or dual-read is warranted.

## Risks / tradeoffs

- Reading `.model` via `getattr` is duck-typed rather than protocol-enforced.
  Acceptable: the fallback (`None` ⇒ prompt-only key) is exactly the pre-change
  behavior, so a service without `.model` is never worse off.
- One-time cache churn on first run after deploy (all entries miss once).
  Expected and cheap.
