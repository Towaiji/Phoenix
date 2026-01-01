from __future__ import annotations

from typing import Iterable, Set

from phoenix.types import BoolType, FloatType, IntType, ListType, Type


def c_type_name(t: Type) -> str:
    """Return the C11 type name for a Phoenix type."""
    if isinstance(t, IntType):
        return "int"
    if isinstance(t, FloatType):
        return "double"
    if isinstance(t, BoolType):
        return "bool"
    if isinstance(t, ListType):
        return c_type_name(t.element_type)
    # Unknown fallback keeps the C code compilable; checker should guard earlier.
    return "int"


def required_headers(types: Iterable[Type]) -> Set[str]:
    """Collect C headers needed for the given types."""
    headers: Set[str] = set()
    for t in types:
        if isinstance(t, BoolType):
            headers.add("<stdbool.h>")
        if isinstance(t, FloatType):
            headers.add("<math.h>")  # sqrt and friends live here
        if isinstance(t, ListType):
            headers.update(required_headers([t.element_type]))
    return headers
