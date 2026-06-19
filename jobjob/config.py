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
ENV_APPLICATIONS_FOLDER_ID = "APPLICATIONS_FOLDER_ID"
ENV_APPLICATIONS_LOCAL_DIR = "APPLICATIONS_LOCAL_DIR"
ENV_DATA_DIR = "DATA_DIR"
ENV_LINKEDIN_SHEET_ID = "LINKEDIN_SHEET_ID"

DEFAULT_DATA_DIR = Path("data")
ENV_APPLICANT_NAME = "APPLICANT_NAME"
ENV_APPLICANT_PHONE = "APPLICANT_PHONE"
ENV_APPLICANT_EMAIL = "APPLICANT_EMAIL"
ENV_APPLICANT_LINKEDIN = "APPLICANT_LINKEDIN"

# Config tiers — disjoint by construction; enforced by _validate_scopes.
# APP: one jobjob instance (secrets, local paths, output IDs, registry).
APP_KEYS = frozenset({
    ENV_ANTHROPIC_API_KEY,
    ENV_MODEL,
    ENV_CACHE_ENABLED,
    ENV_CACHE_DIR,
    ENV_GOOGLE_CREDENTIALS_FILE,
    ENV_GOOGLE_TOKEN_FILE,
    ENV_DATA_DIR,
    ENV_APPLICATIONS_LOCAL_DIR,
    ENV_APPLICATIONS_FOLDER_ID,
    ENV_LINKEDIN_SHEET_ID,
})
# PROFILE: the active content set (identity + resume template). No local paths.
PROFILE_KEYS = frozenset({
    ENV_APPLICANT_NAME,
    ENV_APPLICANT_PHONE,
    ENV_APPLICANT_EMAIL,
    ENV_APPLICANT_LINKEDIN,
    ENV_RESUME_TEMPLATE_ID,
})

_TRUE_VALUES = ("true", "1", "yes")


@dcs.dataclass(frozen=True)
class GoogleSettings:
    """Google Drive/Docs runtime settings.

    Attributes:
        credentials_file: OAuth client-secrets JSON path.
        token_file: Pickled-token path.
        template_id: Resume-template Google Doc id.
        applications_folder_id: Applications-root folder id.
        applications_local_dir: Local path of the synced Google Drive applications
            output directory (e.g. a Google Drive for Desktop mirror). When set, the
            completed-applications list is read from here instead of the Drive API.
    """

    credentials_file: Optional[Path] = None
    token_file: Optional[Path] = None
    template_id: Optional[str] = None
    applications_folder_id: Optional[str] = None
    applications_local_dir: Optional[Path] = None


@dcs.dataclass(frozen=True)
class Settings:
    """Aggregated runtime settings (built once at the entry point).

    Attributes:
        applicant: Applicant identity.
        model: Claude model id.
        anthropic_api_key: Anthropic API key.
        cache_enabled: Default response-cache toggle.
        google: Google Drive/Docs settings.
        linkedin_sheet_id: Spreadsheet id for the contacts sheet (enrich).
        data_dir: Root holding ``jobs/``, ``profiles/`` and ``completed/`` — where a
            processed JD is moved on completion.
    """

    applicant: Applicant
    model: str = DEFAULT_MODEL
    anthropic_api_key: Optional[str] = None
    cache_enabled: bool = True
    google: GoogleSettings = dcs.field(default_factory=GoogleSettings)
    linkedin_sheet_id: Optional[str] = None
    data_dir: Path = DEFAULT_DATA_DIR
    profile_name: Optional[str] = None
    profile_dir: Optional[Path] = None


def _path(value: Optional[str]) -> Optional[Path]:
    # Tolerate a value pasted with surrounding quotes (e.g. via the config UI).
    if value:
        value = value.strip().strip("\"'").strip()
    return Path(value).expanduser() if value else None


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
            k for k in prof_keys if k.startswith(PROFILE_REGISTRY_PREFIX)
            or k == "JOBJOB_ACTIVE_PROFILE"
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
    return Settings(
        applicant=applicant,
        model=os.environ.get(ENV_MODEL) or DEFAULT_MODEL,
        anthropic_api_key=os.environ.get(ENV_ANTHROPIC_API_KEY),
        cache_enabled=_bool(os.environ.get(ENV_CACHE_ENABLED), default=True),
        google=GoogleSettings(
            credentials_file=_path(os.environ.get(ENV_GOOGLE_CREDENTIALS_FILE)),
            token_file=_path(os.environ.get(ENV_GOOGLE_TOKEN_FILE)),
            template_id=os.environ.get(ENV_RESUME_TEMPLATE_ID),
            applications_folder_id=os.environ.get(ENV_APPLICATIONS_FOLDER_ID),
            applications_local_dir=_path(os.environ.get(ENV_APPLICATIONS_LOCAL_DIR)),
        ),
        linkedin_sheet_id=os.environ.get(ENV_LINKEDIN_SHEET_ID),
        data_dir=_path(os.environ.get(ENV_DATA_DIR)) or DEFAULT_DATA_DIR,
        profile_name=active_profile_name(),
        profile_dir=profile_dir,
    )


# __END__
