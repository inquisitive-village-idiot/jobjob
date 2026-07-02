#!/usr/bin/env python3
"""Test."""

import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import jobjob.ailib.cachemanager as MOD

LOGGER = logging.getLogger(__name__)


class ThisTestCase(TestCase):
    """Base test case for the module."""

    def setUp(self) -> None:
        # We MUST protect existing caches (just in case testing alongside project)
        self.protect_existing_caches()

        # and make sure we haven't mucked up the registry
        self.addCleanup(MOD.deregister_cache)  # NOTE: SHOULD run before deregister all
        self.addCleanup(MOD.set_cache_path, None)
        self.addCleanup(MOD.CacheManager.deregister_all)

        # protect env (b/c of CACHE_DIR)
        self.addCleanup(self.thaw_env, self.freeze_env())

    def get_tmpdir(self, **kwargs) -> Path:
        tmpdir = TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return Path(tmpdir.name)

    def protect_existing_caches(self) -> None:
        self._get_cache_path = MOD.get_cache_path
        tmpdir = self.get_tmpdir()
        patch = mock.patch.object(MOD, "get_cache_path")
        self.mock_get_cache_path = patch.start()
        self.mock_get_cache_path.return_value = Path(tmpdir, "protected")
        self.addCleanup(patch.stop)

    def get_clean_cache(self, **kwargs) -> MOD.CacheManager:
        tmpdir = self.get_tmpdir()
        instance = MOD.CacheManager(tmpdir, **kwargs)
        return instance

    def freeze_env(self) -> tuple[str, str]:
        return tuple(os.environ.items())

    def thaw_env(self, items: tuple[str, str]) -> None:
        os.environ = dict(items)


class TestCacheManagerBehavior(ThisTestCase):
    """Test class(method) behavior."""

    def test_new_returns_new_cache_manager_instance_per_directory(self) -> None:
        with TemporaryDirectory() as td1, TemporaryDirectory() as td2:
            tmpdir1, tmpdir2 = Path(td1), Path(td2)
            instance1 = MOD.CacheManager.new(tmpdir1)
            instance2 = MOD.CacheManager.new(tmpdir2)
            instance3 = MOD.CacheManager.new(tmpdir1)

        assert instance1 is not instance2
        assert instance1 is instance3

    def test_deregister_via_path(self) -> None:
        _ = self.get_clean_cache()
        control = tuple(MOD.CacheManager._registry.items())

        instance = self.get_clean_cache()
        assert instance.cache_path in MOD.CacheManager._registry
        MOD.CacheManager.deregister(instance.cache_path)

        with self.subTest("remove via path"):
            expected = dict(control)
            found = MOD.CacheManager._registry
            self.assertEqual(expected, found)

        with self.subTest("idempotence"):
            MOD.CacheManager.deregister(instance.cache_path)  # should not raise
            MOD.CacheManager.deregister(instance.cache_path)  # should not raise
            expected = dict(control)
            found = MOD.CacheManager._registry
            self.assertEqual(expected, found)

    def test_deregister_via_instance(self) -> None:
        _ = self.get_clean_cache()
        control = tuple(MOD.CacheManager._registry.items())

        instance = self.get_clean_cache()
        assert instance.cache_path in MOD.CacheManager._registry
        MOD.CacheManager.deregister(instance)

        with self.subTest("remove via path"):
            expected = dict(control)
            found = MOD.CacheManager._registry
            self.assertEqual(expected, found)

        with self.subTest("idempotence"):
            MOD.CacheManager.deregister(instance)  # should not raise
            MOD.CacheManager.deregister(instance)  # should not raise
            expected = dict(control)
            found = MOD.CacheManager._registry
            self.assertEqual(expected, found)

    def test_deregister_all_resets_registry(self) -> None:
        _ = MOD.get_cache()  # ensure we have at least one cache
        _ = self.get_clean_cache()
        _ = self.get_clean_cache()

        assert MOD.CacheManager._registry != {}, "invalid test state: registry empty"

        MOD.CacheManager.deregister_all()

        expected = {}
        found = MOD.CacheManager._registry
        self.assertEqual(expected, found)


