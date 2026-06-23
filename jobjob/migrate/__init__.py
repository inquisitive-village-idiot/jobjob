#!/usr/bin/env python3
"""Versioned, idempotent migrations applied to a jobjob working dir on launch.

Each migration is a callable ``(home: Path) -> bool`` (returns whether it changed
anything) and MUST be safe to re-run. ``run_migrations`` applies them in order. Keep
appending new migrations to ``MIGRATIONS`` — order is the version history.

Migrations are best-effort: the app must still launch if one is skipped, so the
runtime also tolerates pre-migration state (e.g. the config load-time fallback in
``jobjob.config`` keeps deprecated env keys working regardless of the file rewrite).
"""

import logging
from collections.abc import Callable
from pathlib import Path

from jobjob.migrate._env_keys import migrate_env_keys
from jobjob.migrate._profile_layout import migrate_legacy_profile

# Ordered migration history. Append new migrations; never reorder existing ones.
MIGRATIONS: tuple[tuple[str, Callable[[Path], bool]], ...] = (
    ("legacy_profile_layout", migrate_legacy_profile),
    ("env_key_rename", migrate_env_keys),
)


def run_migrations(home: Path, *, logger: logging.Logger | None = None) -> list[str]:
    """Run every migration in order against ``home``; return the names that applied.

    A migration that raises is logged and skipped — a migration failure must not stop
    the app from launching.
    """
    _logger = logger or logging.getLogger("jobjob.migrate")
    applied: list[str] = []
    for name, fn in MIGRATIONS:
        try:
            if fn(home):
                applied.append(name)
                _logger.info("Applied migration: %s", name)
        except Exception:  # never let a migration block launch
            _logger.warning("Migration %s failed; skipping", name, exc_info=True)
    return applied


__all__ = ["MIGRATIONS", "run_migrations"]

# __END__
