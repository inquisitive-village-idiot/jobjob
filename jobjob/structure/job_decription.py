#!/usr/bin/env python3
"""."""

import dataclasses as dcs
from collections.abc import Iterable, Mapping


# NOTE: per-field docs are carried in field metadata (``{"doc": ...}``) and drive the
#   extraction prompt (loadprompt.py). Metadata works on all supported Pythons, unlike
#   the 3.14-only ``field(doc=...)`` keyword.
@dcs.dataclass
class JobDescription:
    company_name: str = dcs.field(metadata={"doc": "The company name"})
    role_title: str = dcs.field(metadata={"doc": "The exact job title"})
    department: str = dcs.field(metadata={"doc": "Department or team if mentioned"})
    location: Iterable[str] = dcs.field(metadata={"doc": "Job location(s)"})
    key_requirements: Iterable[str] = dcs.field(
        metadata={"doc": "List of 5-10 most important requirements/qualifications"}
    )
    responsibilities: Iterable[str] = dcs.field(
        metadata={"doc": "List of main job responsibilities  "}
    )
    technical_skills: Iterable[str] = dcs.field(
        metadata={"doc": "List of technical skills mentioned"}
    )
    soft_skills: Iterable[str] = dcs.field(
        metadata={"doc": "List of soft skills mentioned"}
    )
    keywords: Iterable[str] = dcs.field(
        metadata={"doc": "List of important keywords for resume optimization"}
    )
    seniority_level: str = dcs.field(
        metadata={"doc": "junior/mid/senior/lead/director/vp/c-level"}
    )
    salary: str = dcs.field(
        metadata={"doc": "Salary or compensation range if stated, else empty"}
    )
    hiring_manager: str = dcs.field(
        metadata={"doc": "Hiring manager or recruiter name if named, else empty"}
    )
    summary: str = dcs.field(metadata={"doc": "2-3 sentence summary of the role"})
    # NOTE: defaulted (and therefore last) so older cached parses and existing
    #   call sites construct cleanly without it.
    canonical_skills: Mapping[str, str] = dcs.field(
        default_factory=dict,
        metadata={
            "doc": (
                "JSON object mapping EACH item of key_requirements and "
                "technical_skills (exact text as the key) to the most standard, "
                'widely used generic name for that skill (e.g. "solid Python '
                'scripting": "Python (computer programming)"). Use plain '
                "taxonomy-style names; do not invent compound names"
            )
        },
    )


# __END__
