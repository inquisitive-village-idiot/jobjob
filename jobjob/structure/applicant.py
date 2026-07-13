#!/usr/bin/env python3
"""Applicant identity used in cover-letter headers.

NOTE: values come from runtime config (config/.env via jobjob.config), not from
    defaults defined here. This is a pure data structure.
"""

import dataclasses as dcs

# Generational suffixes kept (not stripped as a "credential") whether they trail
# a comma ("Tila Mer, Jr.") or not ("Tila Mer Jr"). Matched case-insensitively.
_GENERATIONAL_SUFFIXES = frozenset({"jr", "sr", "junior", "senior"})

# Roman numeral suffixes kept for the same reason (design D8: "Tila Mer III" ->
# "TilaMerIII"). A closed allowlist rather than a general roman-numeral regex:
# a generational numeral is never higher than a few dozen, and a general
# matcher would also accept e.g. "MD" (M=1000, D=500) or "CD" (400) — common
# credential abbreviations that must be dropped as credentials, not kept as a
# (nonsensical) numeral suffix.
_ROMAN_NUMERAL_SUFFIXES = frozenset(
    {
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "IX",
        "X",
        "XI",
        "XII",
        "XIII",
        "XIV",
        "XV",
        "XVI",
        "XVII",
        "XVIII",
        "XIX",
        "XX",
    }
)


@dcs.dataclass(frozen=True)
class Applicant:
    """Applicant contact details for document headers.

    Attributes:
        name: Full name (with credentials).
        phone: Contact phone.
        email: Contact email.
        linkedin: LinkedIn URL.
    """

    name: str | None = None
    phone: str | None = None
    email: str | None = None
    linkedin: str | None = None

    def contact_line(self) -> str:
        """Return the ``phone | email | linkedin`` header, omitting unset parts."""
        return " | ".join(
            part for part in (self.phone, self.email, self.linkedin) if part
        )


def _is_suffix_token(token: str) -> bool:
    """Return whether ``token`` is a generational suffix or roman numeral."""
    cleaned = token.strip(" .")
    if not cleaned:
        return False
    if cleaned.lower() in _GENERATIONAL_SUFFIXES:
        return True
    return cleaned.upper() in _ROMAN_NUMERAL_SUFFIXES


def _capitalize_word(word: str) -> str:
    """Capitalize ``word``'s first letter, preserving the rest (e.g. "McDonald")."""
    return word[:1].upper() + word[1:] if word else word


def first_last_name(name: str | None) -> str:
    """Derive a filename-safe ``FirstLast`` token from a full applicant name.

    Strips credentials (comma-separated trailers such as ``", PhD"``) and
    punctuation, but **keeps** generational suffixes and roman numerals whether
    they trail a comma or a space:

    - ``"Tila Mer, PhD"``  -> ``"TilaMer"``   (credential dropped)
    - ``"Tila Mer Jr"``    -> ``"TilaMerJr"``  (suffix kept, no comma)
    - ``"Tila Mer, Jr."``  -> ``"TilaMerJr"``  (suffix kept, comma form)
    - ``"Tila Mer III"``   -> ``"TilaMerIII"`` (roman numeral kept)

    Arguments:
        name: The applicant's full name, or None.
    Returns:
        The derived ``FirstLast[Suffix]`` token, or ``""`` for an empty/None name.
    """
    if not name:
        return ""  # EARLY EXIT: no name to derive from.

    # Comma-separated trailers: keep only the ones that look like a
    # generational suffix; anything else (PhD, MBA, Esq, ...) is a credential
    # and is dropped.
    segments = [s.strip() for s in name.split(",") if s.strip()]
    base = segments[0] if segments else ""
    kept_suffixes = [s for s in segments[1:] if _is_suffix_token(s)]

    # A suffix given without a comma ("Tila Mer Jr" / "Tila Mer III") is the
    # base's last word.
    words = base.split()
    if len(words) > 1 and _is_suffix_token(words[-1]):
        kept_suffixes = [words[-1]] + kept_suffixes
        words = words[:-1]

    def _format_suffix(raw: str) -> str:
        cleaned = raw.strip(" .")
        if cleaned.lower() in _GENERATIONAL_SUFFIXES:
            return _capitalize_word(cleaned.lower())
        return cleaned.upper()  # Roman numerals are conventionally all-caps.

    name_part = "".join(
        "".join(c for c in _capitalize_word(w) if c.isalnum()) for w in words
    )
    suffix_part = "".join(_format_suffix(s) for s in kept_suffixes)
    return name_part + suffix_part


# __END__
