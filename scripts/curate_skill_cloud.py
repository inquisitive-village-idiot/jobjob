#!/usr/bin/env python3
"""Curate the packaged skill cloud from the public ESCO API.

Traverses selected branches of the ESCO skills pillar (S: skills, K: knowledge,
plus the transversal skills/competences tree), assigns weighted category
membership per skill from its nearest mapped ancestor group, and emits
``jobjob/data/skill_cloud.toml``.

Regeneration is a rare, deliberate event: run against a new ESCO release, review
the diff, commit. Raw API responses are cached on disk so an interrupted run
resumes cheaply and re-runs are reproducible.

Licensing: ESCO data is reusable for any purpose free of charge under Commission
Decision 2011/833/EU (CC BY 4.0 terms). Attribution and an indication of changes
(this curation) ship with the generated file. See jobjob/data/NOTICE-ESCO.md.

Usage:
    uv run python scripts/curate_skill_cloud.py \
        --output jobjob/data/skill_cloud.toml \
        --cache-dir .esco-cache \
        --max-per-group 60 --max-total 1600
"""

import argparse
import datetime as dt
import hashlib
import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Iterator, Optional

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
LOGGER = logging.getLogger("curate_skill_cloud")

API_BASE = "https://ec.europa.eu/esco/api"
ESCO_VERSION = "v1.2.1"  # verify against the release you traverse

CATEGORIES = (
    "communication",
    "collaboration",
    "leadership",
    "creativity",
    "technical",
    "domain",
)

# Category weights per ESCO group. Keys are ESCO skill-group URI suffixes (the
# part after the final '/'). A leaf skill inherits the weights of its nearest
# mapped ancestor (most specific wins). Weights must sum to 1.0 per group.
#
# PROVISIONAL: first-pass judgment; tune after reviewing real JD matches.
GROUP_WEIGHTS: dict[str, dict[str, float]] = {
    # --- S1: communication, collaboration and creativity -------------------
    "S1.1": {"communication": 0.6, "collaboration": 0.4},  # negotiating
    "S1.2": {"communication": 0.5, "collaboration": 0.5},  # liaising, networking
    "S1.3": {"communication": 0.7, "leadership": 0.3},  # teaching and training
    "S1.4": {"communication": 1.0},  # presenting information
    "S1.5": {"communication": 0.6, "collaboration": 0.2, "domain": 0.2},  # advising
    "S1.6": {"communication": 0.8, "domain": 0.2},  # promoting, selling
    "S1.7": {"communication": 1.0},  # obtaining information verbally
    "S1.8": {"collaboration": 1.0},  # working with others
    "S1.9": {"creativity": 0.5, "technical": 0.5},  # solving problems
    "S1.11": {"creativity": 0.6, "technical": 0.4},  # designing systems/products
    "S1.12": {"creativity": 0.8, "communication": 0.2},  # artistic/visual materials
    "S1.13": {"communication": 0.6, "creativity": 0.4},  # writing and composing
    "S1.14": {"creativity": 0.8, "communication": 0.2},  # performing
    "S1.15": {"communication": 1.0},  # using more than one language
    # --- other S branches ---------------------------------------------------
    "S2": {"technical": 0.6, "domain": 0.4},  # information skills
    "S4": {"leadership": 0.7, "collaboration": 0.3},  # management skills
    "S5": {"technical": 1.0},  # working with computers
    # --- K: knowledge (ISCED-F fields) → domain -----------------------------
    "00": {"domain": 1.0},
    "01": {"domain": 1.0},  # education
    "02": {"domain": 0.8, "creativity": 0.2},  # arts and humanities
    "03": {"domain": 0.7, "communication": 0.3},  # social sci, journalism, info
    "04": {"domain": 0.8, "leadership": 0.2},  # business, admin, law
    "05": {"domain": 0.8, "technical": 0.2},  # natural sci, math, statistics
    "06": {"domain": 0.5, "technical": 0.5},  # ICT
    "07": {"domain": 0.6, "technical": 0.4},  # engineering, manufacturing
    "08": {"domain": 1.0},  # agriculture
    "09": {"domain": 1.0},  # health and welfare
    "10": {"domain": 1.0},  # services
}

