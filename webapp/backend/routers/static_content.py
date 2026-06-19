#!/usr/bin/env python3
"""Static content API: read and write TOML files and reference documents."""

import tomllib
from pathlib import Path
from typing import Any

import tomlkit
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from security import safe_path

router = APIRouter()

_TOML_FILES = {
    "highlights": "static/content/highlights.toml",
    "skills": "static/content/skills.toml",
    "templates": "static/content/templates.toml",
}
_REFERENCE_BASE = "static/reference"

# Maps TOML name → (table path segments, item array key).
# e.g. highlights lives at doc["tool"]["highlights"]["highlight"][i]
_ITEM_PATH: dict[str, tuple[list[str], str]] = {
    "highlights": (["tool", "highlights"], "highlight"),
    "skills":     (["tool", "skills"],     "skill"),
    "templates":  (["tool", "templates"],  "template"),
}


def _repo_root(request: Request) -> Path:
    return request.app.state.repo_root


def _toml_path(request: Request, name: str) -> Path:
    """Resolve a content TOML path: the active profile's ``content/`` if present,
    else the repo's ``static/content`` (mirrors jobjob.loader.location)."""
    filename = Path(_TOML_FILES[name]).name
    profile_dir = request.app.state.profile_dir
    if profile_dir and (Path(profile_dir) / "content").is_dir():
        return safe_path(Path(profile_dir) / "content" / filename)
    return safe_path(_repo_root(request) / _TOML_FILES[name])


def _reference_base(request: Request) -> Path:
    """Resolve the reference dir: the active profile's ``reference/`` if present,
    else the repo's ``static/reference``."""
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


@router.get("/toml/{name}")
def get_toml(name: str, request: Request) -> dict:
    """Return the raw TOML string and parsed data for a known content file."""
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    path = _toml_path(request, name)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{name}.toml not found")
    raw = path.read_text()
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
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    try:
        tomllib.loads(body.content)
    except tomllib.TOMLDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid TOML: {exc}")
    path = _toml_path(request, name)
    path.write_text(body.content)
    return {"name": name, "content": body.content}


@router.patch("/toml/{name}/items/{index}")
def update_toml_item(
    name: str, index: int, body: ItemUpdate, request: Request
) -> dict:
    """Update a single item in a TOML array-of-tables, preserving formatting.

    Uses tomlkit so comments and surrounding structure are kept intact.
    Only the keys present in ``body.fields`` are touched.

    Arguments:
        name: TOML file name (highlights, skills, templates).
        index: Zero-based index of the item in its array.
        body: Dict of field names → new values.
    """
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    table_keys, array_key = _ITEM_PATH[name]
    path = _toml_path(request, name)

    try:
        doc = tomlkit.loads(path.read_text())
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

    path.write_text(tomlkit.dumps(doc))

    # Return the full refreshed file so the frontend can re-render.
    raw = path.read_text()
    parsed = tomllib.loads(raw)
    return {"name": name, "content": raw, "parsed": parsed, "parse_error": None}


@router.patch("/toml/{name}/config")
def update_toml_config(name: str, body: ConfigUpdate, request: Request) -> dict:
    """Update tool-level scalar config (e.g. ``default_number``) in ``[tool.<name>]``.

    Only existing scalar keys may be set; the item array is never touched. Uses
    tomlkit so comments and formatting are preserved.
    """
    if name not in _TOML_FILES:
        raise HTTPException(status_code=404, detail=f"Unknown TOML file: {name}")
    table_keys, array_key = _ITEM_PATH[name]
    path = _toml_path(request, name)

    try:
        doc = tomlkit.loads(path.read_text())
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

    path.write_text(tomlkit.dumps(doc))
    raw = path.read_text()
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
    return {"path": file_path, "content": path.read_text()}


@router.put("/reference/{file_path:path}")
def update_reference_file(
    file_path: str, body: ReferenceUpdate, request: Request
) -> dict:
    """Write updated text content to a reference file."""
    path = safe_path(_reference_base(request) / file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    path.write_text(body.content)
    return {"path": file_path, "content": body.content}
