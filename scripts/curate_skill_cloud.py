#!/usr/bin/env python3
"""Curate the packaged skill cloud from the public ESCO API.

Traverses selected branches of the ESCO skills pillar (S: skills, K: knowledge,
plus the transversal skills/competences tree), assigns weighted category
membership per skill from its nearest mapped ancestor group, and emits
``jobjob/data/skill_cloud.toml``.

All curation constraints (roots, budgets, group/category weights, seeds,
curated aliases) live in ``scripts/curate_skill_cloud.toml`` -- edit that file
to tune, then regenerate and review the diff. Raw API responses are cached on
disk so an interrupted run resumes cheaply and re-runs are reproducible.

Licensing: ESCO data is reusable for any purpose free of charge under
Commission Decision 2011/833/EU (CC BY 4.0 terms). Attribution and an
indication of changes (this curation) ship with the generated file. See
jobjob/data/NOTICE-ESCO.md.

Usage:
    uv run python scripts/curate_skill_cloud.py \
        --output jobjob/data/skill_cloud.toml \
        --cache-dir .esco-cache
"""

import argparse
import dataclasses as dcs
import datetime as dt
import hashlib
import json
import logging
import re
import time
import tomllib
import unicodedata
from pathlib import Path
from typing import Iterator, Optional

import httpx

LOGGER = logging.getLogger("curate_skill_cloud")

DEFAULT_CONFIG = Path(__file__).resolve().parent / "curate_skill_cloud.toml"


# Configuration
# ======================================================================


@dcs.dataclass(frozen=True)
class CurationConfig:
    """Curation constraints loaded from the config TOML.

    Attributes:
        esco_version: Release recorded in the output metadata.
        api_base: ESCO API base URL.
        categories: The fixed category vocabulary.
        group_weights: Category weights keyed by ESCO group URI suffix.
        transversal_weights: Weights keyed by transversal group title.
        excluded_titles: Transversal group titles to skip entirely.
        roots: (uri, weights-or-None, budget) traversal roots, in order.
        seed_weights: Search-seeded skills (term -> weights).
        curated_aliases: Extra aliases keyed by generated entry id.
    """

    esco_version: str
    api_base: str
    categories: tuple[str, ...]
    group_weights: dict[str, dict[str, float]]
    transversal_weights: dict[str, dict[str, float]]
    excluded_titles: frozenset[str]
    roots: tuple[tuple[str, Optional[dict[str, float]], int], ...]
    seed_weights: dict[str, dict[str, float]]
    curated_aliases: dict[str, list[str]]


def load_config(path: Path) -> CurationConfig:
    """Load and lightly validate the curation config."""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    group_weights = data.get("group_weights", {})

    roots = []
    for entry in data.get("roots", []):
        weights = entry.get("weights")
        if isinstance(weights, str):  # reference into group_weights
            weights = group_weights[weights]
        roots.append((entry["uri"], weights, int(entry["budget"])))

    transversal = data.get("transversal", {})
    return CurationConfig(
        esco_version=data["esco"]["version"],
        api_base=data["esco"]["api_base"],
        categories=tuple(data["cloud"]["categories"]),
        group_weights=group_weights,
        transversal_weights=transversal.get("title_weights", {}),
        excluded_titles=frozenset(
            t.lower() for t in transversal.get("excluded_titles", [])
        ),
        roots=tuple(roots),
        seed_weights=data.get("seed_weights", {}),
        curated_aliases=data.get("curated_aliases", {}),
    )


# API access (disk-cached)
# ======================================================================


