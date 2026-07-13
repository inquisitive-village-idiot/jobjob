#!/usr/bin/env python3
"""Cache support.

## Global Cache

This module supports a global cache via a pseudo-singleton (a single instance is
managed via the module, but the class itself is not a singleton).

Each cache manager supports a single, unique directory.

## Patterns

(or considerations and future work)

This module
"""

import dataclasses as dcs
import hashlib
import json
import os
import tempfile
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, Self

_CACHE = None  # type: CacheManager | None
_CACHE_PATH = None  # type: Path | None
_CACHE_PATH_ENV = "CACHE_DIR"
__CACHE_PATH_DEFAULT = Path(Path.cwd(), ".cache").resolve()


# Errors
# ======================================================================


class CacheMissError(KeyError):
    """Raise if there is no cache for the given prompt."""


class CacheManagerCollisionError(ValueError):
    """Raise if a CacheManager instance already exists for the given path."""


class CachePathSetOnceError(RuntimeError):
    """Raise if the module cache path is already set (set-once violation)."""


class InvalidCacheError(ValueError):
    """Raise if the cache doesn't match the expected pattern."""


# Cache Hash Generator
# ======================================================================


def get_cache_hash(value: Any, size: int = 32) -> str:
    """Generate a suitable hash from the given value.

    NOTE: This hash is not guaranteed unique, but should be effectively so.
    """
    return hashlib.sha256(str(value).encode()).hexdigest()[:size]


# Cache Manager
# ======================================================================


