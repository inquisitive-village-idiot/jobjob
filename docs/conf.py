# Configuration file for the Sphinx documentation builder.
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

# Make the ``jobjob`` package importable for autodoc, whether or not it is installed
# (anchored on this file: <root>/docs/conf.py -> <root>).
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

# -- Project information ------------------------------------------------------
project = "jobjob"
author = "Tila Mer"
copyright = "2026, Tila Mer"

try:
    from jobjob.__about__ import __version__ as release
except Exception:  # pragma: no cover - docs build without the package installed
    release = ""
version = release

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_rtd_theme",
]

# Source dir is ``docs/`` itself; exclude the build output and non-page files so they
# aren't treated as documents.
templates_path = ["_templates"]
exclude_patterns = [
    "build",
    "build/**",
    "Makefile",
    "README.md",
    "**/tests",
    "quickstart-draft.md",
]

# Markdown (MyST) alongside reStructuredText.
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
myst_heading_anchors = 3

# The guide pages are single-sourced from docs/*.md, which use GitHub-relative links
# (e.g. setup.md) that resolve on GitHub but not as Sphinx cross-references. Don't let
# those turn into build warnings.
suppress_warnings = ["myst.xref_missing"]

# Don't fail the build if an optional/heavy dependency can't be imported during autodoc.
autodoc_mock_imports = []
autodoc_default_options = {"members": True, "show-inheritance": True}
autosummary_generate = True

# Napoleon (Google-style docstrings).
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

# -- HTML output -------------------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = []
html_context = {
    "display_github": True,
    "github_user": "inquisitive-village-idiot",
    "github_repo": "jobjob",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
