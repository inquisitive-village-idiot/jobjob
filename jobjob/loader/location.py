#!/usr/bin/env python3
"""Resource file location management.

Resolves ``content``, ``reference``, and ``prompt`` resources against the active
profile repo (``<profile>/<name>``) when one is configured, falling back to the
bundled example profile (``static/example/<name>``) so tests and a fresh clone
work without a profile. Prompts override per-file but default to the bundled
jobjob versions.

NOTE: resource getters are intentionally NOT cached — resolution depends on the
    active profile (``os.environ``), which can change at runtime on a profile
    switch. ``get_root_dir``/``get_static_dir``/example getters are profile-
    independent and stay cached.
"""

import os
from functools import cache
from pathlib import Path

from jobjob.loader.profiles import resolve_active_profile_dir

# Per-profile resource dir names (env key → conventional default). A profile may
# rename its resource subdirs via these keys; unset means the conventional name, so
# existing profiles keep working. The names are duplicated here (not imported from
# jobjob.config) to keep this module import-light and free of a config cycle.
_CONTENT_DIR_KEY = "CONTENT_DIR"
_REFERENCE_DIR_KEY = "REFERENCE_DIR"
_PROMPT_DIR_KEY = "PROMPT_DIR"


def _profile_subdir(env_key: str, default: str) -> str:
    """Return the configured resource-dir name for ``env_key``, or ``default``.

    Reads ``os.environ`` (populated by the active profile's config), tolerating
    surrounding quotes/whitespace; an empty value falls back to ``default``.
    """
    value = (os.environ.get(env_key) or "").strip().strip("\"'").strip()
    return value or default


# Template Functions
# ======================================================================


def _get_static_dir(name: str) -> Path:
    """Return the bundled fallback dir ``static/example/{name}`` at project root.

    The bundled example profile doubles as the no-active-profile fallback, so its
    ``content``/``reference`` dirs back tests and a fresh clone.

    Raises:
        FileNotFoundError if the dir does not exist.
    """
    root = get_root_dir()
    result = Path(root, "static", "example", name)
    if not result.is_dir():
        raise FileNotFoundError(
            f'"static/example/{name}" dir not found in project root'
        )
    return result


def _path_in(directory: Path, stem: str) -> Path:
    """Return the file in ``directory`` whose stem matches ``stem``.

    Raises:
        ValueError if no file with that stem exists.
    """
    files = {x.stem: x for x in directory.iterdir()}
    if stem not in files:
        raise ValueError(f'Unknown file "{stem}" in {directory}')
    return files[stem]


def _get_static_path(name: str, stem: str) -> Path:
    """Return path to static/{name} file given the file stem.

    Raises:
        ValueError if file stem not found.
    """
    return _path_in(_get_static_dir(name), stem)


def _resolve_dir(name: str, subdir: str | None = None) -> Path:
    """Return ``<active-profile>/<subdir>`` if it exists, else ``static/<name>``.

    ``subdir`` is the profile's (possibly renamed) directory for this resource; it
    defaults to ``name``. The static fallback always uses the canonical ``name`` (the
    bundled example uses conventional dir names).

    Raises:
        FileNotFoundError if neither the profile dir nor the static default exists.
    """
    profile_dir = resolve_active_profile_dir()
    if profile_dir is not None:
        candidate = profile_dir / (subdir or name)
        if candidate.is_dir():
            return candidate
    return _get_static_dir(name)


# Content
# ======================================================================


def get_content_dir() -> Path:
    """Return the content dir: the active profile's ``content/`` if present, else
    ``static/content``.

    Raises:
        FileNotFoundError if neither exists.
    """
    return _resolve_dir("content", _profile_subdir(_CONTENT_DIR_KEY, "content"))


def get_content_path(stem: str) -> Path:
    """Return the content file for ``stem`` from the resolved content dir.

    Raises:
        ValueError if file stem not found.
    """
    return _path_in(get_content_dir(), stem)


# Prompt
# ======================================================================


def _package_prompt_dir() -> Path:
    """Return the bundled default prompt dir (``jobjob/prompts``).

    Prompts are app behavior, so the defaults ship inside the package rather than
    in ``static/``. Anchored on the repo root so test mocking of ``get_root_dir``
    still exercises the missing-dir path.

    Raises:
        FileNotFoundError if the dir does not exist.
    """
    result = get_root_dir() / "jobjob" / "prompts"
    if not result.is_dir():
        raise FileNotFoundError('"jobjob/prompts" dir not found')
    return result


def package_prompt_dir() -> Path:
    """Public accessor for the bundled default prompt dir (``jobjob/prompts``).

    The prompts editor needs the bundled default explicitly (to show it and to reset
    an override), independent of any active-profile override resolution.
    """
    return _package_prompt_dir()


def get_prompt_dir() -> Path:
    """Return the prompt dir: the active profile's ``prompt/`` if present, else
    the bundled ``jobjob/prompts``."""
    profile_dir = resolve_active_profile_dir()
    if profile_dir is not None:
        prompt_dir = profile_dir / _profile_subdir(_PROMPT_DIR_KEY, "prompt")
        if prompt_dir.is_dir():
            return prompt_dir
    return _package_prompt_dir()


def get_prompt_path(stem: str) -> Path:
    """Return the prompt file for ``stem``.

    A profile may override individual prompts in its ``prompt/`` dir; any prompt
    it does not provide falls back to the bundled ``jobjob/prompts`` default.

    Raises:
        ValueError if file stem not found in the profile override or the default.
    """
    profile_dir = resolve_active_profile_dir()
    if profile_dir is not None:
        prompt_dir = profile_dir / _profile_subdir(_PROMPT_DIR_KEY, "prompt")
        if prompt_dir.is_dir():
            try:
                return _path_in(prompt_dir, stem)
            except ValueError:
                pass  # fall through to the bundled jobjob default
    return _path_in(_package_prompt_dir(), stem)


# Reference
# ======================================================================


def get_reference_dir() -> Path:
    """Return the reference dir: the active profile's ``reference/`` if present,
    else ``static/reference``.

    Raises:
        FileNotFoundError if neither exists.
    """
    return _resolve_dir("reference", _profile_subdir(_REFERENCE_DIR_KEY, "reference"))


# Root, etc
# ======================================================================


@cache
def get_root_dir() -> Path:
    """Return the jobjob project root (the dir containing the ``jobjob`` package).

    Anchored on this file's location (``<root>/jobjob/loader/location.py``) rather than
    searching the path for ``"jobjob"`` — robust when the checkout/site-packages dir is
    itself named ``jobjob``.
    """
    return Path(__file__).resolve().parents[2]


@cache
def get_static_dir() -> Path:
    """Return path to default static dir at project root.

    Raises:
        FileNotFoundError if default dir does not exist.
    """
    root = get_root_dir()
    result = Path(root, "static")
    if not result.is_dir():
        raise FileNotFoundError('"static" dir not found in project root')
    return result


# __END__