class TestCacheManagerInit(ThisTestCase):
    """Test behavior."""

    def test_raises_if_cache_exists_for_same_dir(self) -> None:
        with TemporaryDirectory() as td:
            tmpdir = Path(td)
            _ = MOD.CacheManager(tmpdir)
            with self.assertRaises(ValueError):
                _ = MOD.CacheManager(tmpdir)

    def test_adds_self_to_class_tracker(self) -> None:
        assert MOD.CacheManager._registry == {}, "initial assumption"
        with TemporaryDirectory() as td:
            tmpdir = Path(td)
            instance = MOD.CacheManager(tmpdir)
        expected = {tmpdir: instance}
        found = MOD.CacheManager._registry
        self.assertEqual(expected, found)

    def test_creates_dir_if_needed(self) -> None:
        with TemporaryDirectory() as td:
            given = Path(td, "foo")
            _ = MOD.CacheManager(given)

            expected = True
            found = given.is_dir()
            self.assertEqual(expected, found)


class TestCacheManagerDeleteCacheEntry(ThisTestCase):
    """Test method."""

    def test_does_not_raise_if_entry_not_found(self) -> None:
        instance = self.get_clean_cache()
        instance.delete_cache_entry("foo")  # should not raise

    def test_removes_single_entry(self) -> None:
        # NOTE: Coupled with load and save to ensure correct pattern is used.
        instance = self.get_clean_cache()

        foo = ("foo", "... some data ...")
        bar = ("bar", "... more data ...")

        instance.save_to_cache(*foo)
        instance.save_to_cache(*bar)

        assert instance.load_from_cache(foo[0]) == foo[1], "invalid base assumption"
        instance.delete_cache_entry(foo[0])
        assert instance.load_from_cache(bar[0]) == bar[1], "other untouched"

        with self.assertRaises(KeyError):
            instance.load_from_cache(foo[0])  # deleted


class TestCacheManagerLoadFromCache(ThisTestCase):
    """Test method."""

    def test_raises_if_error_loading_invalid_cache_encoding(self) -> None:
        instance = self.get_clean_cache()
        prompt = "foo"
        prompt_hash = MOD.get_cache_hash(prompt)

        cache_path = Path(instance.cache_path, f"{prompt_hash}.json")
        cache_path.write_text("foo-bar")

        # NOTE: prompt should be appreviated in the error message (not tested)
        with self.assertRaisesRegex(ValueError, f"Invalid cache: {prompt}"):
            instance.load_from_cache(prompt)

    def test_raises_if_error_loading_invalid_cache_structure(self) -> None:
        instance = self.get_clean_cache()
        prompt = "foo"
        prompt_hash = MOD.get_cache_hash(prompt)

        cache_path = Path(instance.cache_path, f"{prompt_hash}.json")
        cache_path.write_text(json.dumps({"foo": "bar"}))

        # NOTE: prompt should be appreviated in the error message (not tested)
        with self.assertRaisesRegex(ValueError, f"Invalid cache: {prompt}"):
            instance.load_from_cache(prompt)

    def test_raises_if_cache_not_found(self) -> None:
        instance = self.get_clean_cache()
        key = "foo"
        with self.assertRaisesRegex(KeyError, f"No cache found: {key}"):
            instance.load_from_cache(key)

    def test_returns_cache(self) -> None:
        with TemporaryDirectory() as td:
            tmpdir = Path(td)
            key = "foo"

            cache_path = Path(tmpdir, f"{key}.json")
            content = {"response": "bar"}
            cache_path.write_text(json.dumps(content))

            instance = MOD.CacheManager(tmpdir, _get_cache_hash=lambda x: key)

            expected = content["response"]
            found = instance.load_from_cache(key)
            self.assertEqual(expected, found)


class TestCacheManagerPurgeCache(ThisTestCase):
    """Test method."""

    def test_removes_all_files_in_cache_dir(self) -> None:
        instance = self.get_clean_cache()

        Path(instance.cache_path, "foo.json").write_text("foo")
        Path(instance.cache_path, "bar.json").write_text("bar")

        instance.purge_cache()

        expected = []
        found = list(instance.cache_path.iterdir())
        self.assertEqual(expected, found)

    def test_ignores_directories(self) -> None:
        instance = self.get_clean_cache()

        subdir = Path(instance.cache_path, "meh")
        subdir.mkdir()
        protected = Path(subdir, "baz.json")
        protected.write_text("baz")

        Path(instance.cache_path, "foo.json").write_text("foo")
        Path(instance.cache_path, "bar.json").write_text("bar")

        instance.purge_cache()

        expected = [subdir]
        found = list(instance.cache_path.iterdir())
        self.assertEqual(expected, found)

        assert protected.is_file(), "protected file was removed"


