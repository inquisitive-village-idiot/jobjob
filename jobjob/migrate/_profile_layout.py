#!/usr/bin/env python3
"""Migration: move a pre-unification ``<home>/profile`` to ``<home>/profiles/local``.

Upgrades a ``<2.0.0`` working dir to the ``2.0.0+`` profile layout. Older installs
scaffolded a single ``profile/`` dir (seeded from the Tila Mer example); the 2.0.0
unification moved it to ``profiles/<name>/``. The move preserves whatever the user
edited; the ``.env`` registry path is rewritten to match. Idempotent and a no-op when
there is nothing to migrate.

Moved here from ``jobjob.launcher`` as the first entry in the versioned migration set.
"""

from pathlib import Path

# Layout constants (kept here to avoid a launcher↔migrate import cycle).
LOCAL_PROFILE_NAME = "local"
PROFILES_SUBDIR = "profiles"


def _local_profile_dir(home: Path) -> Path:
    return home / PROFILES_SUBDIR / LOCAL_PROFILE_NAME


def migrate_legacy_profile(home: Path) -> bool:
    """Move ``<home>/profile`` → ``<home>/profiles/local`` and fix the registry path.

    Arguments:
        home: The jobjob working directory to migrate in place.
    Returns:
        True if a migration was performed, else False (no legacy dir, or the target
        already exists).
    """
    legacy = home / "profile"
    target = _local_profile_dir(home)
    if not legacy.is_dir() or target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    legacy.rename(target)

    env_path = home / "config" / ".env"
    if env_path.is_file():
        key = f"JOBJOB_PROFILE_{LOCAL_PROFILE_NAME.upper()}"
        new_lines = []
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{key}=") and not stripped.startswith("#"):
                new_lines.append(f"{key}={target}")
            else:
                new_lines.append(line)
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True


# __END__
