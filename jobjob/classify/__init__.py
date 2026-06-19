"""File classification (JD vs LinkedIn profile vs unsupported)."""

from jobjob.classify.classify import (
    JD,
    LINKEDIN_PROFILE,
    UNSUPPORTED,
    classify_file,
)

__all__ = ["JD", "LINKEDIN_PROFILE", "UNSUPPORTED", "classify_file"]
