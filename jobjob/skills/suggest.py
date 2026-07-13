#!/usr/bin/env python3
"""`jobjob skills suggest` — skills-file feedback from processed applications.

Aggregates skills that the saved skills analyses support but the active
profile's ``skills.toml`` never declares — the "skills-file candidates" each
apply run prints into its README, collected across every processed application
and deduplicated by canonical id. Everything comes from saved artifacts plus
the packaged skill cloud: no AI calls, no Google API reads.

Honesty gate: only canonical, analysis-evidenced, undeclared skills are ever
suggested, and nothing is written without an explicit ``--apply`` id list.
Appends go through tomlkit (``jobjob.ingest.save``), preserving the file's
formatting and comments.
"""

import argparse
import dataclasses as dcs
import json
import logging
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import Optional

from jobjob.apply.generate.ats import supported_canonical_ids
from jobjob.apply.recheck import SKILLS_NAME, SUMMARY_NAME
from jobjob.cli import run_main
from jobjob.config import load_settings
from jobjob.ingest.save import save_skills
from jobjob.loader.loadcontent import load_skills
from jobjob.loader.location import get_content_path
from jobjob.structure.skill import Skill, SkillSet
from jobjob.structure.skillcloud import CloudSkill, SkillCloud, get_skill_cloud

NAME = "jobjob.skills.suggest"


# Structures
# ======================================================================


@dcs.dataclass(frozen=True)
class Citation:
    """One application's evidence for a suggested skill.

    Attributes:
        application: Source application directory name.
        evidence: Evidence string from that application's skills analysis.
    """

    application: str
    evidence: str


@dcs.dataclass(frozen=True)
class SkillSuggestion:
    """An evidenced, canonical skill missing from the skills file.

    Attributes:
        canonical_id: Skill-cloud canonical id (the ``--apply`` handle).
        name: Canonical display name.
        citations: Evidence citations, one per supporting application.
    """

    canonical_id: str
    name: str
    citations: tuple[Citation, ...]


# Aggregation
# ======================================================================


def iter_application_dirs(root: Path) -> Iterator[Path]:
    """Yield immediate subdirectories of ``root`` holding saved apply artifacts.

    A directory counts as a processed application when both ``summary.json``
    and ``skills_analysis.json`` are present; anything else is skipped.
    """
    for path in sorted(Path(root).iterdir()):
        if path.is_dir() and all(
            Path(path, name).is_file() for name in (SUMMARY_NAME, SKILLS_NAME)
        ):
            yield path