class TestCacheManagerSaveToCache(ThisTestCase):
    """Test method."""

    def test_saves_prompt_and_response_to_cache(self) -> None:
        with TemporaryDirectory() as td:
            tmpdir = Path(td)
            instance = MOD.CacheManager(tmpdir)

            prompt = "foo bar baz"
            response = "... some data ..."
            key = instance._get_cache_hash(prompt)

            instance.save_to_cache(prompt, response)

            expected = {"prompt": prompt, "response": response}
            found = json.loads(instance._cache_path_for(key).read_text())
            self.assertEqual(expected, found)

    def test_overwrites_existing_prompt_cache(self) -> None:
        instance = self.get_clean_cache()

        prompt = "foo bar baz"
        response1 = "... some data ..."
        response2 = "... other data ..."

        cache_path = instance._cache_path_for(instance._get_cache_hash(prompt))

        instance.save_to_cache(prompt, response1)
        instance.save_to_cache(prompt, response2)

        expected = {"prompt": prompt, "response": response2}
        found = json.loads(cache_path.read_text())
        self.assertEqual(expected, found)

    def test_successful_save_leaves_no_temp_files(self) -> None:
        instance = self.get_clean_cache()

        prompt = "foo bar baz"
        key = instance._get_cache_hash(prompt)

        instance.save_to_cache(prompt, "... some data ...")

        expected = [instance._cache_path_for(key)]
        found = list(instance.cache_path.iterdir())
        self.assertEqual(expected, found)

    def test_failed_write_leaves_final_path_unchanged(self) -> None:
        instance = self.get_clean_cache()

        prompt = "foo bar baz"
        response1 = "... some data ..."
        cache_path = instance._cache_path_for(instance._get_cache_hash(prompt))
        instance.save_to_cache(prompt, response1)

        err = OSError("disk full")
        with mock.patch.object(MOD.os, "replace", side_effect=err):
            with self.subTest("exception propagates"):
                with self.assertRaisesRegex(OSError, "disk full"):
                    instance.save_to_cache(prompt, "... other data ...")

        with self.subTest("prior entry untouched"):
            expected = response1
            found = instance.load_from_cache(prompt)
            self.assertEqual(expected, found)

        with self.subTest("temp file removed"):
            expected = [cache_path]
            found = list(instance.cache_path.iterdir())
            self.assertEqual(expected, found)

    def test_orphaned_temp_file_is_inert(self) -> None:
        instance = self.get_clean_cache()

        prompt = "foo bar baz"
        key = instance._get_cache_hash(prompt)
        orphan = Path(instance.cache_path, f"{key}.orphan.tmp")
        orphan.write_text("{ partial garbage")

        with self.subTest("ignored by load_from_cache"):
            with self.assertRaises(KeyError):
                instance.load_from_cache(prompt)  # miss, NOT InvalidCacheError

        with self.subTest("removed by purge_cache"):
            instance.purge_cache()
            expected = []
            found = list(instance.cache_path.iterdir())
            self.assertEqual(expected, found)


# Module Functions
# ======================================================================


class TestDeregisterCache(ThisTestCase):
    """Test function."""

    def test_deregisters_and_removes_module_cache(self) -> None:
        instance1 = MOD.get_cache()
        assert MOD._CACHE is not None

        MOD.deregister_cache()

        with self.subTest("clears the module cache var"):
            assert MOD._CACHE is None

        with self.subTest("removes from registry"):
            assert instance1.cache_path not in MOD.CacheManager._registry

    def test_idempotence(self) -> None:
        _ = MOD.get_cache()
        with self.subTest("safe to call multiple times"):
            MOD.deregister_cache()  # should not raise
            MOD.deregister_cache()  # should not raise
            MOD.deregister_cache()  # should not raise

    def test_does_not_modify_other_registry_items(self) -> None:
        _ = MOD.get_cache()
        MOD.CacheManager._registry["foo"] = "bar"
        MOD.deregister_cache()
        expected = {"foo": "bar"}
        found = MOD.CacheManager._registry
        self.assertEqual(expected, found)


