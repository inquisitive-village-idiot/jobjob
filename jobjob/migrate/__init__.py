#!/usr/bin/env python3
"""Versioned, idempotent migrations applied to a jobjob working dir on launch.

Each migration is a :class:`Migration` carrying the version range it upgrades FROM →
TO plus a callable ``(home: Path) -> bool`` (returns whether it changed anything). A
migration MUST be safe to re-run. ``run_migrations`` applies them in declaration
order; keep appending to ``MIGRATIONS`` — that order is the version history.

Registered migrations:

- ``legacy_profile_layout`` — ``<2.0.0`` single ``profile/`` dir → ``profiles/<name>/``
  (``2.0.0+``); the 2.0.0 profile-unification layout.
- ``env_key_rename`` — ``<2.4.0`` I/O config keys (``DATA_DIR``,
  ``APPLICATIONS_LOCAL_DIR``, ``APPLICATIONS_FOLDER_ID``, ``LINKEDIN_SHEET_ID``) →
  the ``2.4.0+`` per-component ``APPLICATIONS_*`` / ``ENRICHMENT_*`` names.

Migrations are best-effort: the app must still launch if one is skipped, so the
runtime also tolerates pre-migration state (e.g. the config load-time fallback in
``jobjob.config`` keeps deprecated env keys working regardless of the file rewrite).
"""

import dataclasses as dcs
import logging
from collections.abc import Callable
from pathlib import Path

from jobjob.migrate._env_keys import migrate_env_keys
from jobjob.migrate._profile_layout import migrate_legacy_profile


@dcs.dataclass(frozen=True)
class Migration:
    """A single launch-time migration.

    Attributes:
        name: Stable identifier (logged; do not rename after release).
        from_version: Version range the migration upgrades FROM (e.g. ``<2.4.0``).
        to_version: Version the new behavior was introduced (e.g. ``2.4.0+``).
        apply: Callable taking the working dir; returns True if it changed anything.
    """

    name: str
    from_version: str
    to_version: str
    apply: Callable[[Path], bool]


# Ordered migration history. Append new migrations; never reorder existing ones.
MIGRATIONS: tuple[Migration, ...] = (
    Migration("legacy_profile_layout", "<2.0.0", "2.0.0+", migrate_legacy_profile),
    Migration("env_key_rename", "<2.4.0", "2.4.0+", migrate_env_keys),
)


def run_migrations(home: Path, *, logger: logging.Logger | None = None) -> list[str]:
    """Run every migration in order against ``home``; return the names that applied.

    A migration that raises is logged and skipped — a migration failure must not stop
    the app from launching.

    Arguments:
        home: The jobjob working directory to migrate in place.
        logger: Optional logger; defaults to ``jobjob.migrate``.
    Returns:
        The names of the migrations that actually changed something, in run order.
    """
    _logger = logger or logging.getLogger("jobjob.migrate")
    applied: list[str] = []
    for migration in MIGRATIONS:
        try:
            if migration.apply(home):
                applied.append(migration.name)
                _logger.info(
                    "Applied migration %s (%s → %s)",
                    migration.name,
                    migration.from_version,
                    migration.to_version,
                )
        except Exception:  # never let a migration block launch
            _logger.warning(
                "Migration %s failed; skipping", migration.name, exc_info=True
            )
    return applied


__all__ = ["MIGRATIONS", "Migration", "run_migrations"]

# __END__
