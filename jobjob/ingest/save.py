#!/usr/bin/env python3
"""Persist an imported resume draft into content TOML and reference docs.

These functions take explicit destination paths so the same logic serves both the
CLI (paths resolved via ``jobjob.loader.location``) and the webapp (paths resolved via
``app.state`` / the active profile). ``mode`` is "replace" (overwrite the
existing items) or "append" (add to them).
"""

from collections.abc import Iterable
from pathlib import Path

import tomlkit

from jobjob.ingest.resume_import import SAVE_MODES
from jobjob.structure.experience import Role
from jobjob.structure.highlight import Highlight
from jobjob.structure.skill import Skill


def _check_mode(mode: str) -> None:
    if mode not in SAVE_MODES:
        raise ValueError(f"Unknown save mode {mode!r}; expected one of {SAVE_MODES}")


def _ensure_table(doc: tomlkit.TOMLDocument, keys: list[str]):
    """Return the nested table at ``keys``, creating tables as needed."""
    node: object = doc
    for key in keys:
        if key not in node:  # type: ignore[operator]
            node[key] = tomlkit.table()  # type: ignore[index]
        node = node[key]  # type: ignore[index]
    return node


def _load_or_new(path: Path) -> tomlkit.TOMLDocument:
    if path.is_file():
        return tomlkit.loads(path.read_text(encoding="utf-8"))
    return tomlkit.document()


def _highlight_item(highlight: Highlight):
    item = tomlkit.table()
    item["context"] = highlight.context
    if highlight.topic:
        item["topic"] = highlight.topic
    item["enabled"] = highlight.enabled
    item["text"] = tomlkit.string(highlight.text.strip(), multiline=True)
    item["keywords"] = list(highlight.keywords)
    return item


def _skill_item(skill: Skill):
    item = tomlkit.table()
    item["label"] = skill.label
    item["text"] = skill.text
    item["keywords"] = list(skill.keywords)
    return item


def _role_item(role: Role):
    item = tomlkit.table()
    item["company"] = role.company
    item["title"] = role.title
    item["location"] = role.location
    item["start"] = role.start
    item["end"] = role.end
    item["current"] = role.current
    item["description"] = tomlkit.string(role.description.strip(), multiline=True)
    return item


def _save_aot(
    path: Path,
    table_keys: list[str],
    array_key: str,
    items: Iterable,
    *,
    mode: str,
) -> int:
    """Append/replace an array-of-tables in a TOML file, preserving other content.

    Returns the number of items written.
    """
    _check_mode(mode)
    doc = _load_or_new(path)
    table = _ensure_table(doc, table_keys)
    if array_key not in table or mode == "replace":
        table[array_key] = tomlkit.aot()
    array = table[array_key]
    count = 0
    for item in items:
        array.append(item)
        count += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return count


def save_highlights(path: Path, highlights: Iterable[Highlight], *, mode: str) -> int:
    """Write highlights into ``[tool.highlights.highlight]`` of ``path``."""
    return _save_aot(
        path,
        ["tool", "highlights"],
        "highlight",
        (_highlight_item(h) for h in highlights),
        mode=mode,
    )


def save_skills(path: Path, skills: Iterable[Skill], *, mode: str) -> int:
    """Write skills into ``[tool.skills.skill]`` of ``path``."""
    return _save_aot(
        path,
        ["tool", "skills"],
        "skill",
        (_skill_item(s) for s in skills),
        mode=mode,
    )


def save_experience(path: Path, roles: Iterable[Role], *, mode: str) -> int:
    """Write roles into ``[[tool.experience.role]]`` of ``path``."""
    return _save_aot(
        path,
        ["tool", "experience"],
        "role",
        (_role_item(r) for r in roles),
        mode=mode,
    )


def save_background(path: Path, text: str, *, mode: str) -> None:
    """Write the background narrative to ``path`` (a reference markdown file)."""
    _check_mode(mode)
    text = text.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "append" and path.is_file():
        existing = path.read_text(encoding="utf-8").rstrip()
        if existing:
            text = f"{existing}\n\n{text}"
    path.write_text(text + "\n", encoding="utf-8")


# __END__
