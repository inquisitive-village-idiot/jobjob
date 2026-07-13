# Atomic Cache Writes

## Why

`CacheManager.save_to_cache()` writes cache entries with a plain `write_text()`, which truncates then writes. A concurrent reader or second writer can observe a torn (partial) JSON file, surfacing as `InvalidCacheError` and poisoning the entry until manually deleted. The TODO at `jobjob/ailib/cachemanager.py:73` calls for thread/process safety.

## What Changes

- Cache writes become atomic: write to a uniquely-named temp file in the cache directory, then `os.replace()` onto the final path.
- Failed writes leave no partial cache entry — the temp file is removed best-effort; the entry is simply a cache miss on next read. No recovery from partial temp files, ever.
- Orphaned `.tmp` files (hard kill) are inert: readers only look at exact `{key}.json` paths, and `purge_cache()` already removes them.
- Resolves the `TODO` without adding `fcntl` or a `filelock` dependency.

## Capabilities

### New Capabilities

- `cache-atomic-writes`: Cache entries are always complete-or-absent; concurrent access never observes partial writes.

### Modified Capabilities

<!-- None — existing cache read/miss/purge behavior is unchanged. -->

## Impact

- `jobjob/ailib/cachemanager.py`: `save_to_cache()` gains temp-file + atomic-replace; TODO comment removed/updated.
- `tests/jobjob/ailib/test_cachemanager.py`: tests for atomicity behavior (temp cleanup on failure, no partial entry visible).
- No new dependencies.
