#!/usr/bin/env python3
"""Prompt-template editor API: view, override, and reset the AI prompts per profile.

A prompt is editable per active profile: a saved override is written to the profile's
``prompt/<stem>.txt`` and shadows the bundled default (mirrors loader.location's
override resolution). Reset deletes the override, falling back to the default. Only the
prompts in the shared catalog are exposed, and only an owned, writable profile can save.
"""

from pathlib import Path
from string import Template

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jobjob.loader.location import package_prompt_dir
from jobjob.loader.prompt_catalog import CATALOG_BY_STEM, PROMPT_CATALOG, PromptInfo
from security import safe_path

router = APIRouter()


class PromptUpdate(BaseModel):
    content: str


def _guard_writable(request: Request) -> Path:
    """Return the writable profile ``prompt/`` dir, or raise if not editable.

    Refuses when there is no active profile or it is the read-only bundled example —
    an override has nowhere safe to live. Steers the user to an owned profile.
    """
    if getattr(request.app.state, "profile_read_only", False):
        raise HTTPException(
            status_code=403,
            detail=(
                "The example profile is read-only. Duplicate it (Settings → Profiles "
                "→ Duplicate) to customize its prompts."
            ),
        )
    profile_dir = getattr(request.app.state, "profile_dir", None)
    if not profile_dir:
        raise HTTPException(
            status_code=403,
            detail="No active profile to save prompt overrides into.",
        )
    return safe_path(Path(profile_dir) / "prompt")


def _override_path(request: Request, stem: str) -> Path | None:
    """The active profile's override path for ``stem`` (None when no profile)."""
    profile_dir = getattr(request.app.state, "profile_dir", None)
    if not profile_dir:
        return None
    return safe_path(Path(profile_dir) / "prompt" / f"{stem}.txt")


def _default_text(stem: str) -> str:
    # The bundled default lives in the trusted package dir (outside the user sandbox),
    # and ``stem`` is validated against the catalog, so no safe_path guard is needed.
    return (package_prompt_dir() / f"{stem}.txt").read_text(encoding="utf-8")


def _view(request: Request, info: PromptInfo) -> dict:
    """Build the editor view for one prompt: effective text, default, placeholders."""
    default = _default_text(info.stem)
    override = _override_path(request, info.stem)
    overridden = bool(override and override.is_file())
    content = override.read_text(encoding="utf-8") if overridden else default
    editable = not getattr(request.app.state, "profile_read_only", False) and bool(
        getattr(request.app.state, "profile_dir", None)
    )
    return {
        "stem": info.stem,
        "title": info.title,
        "kind": info.kind,
        "description": info.description,
        # Placeholders are derived from the live text so the UI can list exactly what
        # this prompt supports — including any the user added in an override.
        "placeholders": sorted(Template(content).get_identifiers()),
        "content": content,
        "default": default,
        "overridden": overridden,
        "editable": editable,
    }


def _require_known(stem: str) -> PromptInfo:
    info = CATALOG_BY_STEM.get(stem)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Unknown prompt: {stem}")
    return info


@router.get("")
def list_prompts(request: Request) -> list[dict]:
    """List every editable prompt with its effective text and metadata."""
    return [_view(request, info) for info in PROMPT_CATALOG]


@router.put("/{stem}")
def save_prompt(stem: str, body: PromptUpdate, request: Request) -> dict:
    """Write a prompt override into the active profile's ``prompt/`` dir."""
    info = _require_known(stem)
    prompt_dir = _guard_writable(request)
    prompt_dir.mkdir(exist_ok=True)
    safe_path(prompt_dir / f"{stem}.txt").write_text(body.content, encoding="utf-8")
    return _view(request, info)


@router.delete("/{stem}")
def reset_prompt(stem: str, request: Request) -> dict:
    """Delete the override for ``stem``, reverting to the bundled default."""
    info = _require_known(stem)
    _guard_writable(request)
    override = _override_path(request, stem)
    if override and override.is_file():
        override.unlink()
    return _view(request, info)


# __END__