class TestGetCache(ThisTestCase):
    """Test function."""

    def test_creates_and_returns_global_cache(self) -> None:
        assert MOD._CACHE is None, "invalid initial assertion"
        instance = MOD.get_cache()

        with self.subTest("returns cache manager"):
            assert isinstance(instance, MOD.CacheManager)

        with self.subTest("sets as global cache"):
            expected = instance
            found = MOD._CACHE
            assert expected is found

        with self.subTest("returns same each time"):
            expected = instance
            found = MOD.get_cache()
            assert expected is found


class TestPurgeCache(ThisTestCase):
    """Test function."""

    def test_removes_module_cache_and_only_module_cache_files(self) -> None:
        module_cache = MOD.get_cache()
        second_cache = self.get_clean_cache()

        Path(module_cache.cache_path, "foo.json").write_text("tmp")
        Path(second_cache.cache_path, "bar.json").write_text("tmp")

        # If we don't have these files, the final assertions are invalid
        # NOTE: This is overkill. It's essentially testing Path.
        # TODO: Better to save new caches than this?
        assert 0 < len(list(module_cache.cache_path.iterdir()))
        assert 0 < len(list(second_cache.cache_path.iterdir()))

        MOD.purge_cache()

        assert 0 == len(list(module_cache.cache_path.iterdir()))
        assert 0 < len(list(second_cache.cache_path.iterdir()))


class TestGetCachePath(ThisTestCase):
    """Test function.

    NOTE: Modifies CACHE_DIR env var. See setUp for protections.
    """

    def setUp(self) -> None:
        super().setUp()
        self.restore_get_cache_path()

    def restore_get_cache_path(self) -> None:
        self.mock_get_cache_path.side_effect = self._get_cache_path

    def test_fallback_behavior(self) -> None:
        # NOTE: Calls the private method for fallback.
        tmpdir = self.get_tmpdir()
        mod_path = Path(tmpdir, "module_var")
        env_path = Path(tmpdir, "env_var")
        default_path = MOD.get_cache_path_default()

        MOD._CACHE_PATH = mod_path
        os.environ[MOD._CACHE_PATH_ENV] = str(env_path)

        with self.subTest("via module attr"):
            expected = mod_path  # NOT resolved -- use as is
            found = MOD.get_cache_path()
            self.assertEqual(expected, found)

        MOD._CACHE_PATH = None
        with self.subTest("via env var"):
            expected = env_path.resolve()
            found = MOD.get_cache_path()
            self.assertEqual(expected, found)

        MOD._CACHE_PATH = None
        del os.environ[MOD._CACHE_PATH_ENV]
        with self.subTest("via env var"):
            expected = default_path.resolve()
            found = MOD.get_cache_path()
            self.assertEqual(expected, found)


class TestSetCachePath(ThisTestCase):
    """Test function."""

    def setUp(self) -> None:
        super().setUp()
        self.restore_get_cache_path()

    def restore_get_cache_path(self) -> None:
        self.mock_get_cache_path.side_effect = self._get_cache_path

    def test_raises_if_cache_path_already_set(self) -> None:
        _ = MOD.get_cache()  # indirectly ensure we have a module cache & path
        assert MOD._CACHE_PATH is not None

        with self.subTest("raises"):
            with self.assertRaises(RuntimeError):
                MOD.set_cache_path("foo")

        with self.subTest("does not clear"):
            assert MOD._CACHE is not None
            assert MOD._CACHE_PATH is not None

    def test_sets_module_value(self) -> None:
        MOD._CACHE = self.get_clean_cache()
        MOD.set_cache_path("foo")

        with self.subTest("sets resolved path"):
            expected = Path("foo").resolve()  # NOTE: implicit conversion to path
            found = MOD._CACHE_PATH
            self.assertEqual(expected, found)

        with self.subTest("clears _CACHE"):
            expected = None
            found = MOD._CACHE
            self.assertEqual(expected, found)

    def test_clears_module_cache_if_None(self) -> None:
        _ = MOD.get_cache()  # ensure we have a module cache

        MOD.set_cache_path(None)

        expected = None
        found = MOD._CACHE
        self.assertEqual(expected, found)


# __END__