def aggregate_candidates(
    root: Path,
    *,
    skill_set: Optional[SkillSet] = None,
    cloud: Optional[SkillCloud] = None,
    logger: logging.Logger | None = None,
) -> list[SkillSuggestion]:
    """Aggregate skills-file candidates across processed applications.

    A candidate is evidenced in at least one saved skills analysis, resolves
    to a canonical skill-cloud entry, and is not declared in ``skill_set``.
    Unlike the per-application README list, resume-text presence is ignored:
    an evidenced skill is undeclared regardless of whether one resume happened
    to render it.

    Arguments:
        root: Directory whose subdirectories are processed applications.
        skill_set: The loaded profile skills (declared allowlist); None means
            nothing is declared yet.
        cloud: Injected skill cloud (testing); defaults to the packaged one.
        logger: Optional logger for injection.
    Returns:
        Suggestions sorted by canonical id, citations in scan order.
    Raises:
        FileNotFoundError: If ``root`` is not a directory.
    """
    _logger = logger or logging.getLogger(NAME)
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"No such applications directory: {root}")
    cloud = cloud or get_skill_cloud()
    declared = {
        s.canonical_id for s in (skill_set.skills if skill_set else ()) if s.canonical
    }

    cited: dict[str, list[Citation]] = {}
    for app_dir in iter_application_dirs(root):
        try:
            analysis = json.loads(
                Path(app_dir, SKILLS_NAME).read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            _logger.warning("Skipping %s: %s", app_dir.name, exc)
            continue
        for canonical_id, evidence in supported_canonical_ids(analysis, cloud).items():
            if canonical_id in declared:
                continue
            cited.setdefault(canonical_id, []).append(
                Citation(application=app_dir.name, evidence=evidence)
            )
    return [
        SkillSuggestion(
            canonical_id=canonical_id,
            name=cloud.skills[canonical_id].name,
            citations=tuple(citations),
        )
        for canonical_id, citations in sorted(cited.items())
    ]


# Confirmed append
# ======================================================================


def skill_from_cloud(canonical: CloudSkill) -> Skill:
    """Derive a skills-file entry from a canonical cloud skill."""
    return Skill(
        label=canonical.id,
        text=canonical.name,
        keywords=tuple(canonical.aliases),
    )


def append_confirmed(
    suggestions: Iterable[SkillSuggestion],
    apply_ids: Sequence[str],
    path: Path,
    *,
    cloud: Optional[SkillCloud] = None,
    logger: logging.Logger | None = None,
) -> int:
    """Append the confirmed candidate ids to the skills file at ``path``.

    The honesty gate: every id must be a current suggestion (evidenced,
    canonical, undeclared). Any unknown id aborts the whole write.

    Arguments:
        suggestions: The current aggregation (see ``aggregate_candidates``).
        apply_ids: Canonical ids the user confirmed; duplicates collapse.
        path: The skills TOML to append to.
        cloud: Injected skill cloud (testing); defaults to the packaged one.
        logger: Optional logger for injection.
    Returns:
        The number of entries appended.
    Raises:
        ValueError: If any id is not in the current suggestion set.
    """
    _logger = logger or logging.getLogger(NAME)
    candidate_ids = {s.canonical_id for s in suggestions}
    apply_ids = list(dict.fromkeys(apply_ids))
    rejected = [i for i in apply_ids if i not in candidate_ids]
    if rejected:
        raise ValueError(
            "Not current candidates (must be evidenced, canonical, and "
            f"undeclared): {', '.join(rejected)}"
        )
    cloud = cloud or get_skill_cloud()
    count = save_skills(
        path, (skill_from_cloud(cloud.skills[i]) for i in apply_ids), mode="append"
    )
    _logger.info("Appended %d skill(s) to %s", count, path)
    return count


# Report rendering
# ======================================================================


def render_suggestions(suggestions: Sequence[SkillSuggestion]) -> str:
    """Render the aggregated suggestions as a plain-text report."""
    if not suggestions:
        return (
            "No skills-file candidates — the skills file already covers the "
            "documented evidence.\n"
        )
    lines = [
        "Skills-file candidates (evidenced in processed applications, not "
        "declared in skills.toml):",
        "",
    ]
    for suggestion in suggestions:
        lines.append(f"{suggestion.canonical_id} — {suggestion.name}")
        for citation in suggestion.citations:
            note = f": {citation.evidence}" if citation.evidence else ""
            lines.append(f"  - {citation.application}{note}")
        lines.append("")
    lines.append("Append confirmed ids with: jobjob skills suggest --apply <id> ...")
    return "\n".join(lines) + "\n"


# Serialization (webapp)
# ======================================================================


def suggestions_as_dicts(suggestions: Iterable[SkillSuggestion]) -> list[dict]:
    """JSON-ready dicts of the suggestions (citations flattened by asdict)."""
    return [dcs.asdict(s) for s in suggestions]


# CLI
# ======================================================================


def parse_args(argv: Optional[Iterable] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="jobjob skills",
        description="Skills-file feedback from processed applications.",
    )
    actions = parser.add_subparsers(dest="action", required=True)
    suggest = actions.add_parser(
        "suggest",
        help=(
            "Aggregate evidence-backed skills-file candidates; optionally "
            "append confirmed ones."
        ),
    )
    suggest.add_argument(
        "--root",
        type=Path,
        default=None,
        help=(
            "Applications directory to scan (default: the configured local "
            "applications mirror)."
        ),
    )
    suggest.add_argument(
        "--apply",
        nargs="+",
        metavar="ID",
        default=None,
        help=(
            "Canonical ids from the report to append to the active profile's "
            "skills file. Ids that are not current candidates abort the write."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable] = None, logger: logging.Logger | None = None) -> int:
    """CLI entrypoint for ``jobjob skills``."""

    def _run(args_iterable: Optional[Iterable]) -> int:
        args = parse_args(args_iterable)
        _logger = logger or logging.getLogger(NAME)
        root = args.root or load_settings().applications_output_dir
        if root is None:
            # EARLY EXIT: nowhere to scan and nothing was pointed at.
            _logger.error(
                "No applications directory configured (set "
                "APPLICATIONS_OUTPUT_DIR) and no --root given."
            )
            return 2
        try:
            skill_set = load_skills(logger=logger)
        except (OSError, ValueError) as exc:
            _logger.warning("Skills file unavailable; treating as empty: %s", exc)
            skill_set = None
        suggestions = aggregate_candidates(
            Path(root), skill_set=skill_set, logger=logger
        )
        print(render_suggestions(suggestions))
        if args.apply:
            append_confirmed(
                suggestions, args.apply, get_content_path("skills"), logger=logger
            )
        return 0

    return run_main(_run, argv)


# __END__
