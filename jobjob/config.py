#!/usr/bin/env python3
"""Centralized runtime configuration in two disjoint tiers.

- **App config** (``config/.env``, gitignored, machine-local): the single jobjob
  instance — secrets, local paths, output IDs, and the profile registry.
- **Profile config** (``<profile-repo>/config/.profile``, committed): the active
  profile's applicant identity and resume template.

The two key sets are **disjoint** (``APP_KEYS`` / ``PROFILE_KEYS``) with no
fallback between them; ``load_settings`` validates that neither file carries the
other's keys. The entry point calls ``load_settings`` once and passes concrete
values each function needs — feature modules never import ``Settings``.

NOTE: the google credential/token env-var names are owned by ``jobjob.loader.auth``
    and re-used here so they are defined in exactly one place.
"""

import dataclasses as dcs
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from jobjob.loader.auth import (
    ENV_GOOGLE_CREDENTIALS_FILE,
    ENV_GOOGLE_TOKEN_FILE,
)
from jobjob.loader.profiles import (
    PROFILE_REGISTRY_PREFIX,
    active_profile_name,
    profile_config_file,
    read_env_keys,
    resolve_active_profile_dir,
)
from jobjob.structure.applicant import Applicant

# App config: machine-local, gitignored. Lives under config/ (not a root .env,
# which autoenv would auto-source).
DEFAULT_APP_CONFIG = Path("config/.env")
DEFAULT_MODEL = "claude-sonnet-4-6"

# Env-var names (single source of truth)
ENV_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"
ENV_MODEL = "CLAUDE_MODEL"
ENV_CACHE_ENABLED = "CLAUDE_CACHE_ENABLED"
ENV_CACHE_DIR = "CACHE_DIR"
ENV_RESUME_TEMPLATE_ID = "RESUME_TEMPLATE_ID"

# Per-component input/output keys. Each component (Applications = apply, Enrichment =
# enrich) has its own INPUT (local working dir) and OUTPUT (where results land).
ENV_APPLICATIONS_INPUT_DIR = "APPLICATIONS_INPUT_DIR"
ENV_APPLICATIONS_OUTPUT_DIR = "APPLICATIONS_OUTPUT_DIR"
ENV_APPLICATIONS_OUTPUT_DRIVE_ID = "APPLICATIONS_OUTPUT_DRIVE_ID"
ENV_ENRICHMENT_INPUT_DIR = "ENRICHMENT_INPUT_DIR"
ENV_ENRICHMENT_OUTPUT_SHEET_ID = "ENRICHMENT_OUTPUT_SHEET_ID"

# Deprecated pre-2.4 names, still read as a fallback (see RENAMED_KEYS and
# _env_first). Kept readable through the 2.x line; removed at a future major.
ENV_DATA_DIR = "DATA_DIR"
ENV_APPLICATIONS_LOCAL_DIR = "APPLICATIONS_LOCAL_DIR"
ENV_APPLICATIONS_FOLDER_ID = "APPLICATIONS_FOLDER_ID"
ENV_LINKEDIN_SHEET_ID = "LINKEDIN_SHEET_ID"

# Old → new renames. The migration rewrites the old keys to the new ones in
# ``config/.env`` (best-effort cleanup); the load-time fallback in ``_env_first``
# is what actually keeps old configs — including env-var-only setups the file
# rewrite can't reach — working until the keys are removed.
RENAMED_KEYS: dict[str, str] = {
    ENV_DATA_DIR: ENV_APPLICATIONS_INPUT_DIR,
    ENV_APPLICATIONS_LOCAL_DIR: ENV_APPLICATIONS_OUTPUT_DIR,
    ENV_APPLICATIONS_FOLDER_ID: ENV_APPLICATIONS_OUTPUT_DRIVE_ID,
    ENV_LINKEDIN_SHEET_ID: ENV_ENRICHMENT_OUTPUT_SHEET_ID,
}

DEFAULT_INPUT_DIR = Path("data")
ENV_APPLICANT_NAME = "APPLICANT_NAME"
ENV_APPLICANT_PHONE = "APPLICANT_PHONE"
ENV_APPLICANT_EMAIL = "APPLICANT_EMAIL"
ENV_APPLICANT_LINKEDIN = "APPLICANT_LINKEDIN"
# Optional domain/industry context for this profile (e.g. "science journalism").
# Injected into the resume-objective prompt so the model describes the target
# company accurately; left out of the prompt entirely when unset.
ENV_INDUSTRY = "INDUSTRY"

