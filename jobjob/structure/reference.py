#!/usr/bin/env python3
"""Reference documents that anchor voice and credentials."""

import dataclasses as dcs
from typing import Optional


@dcs.dataclass(frozen=True)
class ReferenceDocs:
    """Loaded reference material used to ground generation.

    Each field is the assembled text for that category, or None when absent.

    Attributes:
        background: Career narrative / context.
        cover_letter_examples: Concatenated example cover letters (voice anchors).
        star_examples: Concatenated STAR-format experience blocks (honesty layer).
        writing_style: Writing-style guide.
    """

    background: Optional[str] = None
    cover_letter_examples: Optional[str] = None
    star_examples: Optional[str] = None
    writing_style: Optional[str] = None


# __END__