@dcs.dataclass(frozen=True)
class CacheManager:
    """Supports prompt/response loading to and saving from a cache.

    Writes are atomic (temp file + ``os.replace``), so entries are always
    complete-or-absent; no locking is needed. See ``save_to_cache``.

    Class Attributes:
        _registry: Tracks instances based on cache path. Used to ensure one one
            CacheManager per directory.

    Attributes:
        cache_path: Location of the cache.
    """

    cache_path: Path
    _get_cache_hash: Callable[[str], str] = get_cache_hash
    _registry: ClassVar[dict] = {}

    # class methods
    # ----------------------------------

    @classmethod
    def deregister(cls, value: Path | Self) -> None:
        """Remove item from registry.

        NOTE: This does NOT remove the files in the cache.
        NOTE: This does NOT guarantee that cache instances are destroyed.
            References to mangers are still accessible.

        Arguments:
            value: A path or CacheManager instance.
        Returns:
            None
        Raises:
            None. If the given cache isn't registered, it doesn't matter b/c
            we're removing it from the register. Don't complain needlessly.
        """
        _value = getattr(value, "cache_path", value)
        try:
            path = Path(_value)
        except TypeError:
            return  # EARLY EXIT: Nothing to do.
        _ = cls._registry.pop(path, None)
        return

    @classmethod
    def deregister_all(cls) -> None:
        """Clear registry.

        NOTE: This does NOT remove the files in the cache.
        NOTE: This does NOT guarantee that all cache instances are destroyed.
            References to mangers are still accessible.
        """
        cls._registry = {}

    @classmethod
    def new(cls, path: Path) -> Self:
        """Return a unique cache manager instance for the given path.

        NOTE: Returns existing instance if one exists for the given path.
        """
        if existing := cls._registry.get(path):
            return existing  # EARLY EXIT: Unique manager found for path; use it.
        return cls(Path(path))

    # methods
    # ----------------------------------

    def __post_init__(self) -> None:
        """Post-init processing.

        Raises:
            CacheManagerCollisionError(ValueError) if cache_path is already
            registered to another instance.
        """
        if self.cache_path in self._registry:
            msg = (
                "A cache manager instace already exists for this directory. "
                "Use CacheManager.new or CacheManager.retrieve instead"
            )
            raise CacheManagerCollisionError(f"{self.cache_path}. {msg}")

        # Does NOT create parents
        self.cache_path.mkdir(exist_ok=True)

        # Adds self to the instance tracker
        self._registry[self.cache_path] = self

    def delete_cache_entry(self, prompt: str, model: str | None = None) -> None:
        """Delete given cache entry.

        NOTE: Intended to cleanup invalid cache.

        Arguments:
            prompt: The prompt string.
            model: Optional model identifier. Part of the key, so entries for the
                same prompt under different models (or no model) are addressed
                independently.
        Returns:
            None.
        Raises:
            None. If the cache doesn't exist, no need to complain as that's the target.
        """
        key = self._key(prompt, model)
        path = self._cache_path_for(key)
        try:
            path.unlink()
        except FileNotFoundError:
            pass  # ignore -- this is the target state

    def load_from_cache(self, prompt: str, model: str | None = None) -> Any:
        """Load cache for given prompt.

        Arguments:
            prompt: The prompt string.
            model: Optional model identifier. Part of the key, so a response cached
                under one model is never served for another (or for no model).
        Returns:
            The cached response. May be any json-encodable type as the save to cache
            process performs json encoding.
        Raises:
            CacheMissError(KeyError) if no cache exists for the given prompt/model.
        """
        key = self._key(prompt, model)
        path = self._cache_path_for(key)
        if not path.is_file():
            shorter = textwrap.shorten(prompt, width=80)
            raise CacheMissError(f"No cache found: {shorter}")
        content = path.read_text(encoding="utf-8")
        try:
            data = json.loads(content)
            return data["response"]
        except (ValueError, KeyError):
            shorter = textwrap.shorten(prompt, width=80)
            raise InvalidCacheError(f"Invalid cache: {shorter}")

    def purge_cache(self) -> None:
        """Deletes all files in cache. NOT recursive."""
        for path in self.cache_path.iterdir():
            if path.is_dir():
                continue
            path.unlink()

    def save_to_cache(
        self, prompt: str, response: Any, model: str | None = None
    ) -> None:
        """Save given prompt and response to the cache.

        Atomic: content is written to a uniquely-named ``.tmp`` file in the
        cache directory, then moved onto the final path via ``os.replace``.
        Readers never observe a partial entry. On failure, the temp file is
        removed (best-effort) and the final path is left untouched -- recovery
        is a cache miss followed by a fresh save, never a resumed temp file.
        Orphaned ``.tmp`` files (hard kill) are ignored by readers and removed
        by ``purge_cache``.

        Arguments:
            prompt: The prompt string
            response: The response. Must be JSON encodable.
            model: Optional model identifier. Part of the key, so the same prompt
                under a different model is stored as a distinct entry.
        Returns:
            None.
        Raises:
            Errors from encoding or writing are propagated.
        """
        key = self._key(prompt, model)
        path = self._cache_path_for(key)
        data = {"model": model, "prompt": prompt, "response": response}
        content = json.dumps(data, separators=(",", ":"))

        # Same directory as the final path guarantees same filesystem,
        # which guarantees os.replace is atomic.
        fd, tmp_name = tempfile.mkstemp(
            dir=self.cache_path, prefix=f"{key}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp_path, path)
        except BaseException:
            tmp_path.unlink(missing_ok=True)  # best-effort; orphans are inert
            raise

    # "private" methods
    # ----------------------------------

    def _cache_path_for(self, key: str) -> Path:
        return Path(self.cache_path, f"{key}.json")

    def _key(self, prompt: str, model: str | None) -> str:
        """Derive the cache key from the ``(model, prompt)`` pair.

        NOTE: ``repr`` (not ``str``) so ``model=None`` is unambiguous and the
        pair round-trips deterministically as hash input.
        """
        return self._get_cache_hash(repr((model, prompt)))


# Module Functions
# ======================================================================

# Cache (Manager)
# ----------------------------------


def deregister_cache() -> None:
    """Delete cache files from the global registry."""
    global _CACHE
    if not _CACHE:
        return  # EARLY EXIT: No action needed.

    CacheManager.deregister(_CACHE.cache_path)
    _CACHE = None


def get_cache() -> CacheManager:
    """Return a global cache manager."""
    global _CACHE
    if _CACHE:
        return _CACHE  # EARLY EXIT: Cache set; use it.

    cache_path = get_cache_path()
    manager = CacheManager.new(cache_path)
    _CACHE = manager
    return manager


def purge_cache() -> None:
    """Delete cache files from the global registry."""
    cache_manager = get_cache()
    cache_manager.purge_cache()


# Cache Path
# ----------------------------------


def get_cache_path_default() -> Path:
    return __CACHE_PATH_DEFAULT


def get_cache_path() -> Path:
    """Return the default cache path.

    NOTE: If _CACHE_PATH_DEFAULT is modified, this may have undefined behavior.
    NOTE: Will set _CACHE_PATH after first call to finalize.
    """
    global _CACHE_PATH
    if not _CACHE_PATH:
        _CACHE_PATH = _get_cache_path_fallback()
    return _CACHE_PATH


def _get_cache_path_fallback() -> Path:
    env_path = os.environ.get(_CACHE_PATH_ENV)
    path = env_path or get_cache_path_default()
    resolved = Path(path).expanduser().resolve()
    return resolved


def set_cache_path(path: Path | None) -> None:
    """Set the cache path. Deregisters the current cache. Use None to clear.

    NOTE: Clears _CACHE for safety (should be unnecessary).

    Arguments:
        path: Path string for cache. Use None to deregister and clear.
    Returns:
        None
    Raises:
        Errors from Path will be propagated if given path is invalid.
        CachePathSetError(RuntimeError) if the path has already been set. This prevents
        accidental update mid-execution.
    """
    global _CACHE_PATH

    if path is None:
        _path = None
    elif _CACHE_PATH:
        msg = "The cache path has already been set and should not be modified"
        raise CachePathSetOnceError(f"{msg}: {_CACHE_PATH}")
    else:
        _path = Path(path).expanduser().resolve()

    _CACHE_PATH = _path

    # Defensive: Ensures _CACHE is cleared even if call order changes in the future
    deregister_cache()


# __END__
