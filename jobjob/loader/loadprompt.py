#!/usr/bin/env python3
"""Build extraction prompts from a PDF and a dataclass's field docs."""


import dataclasses as dcs
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Protocol, TypeVar

from jobjob.loader.loadstatic import load_pdf_text
from jobjob.loader.location import get_prompt_path
from jobjob.structure.job_decription import JobDescription


class DataclassProtocol(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, dcs.Field[Any]]]


T = TypeVar("T", bound=DataclassProtocol)


def build_field_def(klass: T) -> str:
    """Return the ``- name: doc`` field list used to describe the extraction schema.

    Field docs live in ``field.metadata["doc"]`` (portable across Python versions).
    """
    return "\n".join(
        f"- {x.name}: {x.metadata.get('doc', '')}" for x in dcs.fields(klass)
    )


def format_dataclass_prompt(
    klass: T,
    prompt_stem: str,
    text_content: str,
    prompt_path: Optional[Path] = None,
) -> str:
    """Format a prompt template with ``text_content`` and the dataclass field docs.

    The named template must contain ``{field_def}`` and ``{text_content}``. For a
    vision call (no extracted text), pass a placeholder for ``text_content`` (e.g.
    "(See the attached PDF document.)").

    Arguments:
        klass: The dataclass whose fields define the extraction schema.
        prompt_stem: Stem of the template in ``static/prompt``.
        text_content: The document text (or a placeholder for vision).
        prompt_path: Override path to the prompt template.
    Returns:
        The formatted prompt string.
    """
    prompt_path = prompt_path or get_prompt_path(prompt_stem)
    return prompt_path.read_text(encoding="utf-8").format(
        text_content=text_content, field_def=build_field_def(klass)
    )


def load_dataclass_prompt(
    path: Path,
    klass: T,
    prompt_stem: str,
    prompt_path: Optional[Path] = None,
) -> str:
    """Return an extraction prompt from a PDF's text and a dataclass's field docs.

    Arguments:
        path: PDF to extract text from.
        klass: The dataclass whose fields define the extraction schema.
        prompt_stem: Stem of the prompt template in ``static/prompt``.
        prompt_path: Override path to the prompt template.
    Returns:
        The formatted prompt string.
    """
    text = load_pdf_text(path)
    return format_dataclass_prompt(klass, prompt_stem, text, prompt_path=prompt_path)


def load_prompt_job_description(
    path: Path,
    klass: T = JobDescription,
    prompt_path: Optional[Path] = None,
) -> str:
    """Return a prompt to parse the given job description."""
    return load_dataclass_prompt(path, klass, "job_description", prompt_path=prompt_path)


# __END__