# Per-profile resource directory names (relative to the profile repo). Optional;
# each falls back to its conventional default so existing profiles keep working.
# Read by jobjob.loader.location when resolving the active profile's resources.
ENV_CONTENT_DIR = "CONTENT_DIR"
ENV_REFERENCE_DIR = "REFERENCE_DIR"
ENV_PROMPT_DIR = "PROMPT_DIR"

# Config tiers — disjoint by construction; enforced by _validate_scopes.
# APP: one jobjob instance (secrets, local paths, output IDs, registry).
APP_KEYS = frozenset(
    {
        ENV_ANTHROPIC_API_KEY,
        ENV_MODEL,
        ENV_CACHE_ENABLED,
        ENV_CACHE_DIR,
        ENV_GOOGLE_CREDENTIALS_FILE,
        ENV_GOOGLE_TOKEN_FILE,
        # Per-component input/output keys.
        ENV_APPLICATIONS_INPUT_DIR,
        ENV_APPLICATIONS_OUTPUT_DIR,
        ENV_APPLICATIONS_OUTPUT_DRIVE_ID,
        ENV_ENRICHMENT_INPUT_DIR,
        ENV_ENRICHMENT_OUTPUT_SHEET_ID,
        # Deprecated aliases — still accepted so existing configs keep validating.
        ENV_DATA_DIR,
        ENV_APPLICATIONS_LOCAL_DIR,
        ENV_APPLICATIONS_FOLDER_ID,
        ENV_LINKEDIN_SHEET_ID,
    }
)
# PROFILE: the active content set (identity + resume template + resource dir names).
# No local paths (the resource dirs are names relative to the profile repo).
PROFILE_KEYS = frozenset(
    {
        ENV_APPLICANT_NAME,
        ENV_APPLICANT_PHONE,
        ENV_APPLICANT_EMAIL,
        ENV_APPLICANT_LINKEDIN,
        ENV_RESUME_TEMPLATE_ID,
        ENV_INDUSTRY,
        ENV_CONTENT_DIR,
        ENV_REFERENCE_DIR,
        ENV_PROMPT_DIR,
    }
)

# Conventional defaults for the per-profile resource dirs (used by the loaders and
# the config UI so an unset key behaves exactly as before).
DEFAULT_CONTENT_DIR = "content"
DEFAULT_REFERENCE_DIR = "reference"
DEFAULT_PROMPT_DIR = "prompt"

_TRUE_VALUES = ("true", "1", "yes")


@dcs.dataclass(frozen=True)
class GoogleSettings:
    """Google Drive/Docs credential + template settings.

    Attributes:
        credentials_file: OAuth client-secrets JSON path.
        token_file: Pickled-token path.
        template_id: Resume-template Google Doc id.
    """

    credentials_file: Optional[Path] = None
    token_file: Optional[Path] = None
    template_id: Optional[str] = None


@dcs.dataclass(frozen=True)
class Settings:
    """Aggregated runtime settings (built once at the entry point).

    Inputs/outputs are modeled per component (Applications = apply, Enrichment =
    enrich). Inputs are local-only for now.

    Attributes:
        applicant: Applicant identity.
        model: Claude model id.
        anthropic_api_key: Anthropic API key.
        cache_enabled: Default response-cache toggle.
        google: Google credential + resume-template settings.
        applications_input_dir: Local root holding ``jobs/``, ``profiles/`` and
            ``completed/`` for the apply flow — where a processed JD moves on
            completion.
        applications_output_dir: Local synced Google Drive applications mirror; when
            set, the completed-applications list is read from here instead of Drive.
        applications_output_drive_id: Drive applications-root folder id (output).
        enrichment_input_dir: Local input root for the enrich flow; defaults to
            ``applications_input_dir`` when its own key is unset.
        enrichment_output_sheet_id: Spreadsheet id for the contacts sheet (enrich).
        industry: Optional domain/industry context for the active profile, injected
            into the resume-objective prompt; None means no domain hint is added.
    """

    applicant: Applicant
    model: str = DEFAULT_MODEL
    anthropic_api_key: Optional[str] = None
    cache_enabled: bool = True
    google: GoogleSettings = dcs.field(default_factory=GoogleSettings)
    applications_input_dir: Path = DEFAULT_INPUT_DIR
    applications_output_dir: Optional[Path] = None
    applications_output_drive_id: Optional[str] = None
    enrichment_input_dir: Path = DEFAULT_INPUT_DIR
    enrichment_output_sheet_id: Optional[str] = None
    profile_name: Optional[str] = None
    profile_dir: Optional[Path] = None
    industry: Optional[str] = None


