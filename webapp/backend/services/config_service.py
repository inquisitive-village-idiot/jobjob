#!/usr/bin/env python3
"""Read and write ``config/.env`` preserving comments and secret lines.

Secrets are never returned to callers — the schema marks each key as
``is_secret`` and returns ``is_set`` (bool) in place of the value.
"""

from pathlib import Path
from typing import Any, Optional

# Keys whose values must never leave the backend.
_SECRET_KEYS: frozenset[str] = frozenset({"ANTHROPIC_API_KEY"})


def is_secret(key: str) -> bool:
    """Return True if ``key`` should be treated as a secret."""
    return (
        key in _SECRET_KEYS
        or key.upper().endswith("_KEY")
        or key.upper().endswith("_SECRET")
        or key.upper().endswith("_PASSWORD")
    )


# Human-readable labels and groups for UI rendering.
_SCHEMA: dict[str, dict[str, Any]] = {
    "ANTHROPIC_API_KEY": {
        "label": "Anthropic API Key",
        "group": "AI",
        "description": "Your Anthropic API key.",
        "required": True,
    },
    "ANTHROPIC_BASE_URL": {
        "label": "Anthropic Base URL",
        "group": "AI",
        "description": (
            "Advanced: override the Anthropic API endpoint with a Claude-compatible "
            "proxy (e.g. one forwarding to a free Google AI key) to run on a free "
            "backend. Leave blank to use Anthropic directly. Default: Anthropic."
        ),
        "required": False,
    },
    "CLAUDE_MODEL": {
        "label": "Claude Model",
        "group": "AI",
        "description": "Model id (default: claude-sonnet-4-6).",
        "required": False,
        "options": [
            "claude-fable-5",
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5",
        ],
    },
    "CLAUDE_CACHE_ENABLED": {
        "label": "Response Cache Enabled",
        "group": "AI",
        "description": "Enable the local response cache. Default: true.",
        "required": False,
        "options": ["true", "false"],
    },
    "GOOGLE_CREDENTIALS_FILE": {
        "label": "Google Credentials File",
        "group": "Google",
        "description": "Path to the OAuth client-secrets JSON.",
        "required": False,
    },
    "GOOGLE_TOKEN_FILE": {
        "label": "Google Token File",
        "group": "Google",
        "description": "Path to the pickled OAuth token.",
        "required": False,
    },
    "RESUME_TEMPLATE_ID": {
        "label": "Resume Template ID",
        "group": "Google",
        "description": "Fallback Google Doc id for the resume template.",
        "required": False,
    },
    "APPLICATIONS_INPUT_DIR": {
        "label": "Applications · Input directory",
        "group": "Applications",
        "description": (
            "Local root holding jobs/, profiles/, and completed/ for the apply flow. "
            "Processed JDs move into <input>/completed/jobs/ on completion. "
            "Default: data."
        ),
        "required": False,
    },
    "APPLICATIONS_OUTPUT_DIR": {
        "label": "Applications · Output directory (local)",
        "group": "Applications",
        "description": (
            "Local path of the synced Google Drive applications mirror. When set, the "
            "completed list reads from here instead of the Drive API. Set this and/or "
            "the output Drive folder id."
        ),
        "required": False,
    },
    "APPLICATIONS_OUTPUT_DRIVE_ID": {
        "label": "Applications · Output Drive folder id",
        "group": "Applications",
        "description": (
            "Google Drive folder id where generated applications are uploaded. Set "
            "this and/or the local output directory."
        ),
        "required": False,
    },
    "ENRICHMENT_INPUT_DIR": {
        "label": "Enrichment · Input directory",
        "group": "Enrichment",
        "description": (
            "Local input root for the enrich (contacts) flow. Leave blank to use the "
            "applications input directory."
        ),
        "required": False,
    },
    "ENRICHMENT_OUTPUT_SHEET_ID": {
        "label": "Enrichment · Output Sheet id",
        "group": "Enrichment",
        "description": "Google Sheets id for the contacts sheet (enrich).",
        "required": False,
    },
    "APPLICANT_NAME": {
        "label": "Your Name",
        "group": "Applicant",
        "description": "Name shown on cover letter headers.",
        "required": False,
    },
    "APPLICANT_PHONE": {
        "label": "Phone",
        "group": "Applicant",
        "description": "Phone number for cover letter headers.",
        "required": False,
    },
    "APPLICANT_EMAIL": {
        "label": "Email",
        "group": "Applicant",
        "description": "Email address for cover letter headers.",
        "required": False,
    },
    "APPLICANT_LINKEDIN": {
        "label": "LinkedIn URL",
        "group": "Applicant",
        "description": "LinkedIn profile URL for cover letter headers.",
        "required": False,
    },
    "INDUSTRY": {
        "label": "Industry / Domain",
        "group": "Domain",
        "description": (
            "Your field, e.g. 'science journalism' or 'commercial print'. Used to "
            "describe the target company accurately when tailoring the resume "
            "objective. Leave blank for no domain hint."
        ),
        "required": False,
    },
    "CONTENT_DIR": {
        "label": "Content directory",
        "group": "Directories",
        "description": (
            "Folder (inside this profile) holding the content TOML files. "
            "Default: content."
        ),
        "required": False,
    },
    "REFERENCE_DIR": {
        "label": "Reference directory",
        "group": "Directories",
        "description": (
            "Folder (inside this profile) holding reference docs — background, "
            "writing style, cover_letters/, stars/. Default: reference."
        ),
        "required": False,
    },
    "PROMPT_DIR": {
        "label": "Prompt directory",
        "group": "Directories",
        "description": (
            "Folder (inside this profile) holding prompt overrides. Unset/empty uses "
            "the built-in prompts. Default: prompt."
        ),
        "required": False,
    },
}


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """Return (key, value) if ``line`` is a KEY=value assignment, else None."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key, _, raw = stripped.partition("=")
    key = key.strip()
    value = raw.strip().strip('"').strip("'")
    return key, value


def read_config(
    env_path: Path, keys: Optional[frozenset[str]] = None
) -> dict[str, dict]:
    """Parse ``env_path`` into a schema-annotated config dict.

    Secrets are included with ``value=None`` and ``is_set`` reflecting whether
    the key is present and non-empty in the file.

    Arguments:
        env_path: Path to the ``.env``-format file.
        keys: When given, restrict the result to this key set (scopes the view to
            app vs. profile config). Unknown-key passthrough and the profile
            registry are omitted in scoped mode.
    Returns:
        Dict mapping key → {value, is_set, is_secret, label, group, description,
        required}.
    """
    file_values: dict[str, str] = {}
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if parsed:
                file_values[parsed[0]] = parsed[1]

    result: dict[str, dict] = {}
    for key, meta in _SCHEMA.items():
        if keys is not None and key not in keys:
            continue
        raw_value = file_values.get(key, "")
        secret = is_secret(key)
        result[key] = {
            "value": None if secret else raw_value,
            "is_set": bool(raw_value),
            "is_secret": secret,
            **meta,
        }
    # Surface unknown non-secret keys only in the full (unscoped) view; never the
    # profile registry, which is managed via the profiles API.
    if keys is None:
        for key, raw_value in file_values.items():
            if (
                key not in result
                and not is_secret(key)
                and not key.startswith("JOBJOB_")
            ):
                result[key] = {
                    "value": raw_value,
                    "is_set": bool(raw_value),
                    "is_secret": False,
                    "label": key,
                    "group": "Other",
                    "description": "",
                    "required": False,
                }
    return result


def write_config(
    env_path: Path,
    updates: dict[str, str],
    allowed_keys: Optional[frozenset[str]] = None,
) -> None:
    """Write ``updates`` to ``env_path``, preserving comments and secret lines.

    Only non-secret keys in ``updates`` are written. Secret lines in the file
    are preserved verbatim. New keys not yet in the file are appended.

    Arguments:
        env_path: Path to the ``.env``-format file.
        updates: Dict of key → new string value (only non-secrets).
        allowed_keys: When given, reject any update key outside this set — used to
            enforce the app/profile scope boundary (zero overlap).
    Raises:
        ValueError: If any update targets a secret key or a key outside
            ``allowed_keys``.
    """
    for key in updates:
        if is_secret(key):
            raise ValueError(f"Cannot update secret key via API: {key}")
        if allowed_keys is not None and key not in allowed_keys:
            raise ValueError(f"Key not allowed in this config scope: {key}")

    lines = (
        env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    )
    updated_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        parsed = _parse_env_line(line)
        if parsed:
            key, _ = parsed
            if key in updates and not is_secret(key):
                new_lines.append(f'{key}="{updates[key]}"')
                updated_keys.add(key)
                continue
        new_lines.append(line)

    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f'{key}="{value}"')

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def remove_config_key(env_path: Path, key: str) -> bool:
    """Remove every assignment of ``key`` from ``env_path``. Return True if removed.

    Used to unregister a profile (``JOBJOB_PROFILE_<NAME>``) from the app config.
    Comments and other keys are preserved. Refuses secret keys for symmetry with
    ``write_config``.
    """
    if is_secret(key):
        raise ValueError(f"Cannot remove secret key via API: {key}")
    if not env_path.is_file():
        return False
    removed = False
    new_lines: list[str] = []
    for line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed and parsed[0] == key:
            removed = True
            continue
        new_lines.append(line)
    if removed:
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return removed
