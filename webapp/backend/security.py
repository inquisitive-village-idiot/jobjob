#!/usr/bin/env python3
"""Security primitives: file sandboxing and CSRF double-submit cookie.

All path operations from the API must go through ``safe_path`` before any
read/write. ``configure_sandbox`` is called once at startup with the allowlist.
"""

import secrets
from pathlib import Path
from typing import Union

_ALLOWED_ROOTS: list[Path] = []

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def configure_sandbox(roots: list[Union[str, Path]]) -> None:
    """Set the list of allowed roots for the file sandbox.

    Arguments:
        roots: Absolute or ``~``-relative paths that GUI file operations may touch.
    """
    global _ALLOWED_ROOTS
    _ALLOWED_ROOTS = [Path(r).expanduser().resolve() for r in roots]


def safe_path(user_path: Union[str, Path]) -> Path:
    """Resolve ``user_path`` and verify it sits under an allowed root.

    Arguments:
        user_path: User-supplied path string or Path.
    Returns:
        The resolved, validated absolute Path.
    Raises:
        PermissionError: If the resolved path escapes every allowed root.
    """
    resolved = Path(user_path).expanduser().resolve()
    # Symlink escape check: re-resolve after checking each root.
    for root in _ALLOWED_ROOTS:
        try:
            resolved.relative_to(root)
            # Verify no symlink escape: the real path must also be under the root.
            try:
                real = resolved.resolve(strict=False)
                real.relative_to(root)
            except ValueError:
                raise PermissionError(
                    f"Symlink escape detected: {resolved} -> outside {root}"
                )
            return resolved
        except ValueError:
            continue
    raise PermissionError(f"Path not in allowed sandbox: {resolved}")


def generate_csrf_token() -> str:
    return secrets.token_hex(32)