# Deprecated keys we've already warned about this process — keep the log to once each.
_DEPRECATION_WARNED: set[str] = set()


def _warn_deprecated(old_key: str, new_key: str) -> None:
    """Log a one-time deprecation warning when a deprecated config key is used."""
    if old_key not in _DEPRECATION_WARNED:
        _DEPRECATION_WARNED.add(old_key)
        logging.getLogger("jobjob.config").warning(
            "Config key %s is deprecated — rename it to %s. The old name still "
            "works for now but will be removed in a future major release.",
            old_key,
            new_key,
        )


def _env_first(
    new_key: str,
    old_key: Optional[str] = None,
    *,
    overrides: Optional[dict[str, str]] = None,
) -> Optional[str]:
    """Resolve a setting across its new and deprecated names, honoring source priority.

    Precedence, highest first: environment variable (new name, then deprecated) →
    config-file value (new name, then deprecated). ``overrides`` is a snapshot of
    ``os.environ`` taken BEFORE any ``.env`` file was sourced, so a value set directly
    in the environment outranks the config file even across the rename (env > file).
    When ``overrides`` is None the two layers collapse to ``os.environ`` (new before
    deprecated). Using a deprecated name logs a one-time warning.

    This is the compatibility mechanism for the Batch C rename: it covers values in
    ``config/.env`` AND values provided directly as environment variables
    (shell/launchd/Docker/CI), which a file migration can't reach.
    """
    layers: list[dict[str, str]] = []
    if overrides is not None:
        layers.append(overrides)  # real env vars (pre-dotenv) — top precedence
    layers.append(os.environ)  # env + config-file values merged by load_dotenv
    for layer in layers:
        for key in (new_key, old_key):
            if key is None:
                continue
            value = layer.get(key)
            if value is not None and value.strip():
                if key == old_key:
                    _warn_deprecated(old_key, new_key)
                return value
    return os.environ.get(new_key)


def _path(value: Optional[str]) -> Optional[Path]:
    # Tolerate a value pasted with surrounding quotes (e.g. via the config UI).
    if value:
        value = value.strip().strip("\"'").strip()
    return Path(value).expanduser() if value else None


def _text(value: Optional[str]) -> Optional[str]:
    """Return a trimmed, unquoted string, or None when empty (for id-style values)."""
    if value:
        value = value.strip().strip("\"'").strip()
    return value or None


