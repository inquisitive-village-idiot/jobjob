# Cache Atomic Writes

## ADDED Requirements

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
