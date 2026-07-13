#!/usr/bin/env python3
"""Normalized dedup signal (application-identity, phase 6c / design D3).

Casefold + whitespace + a small, documented common-abbreviation map applied to
company+role (or, for a contact, first+last name) sourced from ``source.json``.
The normalized string IS the substance -- the duplicate-detection signal
itself (design D3); any hash of it is a derived, compact key, never stored as
truth. It is computed fresh at listing time (``services.tracking_service``),
never persisted to disk.

Exact-match only, the same posture as ``structure.normalize`` (JD requirement
to skill-cloud resolution): normalization narrows *incidental* naming
variance (casing, whitespace, a small closed set of common abbreviations) --
it never tries to catch every possible spelling variant. This is a flag for a
human, not an auto-merge (design D3's risk note): weak recall is an
acceptable trade-off for zero false "same entity" merges.
"""

import re
import string
from typing import Optional

# Word-level normalization: every key AND every value below reduce to the same
# canonical short form, so "Inc"/"Incorporated" (and the bare "inc") all
# collapse to "inc". Deliberately small (design D3: "keep it small and
# documented") -- not a general legal-suffix or honorific parser. Company
# suffixes (inc/corp/co/ltd/llc) and generational suffixes (sr/jr) are the two
# families the dedup signal actually needs (company+role, or a contact's
# first+last name).
_ABBREVIATIONS: dict[str, str] = {
    "inc": "inc",
    "incorporated": "inc",
    "corp": "corp",
    "corporation": "corp",
    "co": "co",
    "company": "co",
    "ltd": "ltd",
    "limited": "ltd",
    "llc": "llc",
    "sr": "sr",
    "senior": "sr",
    "jr": "jr",
    "junior": "jr",
}

_PUNCT_TABLE = str.maketrans({c: " " for c in string.punctuation})
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_token(text: Optional[str]) -> str:
    """Casefold, strip punctuation, collapse whitespace, apply the abbreviation map.

    Arguments:
        text: Raw string (a company name, role title, or one part of a
            contact's name); ``None``/empty degrades to ``""``.
    Returns:
        The normalized token, directly comparable with ``==``.
    """
    if not text:
        return ""
    folded = text.casefold().translate(_PUNCT_TABLE)
    words = [_ABBREVIATIONS.get(w, w) for w in folded.split()]
    return _WHITESPACE_RE.sub(" ", " ".join(words)).strip()


def dedup_signal(*parts: Optional[str]) -> str:
    """Return the normalized dedup signal for an ordered set of parts.

    For an application: ``dedup_signal(company, role)``. For a contact:
    ``dedup_signal(first_name, last_name)``. The returned string is the
    substance (design D3) -- compare it directly, or hash it yourself for a
    compact key, but never store the hash as the source of truth.

    Arguments:
        parts: The fields to combine, in order (order matters: company+role
            is not comparable with role+company).
    Returns:
        The normalized parts joined by ``"|"``; ``""`` when every part is
        blank -- an all-blank source must never "match" another blank one.
    """
    normalized = [normalize_token(p) for p in parts]
    if not any(normalized):
        return ""
    return "|".join(normalized)


# __END__