# Roots to traverse: (uri, default weights or None to require a mapped ancestor,
# per-root entry budget). Per-root budgets keep any one branch from starving the
# rest (S1 alone can fill a global cap); the highest-JD-value branches go first
# so they can never get squeezed out. High-value ISCED fields (ICT, business,
# science, journalism) get their own roots because broad-K traversal visits
# fields in arbitrary API order and can spend its budget on low-value ones.
ROOTS: tuple[tuple[str, Optional[dict[str, float]], int], ...] = (
    # programming languages (Python, SQL, ...) hang under this group, which
    # deep broad-K traversal only reaches after its budget is spent.
    (
        "http://data.europa.eu/esco/skill/21d2f96d-35f7-4e3f-9745-c533d2dd6e97",
        {"technical": 1.0},
        150,
    ),  # computer programming
    ("http://data.europa.eu/esco/skill/S5", GROUP_WEIGHTS["S5"], 500),
    ("http://data.europa.eu/esco/isced-f/06", GROUP_WEIGHTS["06"], 200),  # ICT
    ("http://data.europa.eu/esco/skill/S4", GROUP_WEIGHTS["S4"], 200),
    ("http://data.europa.eu/esco/isced-f/04", GROUP_WEIGHTS["04"], 150),  # business
    ("http://data.europa.eu/esco/isced-f/05", GROUP_WEIGHTS["05"], 100),  # sci/math
    ("http://data.europa.eu/esco/isced-f/03", GROUP_WEIGHTS["03"], 80),  # journalism
    ("http://data.europa.eu/esco/skill/S2", GROUP_WEIGHTS["S2"], 150),
    # creativity-weighted S1 subgroups get explicit roots: depth-first broad-S1
    # traversal spends its whole budget in the early (communication-heavy)
    # subgroups and starves these.
    ("http://data.europa.eu/esco/skill/S1.11", GROUP_WEIGHTS["S1.11"], 60),
    ("http://data.europa.eu/esco/skill/S1.12", GROUP_WEIGHTS["S1.12"], 60),
    ("http://data.europa.eu/esco/skill/S1.13", GROUP_WEIGHTS["S1.13"], 60),
    ("http://data.europa.eu/esco/skill/S1.14", GROUP_WEIGHTS["S1.14"], 60),
    ("http://data.europa.eu/esco/skill/S1", None, 400),
    ("http://data.europa.eu/esco/skill/K", None, 300),  # remaining fields
    # Transversal skills/competences tree (attitudes, social interaction,
    # thinking, application of knowledge). Language branch intentionally
    # excluded: individual languages add bulk without matching value.
    (
        "http://data.europa.eu/esco/skill/7ee746cb-fded-47f5-9652-19ebebbce51b",
        None,
        150,
    ),
)

# High-value skills that hang OUTSIDE the group hierarchy (no broaderSkill),
# unreachable by tree traversal (e.g. "project management"). Each is fetched via
# search (top hit) and seeded directly with these weights.
SEED_WEIGHTS: dict[str, dict[str, float]] = {
    "project management": {
        "leadership": 0.5,
        "technical": 0.3,
        "collaboration": 0.2,
    },
    "agile project management": {
        "technical": 0.4,
        "leadership": 0.4,
        "collaboration": 0.2,
    },
    "machine learning": {"technical": 0.7, "domain": 0.3},
    "data mining": {"technical": 0.7, "domain": 0.3},
    "data analytics": {"technical": 0.6, "domain": 0.4},
    "SQL": {"technical": 1.0},
    "cloud technologies": {"technical": 1.0},
    "cyber security": {"technical": 0.7, "domain": 0.3},
    "quality assurance methodologies": {"technical": 0.6, "domain": 0.4},
    "business analysis": {"domain": 0.5, "technical": 0.3, "communication": 0.2},
    "financial analysis": {"domain": 0.7, "technical": 0.3},
    "product management": {"leadership": 0.4, "domain": 0.3, "technical": 0.3},
    "graphic design": {"creativity": 0.7, "technical": 0.3},
    "copywriting": {"communication": 0.7, "creativity": 0.3},
    "journalism": {"domain": 0.6, "communication": 0.4},
    "statistics": {"domain": 0.6, "technical": 0.4},
    "utilise machine learning": {"technical": 1.0},
}

