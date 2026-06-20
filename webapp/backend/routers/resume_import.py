#!/usr/bin/env python3
"""Resume-import API: extract reusable content from a resume, review, then save.

Two steps so the user can edit before committing:
  POST /extract  — upload a resume, get a staged draft (highlights/skills/objective/
                   sections/background) back as JSON.
  POST /save     — write selected parts of the (possibly edited) draft into the active
                   profile's content TOML / reference docs, "replace" or "append".

Save targets resolve to the active profile's ``content/``/``reference/`` when one is
active, else the repo's ``static/`` — the same resolution the Static Content page uses.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from routers.static_content import _reference_base, _toml_path

from jobjob.ingest.resume_import import (
    BACKGROUND_MODES,
    SAVE_MODES,
    draft_to_dict,
    extract_resume,
    highlight_from_dict,
    skill_from_dict,
)
from jobjob.ingest.save import save_background, save_highlights, save_skills
from jobjob.loader.loadstatic import SUPPORTED_SUFFIXES

logger = logging.getLogger("jobjob.resume_import")

router = APIRouter()

# Resume documents we can read text from (image-only PDFs are rejected with guidance).
_ALLOWED_SUFFIXES = set(SUPPORTED_SUFFIXES)


def _ai_client():
    """Build the AIClient from current settings (mirrors the jobs router)."""
    from jobjob.ailib.client.anthropic import AnthropicAdapter
    from jobjob.ailib.session import AIClient
    from jobjob.config import load_settings

    settings = load_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="No Anthropic API key configured. Add one in Setup or Config first.",
        )
    return AIClient(
        AnthropicAdapter(model=settings.model, api_key=settings.anthropic_api_key)
    )


def _background_path(request: Request) -> Path:
    """Resolve the background reference file: existing ``background.*`` else ``background.md``."""
    base = _reference_base(request)
    for suffix in SUPPORTED_SUFFIXES:
        candidate = base / f"background{suffix}"
        if candidate.is_file():
            return candidate
    return base / "background.md"


@router.post("/extract")
async def extract(
    request: Request,
    file: UploadFile = File(...),
    background_mode: str = Form("fuller"),
) -> dict:
    """Extract a staged draft from an uploaded resume. Does not write anything."""
    if background_mode not in BACKGROUND_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"background_mode must be one of {sorted(BACKGROUND_MODES)}",
        )
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Upload one of: "
            + ", ".join(sorted(_ALLOWED_SUFFIXES)),
        )

    data = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        client = _ai_client()
        try:
            draft = extract_resume(
                Path(tmp.name), client, background_mode=background_mode
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        except Exception as exc:  # surface model/transport errors cleanly
            logger.exception("Resume extraction failed")
            raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}")

    result = draft_to_dict(draft)
    result["background_mode"] = background_mode
    return result


class SaveTargets(BaseModel):
    # Per-section save mode ("replace"/"append") or None to skip that section.
    highlights: Optional[str] = None
    skills: Optional[str] = None
    background: Optional[str] = None


class SaveRequest(BaseModel):
    highlights: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []
    background: str = ""
    targets: SaveTargets = SaveTargets()


def _validate_modes(targets: SaveTargets) -> None:
    for name in ("highlights", "skills", "background"):
        mode = getattr(targets, name)
        if mode is not None and mode not in SAVE_MODES:
            raise HTTPException(
                status_code=422,
                detail=f"{name} mode must be one of {sorted(SAVE_MODES)} or null",
            )


@router.post("/save")
def save(body: SaveRequest, request: Request) -> dict:
    """Write the selected parts of an (edited) draft into the active profile.

    Only sections with a non-null ``targets.<name>`` mode are written.
    """
    _validate_modes(body.targets)
    written: dict[str, Any] = {}

    if body.targets.highlights and body.highlights:
        seen: set[str] = set()
        highlights = [highlight_from_dict(h, seen) for h in body.highlights]
        path = _toml_path(request, "highlights")
        count = save_highlights(path, highlights, mode=body.targets.highlights)
        written["highlights"] = {"count": count, "mode": body.targets.highlights}

    if body.targets.skills and body.skills:
        seen_s: set[str] = set()
        skills = [skill_from_dict(s, seen_s) for s in body.skills]
        path = _toml_path(request, "skills")
        count = save_skills(path, skills, mode=body.targets.skills)
        written["skills"] = {"count": count, "mode": body.targets.skills}

    if body.targets.background and body.background.strip():
        path = _background_path(request)
        save_background(path, body.background, mode=body.targets.background)
        written["background"] = {"path": path.name, "mode": body.targets.background}

    if not written:
        raise HTTPException(
            status_code=422,
            detail="Nothing to save: select at least one section and a save mode.",
        )
    return {"saved": written}
