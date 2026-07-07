#!/usr/bin/env python3
"""Static content API: read and write TOML files and reference documents."""

import tomllib
from pathlib import Path
from typing import Any

import tomlkit
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from jobjob.loader.loadcontent import load_skills
from jobjob.skills.suggest import aggregate_candidates, suggestions_as_dicts
from security import safe_path

router = APIRouter()

_TOML_FILES = {
    "highlights": "static/example/content/highlights.toml",
    "skills": "static/example/content/skills.toml",
    "templates": "static/example/content/templates.toml",
    "experience": "static/example/content/experience.toml",
}
_REFERENCE_BASE = "static/example/reference"

# Maps TOML name → (table path segments, item array key).
# e.g. highlights lives at doc["tool"]["highlights"]["highlight"][i]
_ITEM_PATH: dict[str, tuple[list[str], str]] = {
    "highlights": (["tool", "highlights"], "highlight"),
    "skills": (["tool", "skills"], "skill"),
    "templates": (["tool", "templates"], "template"),
    "experience": (["tool", "experience"], "role"),
}


def _repo_root(request: Request) -> Path:
    return request.app.state.repo_root


def _guard_writable(request: Request) -> None:
    """Refuse writes when the active profile is the read-only bundled example.

    The example lives in the read-only package install (site-packages under pipx), so
    edits would either fail or mutate shared demo content. Steer the user to duplicate
    it into a profile they own.
    """
    if getattr(request.app.state, "profile_read_only", False):
        raise HTTPException(
            status_code=403,
            detail=(
                "The example profile is read-only. Duplicate it (Settings → Profiles "
                "→ Duplicate) to make an editable copy."
            ),
        )


def _toml_path(request: Request, name: str) -> Path:
    """Resolve a content TOML path: the active profile's ``content/`` if present,
    else the bundled example ``static/example/content`` (mirrors loader.location)."""
    filename = Path(_TOML_FILES[name]).name
    profile_dir = request.app.state.profile_dir
    if profile_dir and (Path(profile_dir) / "content").is_dir():
        return safe_path(Path(profile_dir) / "content" / filename)
    return safe_path(_repo_root(request) / _TOML_FILES[name])


def _reference_base(request: Request) -> Path:
    """Resolve the reference dir: the active profile's ``reference/`` if present,
    else the bundled example ``static/example/reference``."""
    profile_dir = request.app.state.profile_dir
    if profile_dir and (Path(profile_dir) / "reference").is_dir():
        return safe_path(Path(profile_dir) / "reference")
    return safe_path(_repo_root(request) / _REFERENCE_BASE)


class TomlUpdate(BaseModel):
    content: str


class ItemUpdate(BaseModel):
    fields: dict[str, Any]


class ConfigUpdate(BaseModel):
    fields: dict[str, Any]


class ReferenceUpdate(BaseModel):
    content: str


@router.get("/skills/suggestions")
def get_skill_suggestions(request: Request) -> list[dict]:
    """Aggregate evidence-backed skills-file candidates across applications.

    Same rules as ``jobjob skills suggest``: evidenced in a saved skills
    analysis, canonical, and undeclared in the active profile's skills file.
    """
    root = request.app.state.settings.get("applications_output_dir")
    if not root:
        raise HTTPException(
            status_code=400,
            detail=(
                "Local applications mirror not configured "
                "(set APPLICATIONS_OUTPUT_DIR)."
            ),
        )
    skills_path = _toml_path(request, "skills")
    try:
        skill_set = load_skills(skills_path) if skills_path.is_file() else None
    except (OSError, ValueError):
        # Unreadable skills file degrades to "nothing declared yet".
        skill_set = None
    try:
        suggestions = aggregate_candidates(Path(root), skill_set=skill_set)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return suggestions_as_dicts(suggestions)


