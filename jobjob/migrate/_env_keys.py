#!/usr/bin/env python3
"""Migration: rewrite deprecated config keys in ``<home>/config/.env`` to new names.

Best-effort, NON-destructive cleanup that tidies the file to the post-2.4
per-component input/output key names (see ``jobjob.config.RENAMED_KEYS``). This is
NOT the compatibility mechanism — the load-time fallback in
``jobjob.config._env_first`` is, and it also covers env-var-only setups a file rewrite
can't reach. So a skipped or failed rewrite never breaks the app.

Rules:
- A deprecated key is renamed only if its new name is NOT already assigned in the file
  (never clobber a value the user already set under the new name).
- Values, comments, ordering, and unrelated lines are preserved verbatim.
"""

from pathlib import Path


def _assigned_keys(lines: list[str]) -> set[str]:
    """Return the set of KEY names assigned (``KEY=value``) in ``lines``."""
    keys: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            keys.add(stripped.split("=", 1)[0].strip())
    return keys


def migrate_env_keys(home: Path) -> bool:
    """Rewrite deprecated keys in ``<home>/config/.env`` to their new names.

    Returns True if the file was rewritten, else False.
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
