# Tasks: Atomic Cache Writes

## 1. Implement atomic save

- [x] 1.1 Rework `CacheManager.save_to_cache()` to write via a unique `.tmp` file in the cache directory, then `os.replace()` onto `{key}.json`; unlink the temp file best-effort on failure and re-raise
- [x] 1.2 Remove the `TODO: Add fcntl or filelock...` comment and document the atomicity guarantee in the docstring

## 2. Tests

- [x] 2.1 Test: successful save leaves complete entry and no `.tmp` files in the cache directory
- [x] 2.2 Test: failed write (injected error) leaves the final path unchanged, removes the temp file, and propagates the exception
- [x] 2.3 Test: orphaned `.tmp` file is ignored by `load_from_cache()` and removed by `purge_cache()`

## 3. Verify

- [x] 3.1 Run the cachemanager test suite and confirm all tests pass