@router.get("/toml/{name}")
def get_toml(name: str, request: Request) -> dict:
    """Return the raw TOML string and parsed data for a known content file."""
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    path = _toml_path(request, name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{name}.toml not found")
    raw = path.read_text(encoding="utf-8")
    try:
        parsed = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        parsed = None
        parse_error = str(exc)
    else:
        parse_error = None
    return {"name": name, "content": raw, "parsed": parsed, "parse_error": parse_error}


@router.put("/toml/{name}")
def update_toml(name: str, body: TomlUpdate, request: Request) -> dict:
    """Validate and write updated raw TOML to the content file."""
    _guard_writable(request)
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    try:
        tomllib.loads(body.content)
    except tomllib.TOMLDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid TOML: {exc}")
    path = _toml_path(request, name)
    path.write_text(body.content, encoding="utf-8")
    return {"name": name, "content": body.content}


@router.patch("/toml/{name}/items/{index}")
def update_toml_item(name: str, index: int, body: ItemUpdate, request: Request) -> dict:
    """Update a single item in a TOML array-of-tables, preserving formatting.

    Uses tomlkit so comments and surrounding structure are kept intact.
    Only the keys present in ``body.fields`` are touched.

    Arguments:
        name: TOML file name (highlights, skills, templates).
        index: Zero-based index of the item in its array.
        body: Dict of field names → new values.
    """
    _guard_writable(request)
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    table_keys, array_key = _ITEM_PATH[name]
    path = _toml_path(request, name)

    try:
        doc = tomlkit.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not parse TOML: {exc}")

    # Navigate to the array.
    node: Any = doc
    for key in table_keys:
        node = node[key]
    items = node[array_key]

    if index < 0 or index >= len(items):
        raise HTTPException(
            status_code=404,
            detail=f"Item index {index} out of range (0–{len(items)-1})",
        )

    item = items[index]
    for field, value in body.fields.items():
        if field not in item:
            raise HTTPException(
                status_code=422, detail=f"Unknown field '{field}' for {name} item"
            )
        item[field] = value

    path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    # Return the full refreshed file so the frontend can re-render.
    raw = path.read_text(encoding="utf-8")
    parsed = tomllib.loads(raw)
    return {"name": name, "content": raw, "parsed": parsed, "parse_error": None}


# Section fields the UI may set on a [[tool.templates.section]] entry. ``enabled`` is
# the toggle; the others are allowed for completeness. Restricting the set keeps a typo
# from silently adding a stray key.
_SECTION_FIELDS = {"heading", "section", "enabled"}


@router.patch("/toml/templates/sections/{index}")
def update_template_section(index: int, body: ItemUpdate, request: Request) -> dict:
    """Update a section in ``[[tool.templates.section]]`` (e.g. toggle ``enabled``).

    Sections live in a separate array from the templates themselves, so they need a
    dedicated route. Flipping ``enabled`` lets the apply flow omit a section's edit
    (leaving the template text untouched). Uses tomlkit to preserve comments and
    formatting; a missing field (e.g. ``enabled`` not yet present) is added.

    Arguments:
        index: Zero-based index of the section in the array.
        body: Dict of field names → new values (subset of ``heading``/``section``/
            ``enabled``).
    """
    _guard_writable(request)
    path = _toml_path(request, "templates")

    try:
        doc = tomlkit.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not parse TOML: {exc}")

    node: Any = doc
    for key in ("tool", "templates", "section"):
        node = node.get(key) if hasattr(node, "get") else None
        if node is None:
            raise HTTPException(
                status_code=404,
                detail="No [[tool.templates.section]] array in templates.toml",
            )
    sections = node

    if index < 0 or index >= len(sections):
        raise HTTPException(
            status_code=404,
            detail=f"Section index {index} out of range (0–{len(sections)-1})",
        )

    section = sections[index]
    for field, value in body.fields.items():
        if field not in _SECTION_FIELDS:
            raise HTTPException(
                status_code=422, detail=f"Unknown section field '{field}'"
            )
        section[field] = value

    path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    raw = path.read_text(encoding="utf-8")
    parsed = tomllib.loads(raw)
    return {"name": "templates", "content": raw, "parsed": parsed, "parse_error": None}


@router.patch("/toml/{name}/config")
def update_toml_config(name: str, body: ConfigUpdate, request: Request) -> dict:
    """Update tool-level scalar config (e.g. ``default_number``) in ``[tool.<name>]``.

    Only existing scalar keys may be set; the item array is never touched. Uses
    tomlkit so comments and formatting are preserved.
    """
    _guard_writable(request)
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    table_keys, array_key = _ITEM_PATH[name]
    path = _toml_path(request, name)

    try:
        doc = tomlkit.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not parse TOML: {exc}")

    node: Any = doc
    for key in table_keys:
        node = node[key]

    for field, value in body.fields.items():
        if field == array_key or field not in node:
            raise HTTPException(
                status_code=422, detail=f"Unknown config key '{field}' for {name}"
            )
        node[field] = value

    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    raw = path.read_text(encoding="utf-8")
    parsed = tomllib.loads(raw)
    return {"name": name, "content": raw, "parsed": parsed, "parse_error": None}


@router.get("/reference")
def list_reference(request: Request) -> list[dict]:
    """List all reference files, excluding dotfiles and dotfile directories."""
    base = _reference_base(request)
    if not base.is_dir():
        return []
    items = []
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        # Skip dotfiles and any file inside a hidden directory.
        if any(part.startswith(".") for part in f.parts):
            continue
        if f.name.startswith("."):
            continue
        try:
            rel = str(f.relative_to(base))
        except ValueError:
            continue
        items.append({"path": rel, "name": f.name, "extension": f.suffix.lower()})
    return items


@router.get("/reference/{file_path:path}")
def get_reference_file(file_path: str, request: Request) -> dict:
    """Return the text content of a reference file."""
    path = safe_path(_reference_base(request) / file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if path.suffix.lower() == ".pdf":
        raise HTTPException(status_code=415, detail="PDF preview not supported here")
    return {"path": file_path, "content": path.read_text(encoding="utf-8")}


@router.put("/reference/{file_path:path}")
def update_reference_file(
    file_path: str, body: ReferenceUpdate, request: Request
) -> dict:
    """Write updated text content to a reference file."""
    _guard_writable(request)
    path = safe_path(_reference_base(request) / file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    path.write_text(body.content, encoding="utf-8")
    return {"path": file_path, "content": body.content}
