#!/usr/bin/env python3
"""Build dataclass instances from loosely-typed mappings (e.g. LLM JSON)."""

import dataclasses as dcs
from collections.abc import Mapping
from typing import Any, Type, TypeVar

T = TypeVar("T")


def _is_str_field(field: dcs.Field) -> bool:
    """Return True if the field is a plain ``str`` (not a collection)."""
    # NOTE: annotations may be the type object or a string (PEP 563); handle both.
    return field.type is str or field.type == "str"


def _is_mapping_field(field: dcs.Field) -> bool:
    """Return True if the field is annotated as a Mapping/dict."""
    # NOTE: annotations may be the type object or a string (PEP 563); handle both.
    return "Mapping" in str(field.type) or "dict" in str(field.type)


def _default_for(field: dcs.Field) -> Any:
    """Return a sensible empty default for a missing field based on its type."""
    if _is_str_field(field):
        return ""
    if _is_mapping_field(field):
        return {}
    return ()


def from_mapping(klass: Type[T], data: Mapping[str, Any]) -> T:
    """Construct a dataclass from a mapping, supplying empty defaults for gaps.

    Tolerates an LLM omitting fields or returning ``null``: missing/None values
    become "" for str fields and () otherwise. Also coerces a scalar string into a
    single-element list for collection fields (the LLM sometimes returns e.g. a
    single ``location`` as a string rather than a list). Unknown keys are ignored.

    Arguments:
        klass: The dataclass type to build.
        data: The source mapping (e.g. parsed LLM JSON).
    Returns:
        An instance of ``klass``.
    """
    kwargs = {}
    for field in dcs.fields(klass):
        value = data.get(field.name)
        if value is None:
            value = _default_for(field)
        elif _is_mapping_field(field) and not isinstance(value, Mapping):
            # NOTE: a non-object returned for a mapping field is uninterpretable;
            #   fall back to empty rather than propagating a wrong shape.
            value = {}
        elif not _is_str_field(field) and isinstance(value, str):
            # NOTE: scalar returned for a list field -> wrap it so callers can
            #   iterate items rather than characters.
            value = [value]
        kwargs[field.name] = value
    return klass(**kwargs)


# __END__