class EscoClient:
    """Cached, throttled ESCO API reader."""

    def __init__(self, cache_dir: Path, api_base: str, delay: float = 0.15) -> None:
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_base = api_base
        self.delay = delay
        self._client = httpx.Client(timeout=30.0)

    def get_resource(self, uri: str) -> Optional[dict]:
        """Fetch a skill/concept resource, from disk cache when available."""
        key = hashlib.sha256(uri.encode()).hexdigest()[:32]
        cache_path = Path(self.cache_dir, f"{key}.json")
        if cache_path.is_file():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        url = f"{self.api_base}/resource/skill"
        for attempt in range(4):
            try:
                resp = self._client.get(url, params={"uri": uri, "language": "en"})
                if resp.status_code == 200:
                    data = resp.json()
                    cache_path.write_text(
                        json.dumps(data, separators=(",", ":")), encoding="utf-8"
                    )
                    time.sleep(self.delay)
                    return data
                if resp.status_code == 404:
                    LOGGER.warning("Not found: %s", uri)
                    return None
                LOGGER.warning("HTTP %s for %s", resp.status_code, uri)
            except httpx.HTTPError as exc:
                LOGGER.warning("Attempt %d failed for %s: %s", attempt + 1, uri, exc)
            time.sleep(2.0 * (attempt + 1))
        LOGGER.error("Giving up on %s", uri)
        return None

    def search_top_skill_uri(self, text: str) -> Optional[str]:
        """Return the URI of the top skill search hit for ``text``."""
        try:
            resp = self._client.get(
                f"{self.api_base}/search",
                params={"text": text, "type": "skill", "limit": 1, "language": "en"},
            )
            resp.raise_for_status()
            results = resp.json().get("_embedded", {}).get("results", [])
            time.sleep(self.delay)
            return results[0]["uri"] if results else None
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            LOGGER.warning("Search failed for %r: %s", text, exc)
            return None


# Traversal
# ======================================================================


def _links(resource: dict, rel: str) -> list[dict]:
    items = resource.get("_links", {}).get(rel, [])
    return items if isinstance(items, list) else [items]