def _bool(value: Optional[str], default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


def _validate_scopes(app_config: Path, profile_config: Optional[Path]) -> None:
    """Raise if app/profile configs carry each other's keys (zero-overlap rule).

    Arguments:
        app_config: Path to the app ``config/.env``.
        profile_config: Path to the active ``config/.profile``, or None.
    Raises:
        ValueError: If the app config holds profile-owned keys, or the profile
            config holds app-owned or registry keys.
    """
    app_misplaced = read_env_keys(app_config) & PROFILE_KEYS
    if app_misplaced:
        raise ValueError(
            f"App config {app_config} contains profile-owned keys "
            f"{sorted(app_misplaced)} — move them to the profile's config/.profile."
        )
    if profile_config is not None:
        prof_keys = read_env_keys(profile_config)
        prof_misplaced = (prof_keys & APP_KEYS) | {
            k
            for k in prof_keys
            if k.startswith(PROFILE_REGISTRY_PREFIX) or k == "JOBJOB_ACTIVE_PROFILE"
        }
        if prof_misplaced:
            raise ValueError(
                f"Profile config {profile_config} contains app-owned keys "
                f"{sorted(prof_misplaced)} — move them to the app config/.env."
            )


def load_settings(app_config: Path = DEFAULT_APP_CONFIG) -> Settings:
    """Load settings from the app config plus the active profile config.

    Sources ``app_config`` (machine-local), resolves the active profile from the
    registry it declares, then sources that profile's ``config/.profile``. The
    two key sets are validated as disjoint. ``load_dotenv`` is a no-op on a
    missing file, so the ambient environment is used as-is when a file is absent.

    Arguments:
        app_config: Path to the app ``config/.env``. Defaults to ``config/.env``.
    Returns:
        A populated Settings.
    Raises:
        ValueError: If a configured active profile dir is missing, or the two
            configs violate the zero-overlap rule.
    """
    # Snapshot real environment variables before sourcing any .env file so a value set
    # directly in the environment outranks the config file (priority: CLI > env > file
    # > default), even across the deprecated→new key rename. CLI overrides are applied
    # above this, at each command's entry point (e.g. ``args.sheet_id or settings.…``).
    env_overrides = dict(os.environ)
    load_dotenv(app_config, encoding="utf-8")
    profile_dir = resolve_active_profile_dir()
    profile_config: Optional[Path] = None
    if profile_dir is not None:
        if not profile_dir.is_dir():
            raise ValueError(
                f"Active profile dir not found: {profile_dir} "
                f"(check the JOBJOB_PROFILE_* registry in {app_config})."
            )
        # Clear any prior profile's keys so a re-load (e.g. a profile switch in the
        # webapp) doesn't inherit stale values the new profile may omit.
        for key in PROFILE_KEYS:
            os.environ.pop(key, None)
        profile_config = profile_config_file(profile_dir)
        load_dotenv(profile_config, encoding="utf-8")
    _validate_scopes(app_config, profile_config)

    # NOTE: unset applicant fields stay None (no PII default); contact_line and the
    #   document builders treat None as "omit".
    applicant = Applicant(
        name=os.environ.get(ENV_APPLICANT_NAME),
        phone=os.environ.get(ENV_APPLICANT_PHONE),
        email=os.environ.get(ENV_APPLICANT_EMAIL),
        linkedin=os.environ.get(ENV_APPLICANT_LINKEDIN),
    )
    # Applications input: new key → deprecated DATA_DIR → default. Enrichment input:
    # its own key, else it inherits the fully-resolved applications input (so a
    # config that only set the old DATA_DIR keeps both flows pointed there, exactly
    # as before). See the precedence table in docs/setup.md.
    applications_input_dir = (
        _path(
            _env_first(
                ENV_APPLICATIONS_INPUT_DIR, ENV_DATA_DIR, overrides=env_overrides
            )
        )
        or DEFAULT_INPUT_DIR
    )
    enrichment_input_dir = (
        _path(os.environ.get(ENV_ENRICHMENT_INPUT_DIR)) or applications_input_dir
    )
    return Settings(
        applicant=applicant,
        model=os.environ.get(ENV_MODEL) or DEFAULT_MODEL,
        anthropic_api_key=os.environ.get(ENV_ANTHROPIC_API_KEY),
        cache_enabled=_bool(os.environ.get(ENV_CACHE_ENABLED), default=True),
        google=GoogleSettings(
            credentials_file=_path(os.environ.get(ENV_GOOGLE_CREDENTIALS_FILE)),
            token_file=_path(os.environ.get(ENV_GOOGLE_TOKEN_FILE)),
            template_id=os.environ.get(ENV_RESUME_TEMPLATE_ID),
        ),
        applications_input_dir=applications_input_dir,
        applications_output_dir=_path(
            _env_first(
                ENV_APPLICATIONS_OUTPUT_DIR,
                ENV_APPLICATIONS_LOCAL_DIR,
                overrides=env_overrides,
            )
        ),
        applications_output_drive_id=_text(
            _env_first(
                ENV_APPLICATIONS_OUTPUT_DRIVE_ID,
                ENV_APPLICATIONS_FOLDER_ID,
                overrides=env_overrides,
            )
        ),
        enrichment_input_dir=enrichment_input_dir,
        enrichment_output_sheet_id=_text(
            _env_first(
                ENV_ENRICHMENT_OUTPUT_SHEET_ID,
                ENV_LINKEDIN_SHEET_ID,
                overrides=env_overrides,
            )
        ),
        profile_name=active_profile_name(),
        profile_dir=profile_dir,
        industry=(os.environ.get(ENV_INDUSTRY) or "").strip() or None,
    )


# __END__
