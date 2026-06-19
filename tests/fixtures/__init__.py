"""Test fixture data (example JD/profile PDFs) and accessors.

Relocated here from ``static/example`` — this is test-only data, not shipped
with the package.
"""

from pathlib import Path


def fixture_dir() -> Path:
    """Return the test fixtures directory."""
    return Path(__file__).parent


def fixture_path(stem: str) -> Path:
    """Return the fixture file whose stem matches ``stem``.

    Raises:
        ValueError if no fixture with that stem exists.
    """
    files = {p.stem: p for p in fixture_dir().iterdir() if p.is_file()}
    if stem not in files:
        raise ValueError(f'Unknown fixture "{stem}" in {fixture_dir()}')
    return files[stem]