# Curated alias additions keyed by generated entry id: closes vocabulary gaps
# where the JD-common term is missing from ESCO's labels. A documented change
# under the reuse terms (see NOTICE-ESCO.md).
CURATED_ALIASES: dict[str, list[str]] = {
    "data_mining": ["machine learning"],
}

# Transversal second-level groups are keyed by title (uuid URIs are unstable
# to eyeball); resolved during traversal.
TRANSVERSAL_TITLE_WEIGHTS: dict[str, dict[str, float]] = {
    "attitudes and values": {
        "leadership": 0.4,
        "collaboration": 0.3,
        "communication": 0.3,
    },
    "social interaction": {"collaboration": 0.6, "communication": 0.4},
    "thinking": {"creativity": 0.6, "technical": 0.2, "domain": 0.2},
    "application of knowledge": {"domain": 0.5, "technical": 0.5},
    "language": None,  # excluded
}


# API access (disk-cached)
# ======================================================================


class EscoClient:
    """Cached, throttled ESCO API reader."""

    def __init__(self, cache_dir: Path, delay: float = 0.15) -> None:
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self._client = httpx.Client(timeout=30.0)

    def get_resource(self, uri: str) -> Optional[dict]:
        """Fetch a skill/concept resource, from disk cache when available."""
        key = hashlib.sha256(uri.encode()).hexdigest()[:32]
        cache_path = Path(self.cache_dir, f"{key}.json")
        if cache_path.is_file():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        url = f"{API_BASE}/resource/skill"
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
                f"{API_BASE}/search",
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


def _weights_for(uri: str, title: str, inherited: Optional[dict]) -> Optional[dict]:
    """Most-specific weight mapping: exact suffix, then title, then inherited."""
    suffix = _uri_suffix(uri)
    if suffix in GROUP_WEIGHTS:
        return GROUP_WEIGHTS[suffix]
    if title.lower() in TRANSVERSAL_TITLE_WEIGHTS:
        return TRANSVERSAL_TITLE_WEIGHTS[title.lower()]
    return inherited


def walk(
    client: EscoClient,
    uri: str,
    weights: Optional[dict],
    max_per_group: int,
    seen: set[str],
) -> Iterator[tuple[dict, dict]]:
    """Yield (leaf resource, weights) under ``uri``, depth-first."""
    resource = client.get_resource(uri)
    if resource is None:
        return
    title = resource.get("title", "") or ""
    weights = _weights_for(uri, title, weights)
    if weights is None and title.lower() in TRANSVERSAL_TITLE_WEIGHTS:
        return  # explicitly excluded branch

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
            yield from walk(client, group_uri, weights, max_per_group, seen)


# Entry construction
# ======================================================================


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value[:64]


def build_entry(resource: dict, weights: dict, used_ids: set[str]) -> Optional[dict]:
    name = (resource.get("preferredLabel", {}) or {}).get("en") or resource.get("title")
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


def emit_toml(entries: list[dict], output: Path) -> None:
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
        f'esco_version = "{ESCO_VERSION}"',
        f'retrieved = "{dt.date.today().isoformat()}"',
        f'categories = [{", ".join(chr(34) + c + chr(34) for c in CATEGORIES)}]',
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
    parser.add_argument("--cache-dir", type=Path, default=Path(".esco-cache"))
    parser.add_argument("--max-per-group", type=int, default=60)
    parser.add_argument("--max-total", type=int, default=2000)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()

    client = EscoClient(args.cache_dir, delay=args.delay)
    seen: set[str] = set()
    used_ids: set[str] = set()
    entries: list[dict] = []

    # Seeds first: skills outside the group hierarchy that traversal can't
    # reach; seeding first also guarantees them a slot under any cap.
    for term, weights in SEED_WEIGHTS.items():
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

    for root_uri, root_weights, root_budget in ROOTS:
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
            client, root_uri, root_weights, args.max_per_group, seen
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
        extra = CURATED_ALIASES.get(entry["id"])
        if extra:
            entry["aliases"] = sorted(set(entry["aliases"]) | set(extra))

    emit_toml(entries, args.output)
    LOGGER.info("Wrote %d skills to %s", len(entries), args.output)


if __name__ == "__main__":
    main()

# __END__
