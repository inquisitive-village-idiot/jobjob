#!/usr/bin/env python3
"""Load reference documents (background, cover letters, STARs, writing style)."""

from pathlib import Path
from typing import Optional

from jobjob.loader.loadstatic import SUPPORTED_SUFFIXES, read_document
from jobjob.loader.location import get_reference_dir
from jobjob.structure.reference import ReferenceDocs

# NOTE: keep this at or above the file count in static/reference/cover_letters/;
# _collect_directory silently drops files past the cap (sorted by stem).
DEFAULT_MAX_COVER_LETTERS = 8


def _find_named_document(directory: Path, stem: str) -> Optional[Path]:
    """Return the first ``<stem>.<ext>`` file in ``directory`` for a supported ext."""
    for suffix in SUPPORTED_SUFFIXES:
        candidate = Path(directory, f"{stem}{suffix}")
        if candidate.is_file():
            return candidate  # EARLY EXIT: first match wins.
    return None


def _collect_directory(directory: Path, limit: Optional[int] = None) -> Optional[str]:
    """Read supported docs in ``directory``, sorted by stem, into a labeled block.

    Arguments:
        directory: Directory to scan.
        limit: Max number of files to include (None for all).
    Returns:
        Labeled, concatenated text, or None if the directory has no usable docs.
    """
    if not directory.is_dir():
        return None  # EARLY EXIT: nothing to collect.

    files = [p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES]
    files.sort(key=lambda p: p.stem)
    if limit is not None:
        files = files[:limit]

    blocks = []
    for path in files:
        content = read_document(path)
        if content:
            blocks.append(f"=== {path.stem} ===\n{content}")
    return "\n\n".join(blocks) if blocks else None


def load_reference_documents(
    reference_dir: Optional[Path] = None,
    max_cover_letters: int = DEFAULT_MAX_COVER_LETTERS,
) -> ReferenceDocs:
    """Load reference material from the static reference directory.

    Looks for ``background.*``, ``cover_letters/``, ``stars/``, and
    ``writing_style.*`` (suffixes: .txt, .md, .docx, .pdf).

    Arguments:
        reference_dir: Override path to the reference directory. Defaults to the
            static reference directory.
        max_cover_letters: Cap on the number of example cover letters included.
    Returns:
        A ReferenceDocs with whatever was found (missing categories are None).
    """
    reference_dir = reference_dir or get_reference_dir()

    background_path = _find_named_document(reference_dir, "background")
    style_path = _find_named_document(reference_dir, "writing_style")

    return ReferenceDocs(
        background=read_document(background_path) if background_path else None,
        cover_letter_examples=_collect_directory(
            Path(reference_dir, "cover_letters"), limit=max_cover_letters
        ),
        star_examples=_collect_directory(Path(reference_dir, "stars")),
        writing_style=read_document(style_path) if style_path else None,
    )


# __END__
