#!/usr/bin/env python3
"""Create a blank-but-valid jobjob profile from a built-in skeleton.

A *new* profile starts empty — no Tila Mer (or any other) example content — but
structurally complete: the content TOMLs parse and load to empty sets, the reference
dirs exist, and ``config/.profile`` is present (blank). The user fills it in via the
Static Content / Profile pages or by importing a résumé (see ``jobjob.ingest``).

Kept here (next to ``loadcontent``/``location``) so the exact ``[tool.*]`` shapes the
loaders expect stay co-located with the code that reads them.
"""

from pathlib import Path

# Valid-but-empty content. The tool-level config carries the same defaults as the
# bundled example so a fresh profile behaves sensibly; the item arrays are omitted
# (the loaders treat a missing array as an empty set).
_HIGHLIGHTS_TOML = """\
# Your credential highlights — reusable blocks the model selects from per job.
# Add your own below, or import a résumé to pre-fill them (Static Content → Import).
[tool.highlights]
default_number = 6
max_characters = 900
min_characters = 600

# [[tool.highlights.highlight]]
# context = "short_id"
# topic = "Technical"   # Collaboration/Communication/Creativity/Leadership/Teamwork
# enabled = true
# text = '''One strong, specific accomplishment in your own voice.'''
# keywords = ["keyword", "another"]
"""

_SKILLS_TOML = """\
# Your skills. `keywords` drive matching against a job description; the skills
# analysis reports which are supported vs. gaps. Add your own below.
[tool.skills]
default_number = 12

# [[tool.skills.skill]]
# label = "short_id"
# text = "Human-readable skill"
# keywords = ["keyword"]
"""

_TEMPLATES_TOML = """\
# Your resume template(s). Point `doc_id` (or the app's RESUME_TEMPLATE_ID) at your
# own Google Doc. Sections are located by heading and filled by the apply flow.
[tool.templates]
default = "default"

# Editable sections, located by their heading (matched case-insensitively).
# `section` selects how the region is filled: "objective" (rewritten for the role)
# or "highlights" (bullets replaced with the selected highlights). Toggle `enabled`
# to leave a section's template text untouched.
[[tool.templates.section]]
heading = "Objective"
section = "objective"
enabled = true

[[tool.templates.section]]
heading = "Highlights"
section = "highlights"
enabled = true

[[tool.templates.template]]
name = "default"
archetype = "Default"
doc_id = ""
description = "Your resume template. Set doc_id (RESUME_TEMPLATE_ID) to a Google Doc."
keywords = []
"""

_EXPERIENCE_TOML = """\
# Your work history. Each [[tool.experience.role]] is one ATS "Work Experience"
# entry. Several roles at the same employer are separate entries (that's how an ATS
# wants them); list them adjacent and a résumé groups them under one company.
# Add your own below, or import a résumé to pre-fill them (Static Content → Import).
[tool.experience]

# [[tool.experience.role]]
# company = "Acme Corp"
# title = "Senior Engineer"
# location = "Remote"
# start = "2021-03"          # YYYY-MM or YYYY
# end = ""                   # blank when current
# current = true
# description = '''
# - One specific, quantified accomplishment.
# - Another.
# '''
"""

_BACKGROUND_MD = """\
# Background

Your career narrative, context, and any relocation intent go here. This is shared
context the model reads on every generation — write it in your own voice.
"""

_WRITING_STYLE_MD = """\
# Writing style

Notes on your voice and style: tone, sentence rhythm, words to favor or avoid. The
model mirrors this when drafting cover letters.
"""

_PROFILE_CONFIG = """\
# jobjob profile — applicant identity + resume template.
# Fill these in via the setup wizard or the Profile settings page. No secrets or
# local paths here.
APPLICANT_NAME=""
APPLICANT_EMAIL=""
APPLICANT_PHONE=""
APPLICANT_LINKEDIN=""
RESUME_TEMPLATE_ID=""
"""


def create_blank_profile(dest: Path) -> Path:
    """Write a blank-but-valid profile tree at ``dest`` and return it.

    Creates ``content/{highlights,skills,templates,experience}.toml``,
    ``reference/{background.md,writing_style.md,cover_letters/,stars/}``, and
    ``config/.profile``. Parent dirs are created as needed; existing files are left
    untouched (idempotent), so re-running never clobbers user edits.

    Arguments:
        dest: The profile directory to populate.
    Returns:
        ``dest``.
    """
    content = dest / "content"
    reference = dest / "reference"
    config = dest / "config"
    for d in (
        content,
        reference,
        reference / "cover_letters",
        reference / "stars",
        config,
    ):
        d.mkdir(parents=True, exist_ok=True)

    files = {
        content / "highlights.toml": _HIGHLIGHTS_TOML,
        content / "skills.toml": _SKILLS_TOML,
        content / "templates.toml": _TEMPLATES_TOML,
        content / "experience.toml": _EXPERIENCE_TOML,
        reference / "background.md": _BACKGROUND_MD,
        reference / "writing_style.md": _WRITING_STYLE_MD,
        config / ".profile": _PROFILE_CONFIG,
    }
    for path, text in files.items():
        if not path.exists():
            path.write_text(text, encoding="utf-8")
    return dest


# __END__
