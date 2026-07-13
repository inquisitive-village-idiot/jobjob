# Design: Atomic Cache Writes

## Context

Cache entries are self-contained files (`{key}.json`), written once per prompt hash
by `CacheManager.save_to_cache()` via `Path.write_text()`. There is no
read-modify-write cycle — the only unsafe window is the non-atomic truncate-then-write
itself. The TODO suggested `fcntl` or `filelock`, but the access pattern doesn't need
locking; it needs write atomicity.

## Goals / Non-Goals

**Goals:**
- Readers never observe a partially written cache entry.
- Concurrent writers to the same key cannot corrupt the entry.
- No new dependencies; portable (macOS/Linux/Windows).

**Non-Goals:**
- Cross-entry transactions or locking (no operation spans multiple entries).
- Recovering data from partial temp files (recovery = cache miss + fresh write).
- Cache eviction / TTL / size limits.

## Decisions

### Decision 1: Atomic replace instead of locking

Write to a `tempfile.NamedTemporaryFile(dir=cache_path, delete=False)` and
`os.replace(tmp, final)`. `os.replace` is atomic on POSIX and Windows when source
and destination are on the same filesystem — guaranteed here because the temp file
is created *inside* the cache directory. This satisfies the thread/process-safety
intent of the TODO with less machinery than `fcntl` (POSIX-only) or `filelock`
(new dependency).

### Decision 2: Temp files are throwaway

On any error before the replace, unlink the temp file in a `finally` (best-effort)
and re-raise. Never attempt to resume a partial temp file — a truncated JSON payload
cannot be trusted, and the source of truth (the API response) lives with the caller.
Worst case: one lost cache entry, one repeated API call.

### Decision 3: Orphan temp files are inert by construction

Temp files use a `.tmp`-suffixed unique name (never `{key}.json`), so
`load_from_cache()` can never resolve one. A hard kill may strand an orphan;
`purge_cache()` already deletes all files in the directory, so no dedicated
cleanup pass is needed.
