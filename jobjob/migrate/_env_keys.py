#!/usr/bin/env python3
"""Migration: rewrite deprecated config keys in ``<home>/config/.env`` to new names.

Upgrades a ``<2.4.0`` app config to the ``2.4.0+`` per-component input/output key
names: ``DATA_DIR`` → ``APPLICATIONS_INPUT_DIR``, ``APPLICATIONS_LOCAL_DIR`` →
``APPLICATIONS_OUTPUT_DIR``, ``APPLICATIONS_FOLDER_ID`` →
``APPLICATIONS_OUTPUT_DRIVE_ID``, ``LINKEDIN_SHEET_ID`` → ``ENRICHMENT_OUTPUT_SHEET_ID``
(the canonical map is ``jobjob.config.RENAMED_KEYS``).

Best-effort, NON-destructive cleanup that only tidies the file. It is NOT the
compatibility mechanism — the load-time fallback in ``jobjob.config._env_first`` is,
and it also covers env-var-only setups a file rewrite can't reach. So a skipped or
failed rewrite never breaks the app.

Rules:
- A deprecated key is renamed only if its new name is NOT already assigned in the file
  (never clobber a value the user already set under the new name).
- Values, comments, ordering, and unrelated lines are preserved verbatim.
"""

from pathlib import Path


def _assigned_keys(lines: list[str]) -> set[str]:
    """Return the set of KEY names assigned (``KEY=value``) in ``lines``.

    Arguments:
        lines: The raw lines of a dotenv-format file.
    Returns:
        The keys that have an assignment (comments and blank lines ignored).
    """
    keys: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            keys.add(stripped.split("=", 1)[0].strip())
    return keys


def migrate_env_keys(home: Path) -> bool:
    """Rewrite deprecated keys in ``<home>/config/.env`` to their new names.

    Arguments:
        home: The jobjob working directory (its ``config/.env`` is rewritten in place).
    Returns:
        True if the file was rewritten, else False (no file, or nothing to rename).
    """
    env_path = home / "config" / ".env"
    if not env_path.is_file():
        return False

    from jobjob.config import RENAMED_KEYS

    lines = env_path.read_text(encoding="utf-8").splitlines()
    present = _assigned_keys(lines)
    changed = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            new_key = RENAMED_KEYS.get(key.strip())
            # Rename only when the new key isn't already set (don't clobber).
            if new_key is not None and new_key not in present:
                out.append(f"{new_key}={value}")
                present.add(new_key)
                changed = True
                continue
        out.append(line)

    if changed:
        env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


# __END__
