# Configuration file for the Sphinx documentation builder.
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

# Make the ``jobjob`` package importable for autodoc, whether or not it is installed.
# Anchored on this file: <root>/docs/conf.py -> <root>.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

# -- Project information ------------------------------------------------------
project = "jobjob"
author = "jobjob contributors"
copyright = "2026, jobjob contributors"

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
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = ["build", "build/**", "Makefile", "make.bat", "requirements.txt"]

# This documentation set is authored entirely in reStructuredText.
source_suffix = {".rst": "restructuredtext"}

# Don't fail the build if an optional/heavy dependency can't be imported during
# autodoc; mock anything that the docs CI image may lack.
autodoc_mock_imports = []
autodoc_default_options = {"members": True, "show-inheritance": True}
autosummary_generate = True

# Napoleon (Google-style docstrings).
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# -- HTML output -------------------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = []
html_title = "jobjob documentation"
html_context = {
    "display_github": True,
    "github_user": "inquisitive-village-idiot",
    "github_repo": "jobjob",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