def _uri_suffix(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _weights_for(
    uri: str, title: str, inherited: Optional[dict], cfg: CurationConfig
) -> Optional[dict]:
    """Most-specific weight mapping: exact suffix, then title, then inherited."""
    suffix = _uri_suffix(uri)
    if suffix in cfg.group_weights:
        return cfg.group_weights[suffix]
    if title.lower() in cfg.transversal_weights:
        return cfg.transversal_weights[title.lower()]
    return inherited


def walk(
    client: EscoClient,
    uri: str,
    weights: Optional[dict],
    max_per_group: int,
    seen: set[str],
    cfg: CurationConfig,
) -> Iterator[tuple[dict, dict]]:
    """Yield (leaf resource, weights) under ``uri``, depth-first."""
    resource = client.get_resource(uri)
    if resource is None:
        return
    title = resource.get("title", "") or ""
    if title.lower() in cfg.excluded_titles:
        return  # explicitly excluded branch
    weights = _weights_for(uri, title, weights, cfg)

    leaf_count = 0
    for leaf in _links(resource, "narrowerSkill"):
        if weights is None:
            continue  # unmapped branch: skip leaves, keep descending groups
        leaf_uri = leaf.get("uri", "")
        if not leaf_uri or leaf_uri in seen:
            continue
        if leaf_count >= max_per_group:
            LOGGER.info("Group cap reached under %s (%s)", title or uri, max_per_group)
            break
        detail = client.get_resource(leaf_uri)
        if detail is None:
            continue
        seen.add(leaf_uri)
        leaf_count += 1
        yield detail, weights

    for group in _links(resource, "narrowerConcept"):
        group_uri = group.get("uri", "")
        if group_uri:
            yield from walk(client, group_uri, weights, max_per_group, seen, cfg)


# Entry construction
# ======================================================================


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value[:64]


def build_entry(resource: dict, weights: dict, used_ids: set[str]) -> Optional[dict]:
    name = (resource.get("preferredLabel", {}) or {}).get("en") or resource.get(
        "title"
    )
    if not name:
        return None
    uri = resource.get("uri", "")
    alt = resource.get("alternativeLabel", {}) or {}
    candidates = set(alt.get("en", []))
    # en-us preferred labels are often the plain form JDs actually use
    # (e.g. "Python" vs "Python (computer programming)").
    en_us = (resource.get("preferredLabel", {}) or {}).get("en-us")
    if en_us:
        candidates.add(en_us)
    aliases = sorted(
        {a.strip() for a in candidates if a and a.strip() and a.strip() != name}
    )

    entry_id = slugify(name)
    if not entry_id:
        return None
    if entry_id in used_ids:  # collision: disambiguate from the URI
        entry_id = f"{entry_id}_{hashlib.sha256(uri.encode()).hexdigest()[:6]}"
    used_ids.add(entry_id)

    total = sum(weights.values())
    normalized = {k: round(v / total, 3) for k, v in weights.items() if v > 0}
    # Rounding drift: pin the largest weight so the sum is exactly 1.0.
    drift = round(1.0 - sum(normalized.values()), 3)
    if drift:
        top = max(normalized, key=normalized.get)  # type: ignore[arg-type]
        normalized[top] = round(normalized[top] + drift, 3)

    return {
        "id": entry_id,
        "name": name,
        "aliases": aliases,
        "categories": normalized,
        "esco_uri": uri,
    }


# TOML emission
# ======================================================================


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def emit_toml(entries: list[dict], output: Path, cfg: CurationConfig) -> None:
    categories = ", ".join(f'"{c}"' for c in cfg.categories)
    lines = [
        "# jobjob skill cloud -- generated by scripts/curate_skill_cloud.py.",
        "# Do not edit by hand; regenerate against an ESCO release, review the diff.",
        "#",
        "# Contains curated, modified data from ESCO (European Skills,",
        "# Competences, Qualifications and Occupations), (c) European Union.",
        "# Reused under Commission Decision 2011/833/EU (CC BY 4.0 terms).",
        "# Changes: branch selection, category weighting, id assignment.",
        "# See jobjob/data/NOTICE-ESCO.md.",
        "",
        "[cloud]",
        f'esco_version = "{cfg.esco_version}"',
        f'retrieved = "{dt.date.today().isoformat()}"',
        f"categories = [{categories}]",
        "",
    ]
    for entry in sorted(entries, key=lambda e: e["id"]):
        lines.append("[[cloud.skill]]")
        lines.append(f'id = "{entry["id"]}"')
        lines.append(f'name = "{toml_escape(entry["name"])}"')
        aliases = ", ".join(f'"{toml_escape(a)}"' for a in entry["aliases"])
        lines.append(f"aliases = [{aliases}]")
        cats = ", ".join(f"{k} = {v}" for k, v in sorted(entry["categories"].items()))
        lines.append(f"categories = {{ {cats} }}")
        lines.append(f'esco_uri = "{entry["esco_uri"]}"')
        lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


# Main
# ======================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=Path(".esco-cache"))
    parser.add_argument("--max-per-group", type=int, default=80)
    parser.add_argument("--max-total", type=int, default=2400)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()

    cfg = load_config(args.config)
    client = EscoClient(args.cache_dir, cfg.api_base, delay=args.delay)
    seen: set[str] = set()
    used_ids: set[str] = set()
    entries: list[dict] = []

    # Seeds first: skills outside the group hierarchy that traversal can't
    # reach; seeding first also guarantees them a slot under any cap.
    for term, weights in cfg.seed_weights.items():
        uri = client.search_top_skill_uri(term)
        if not uri or uri in seen:
            continue
        resource = client.get_resource(uri)
        if resource is None:
            continue
        seen.add(uri)
        entry = build_entry(resource, weights, used_ids)
        if entry:
            entries.append(entry)
            LOGGER.info("Seeded %r -> %s", term, entry["id"])

    for root_uri, root_weights, root_budget in cfg.roots:
        if len(entries) >= args.max_total:
            break
        LOGGER.info(
            "Traversing %s (budget %d; %d entries so far)",
            root_uri,
            root_budget,
            len(entries),
        )
        root_count = 0
        for resource, weights in walk(
            client, root_uri, root_weights, args.max_per_group, seen, cfg
        ):
            entry = build_entry(resource, weights, used_ids)
            if entry:
                entries.append(entry)
                root_count += 1
            if root_count >= root_budget:
                LOGGER.info("Root budget reached for %s (%d)", root_uri, root_budget)
                break
            if len(entries) >= args.max_total:
                LOGGER.info("Global cap reached (%d)", args.max_total)
                break

    for entry in entries:
        extra = cfg.curated_aliases.get(entry["id"])
        if extra:
            entry["aliases"] = sorted(set(entry["aliases"]) | set(extra))

    emit_toml(entries, args.output, cfg)
    LOGGER.info("Wrote %d skills to %s", len(entries), args.output)


if __name__ == "__main__":
    # NOTE: logging configuration stays behind the __main__ guard so importing
    #   this module (e.g. in tests) never mutates global logging state.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    main()

# __END__
