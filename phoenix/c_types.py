from __future__ import annotations

from typing import Iterable, Set

from phoenix.types import BoolType, DictType, FloatType, IntType, ListType, SetType, Type


def c_type_name(t: Type) -> str:
    """Return the C11 type name for a Phoenix type."""
    if isinstance(t, IntType):
        return "int"
    if isinstance(t, FloatType):
        return "double"
    if isinstance(t, BoolType):
        return "bool"
    from phoenix.types import StringType  # local import to avoid cycle
    if isinstance(t, StringType):
        return "const char *"
    if isinstance(t, ListType):
        if t.length is None:
            if isinstance(t.element_type, IntType):
                return "PhoenixListInt"
            if isinstance(t.element_type, FloatType):
                return "PhoenixListDouble"
            if isinstance(t.element_type, BoolType):
                return "PhoenixListBool"
            from phoenix.types import StringType  # local import to avoid cycle
            if isinstance(t.element_type, StringType):
                return "PhoenixListString"
        return c_type_name(t.element_type)
    if isinstance(t, DictType):
        key = _dict_key_suffix(t.key_type)
        val = _dict_val_suffix(t.value_type)
        return f"PhoenixDict{key}{val}"
    if isinstance(t, SetType):
        elem = _set_elem_suffix(t.element_type)
        return f"PhoenixSet{elem}"
    # Unknown fallback keeps the C code compilable; checker should guard earlier.
    return "int"


def _dict_key_suffix(t: Type) -> str:
    if isinstance(t, IntType):
        return "Int"
    from phoenix.types import StringType  # local import to avoid cycle
    if isinstance(t, StringType):
        return "String"
    return "Int"


def _dict_val_suffix(t: Type) -> str:
    if isinstance(t, IntType):
        return "Int"
    if isinstance(t, FloatType):
        return "Double"
    if isinstance(t, BoolType):
        return "Bool"
    from phoenix.types import StringType  # local import to avoid cycle
    if isinstance(t, StringType):
        return "String"
    if isinstance(t, ListType):
        if isinstance(t.element_type, IntType):
            return "ListInt"
        if isinstance(t.element_type, FloatType):
            return "ListDouble"
        if isinstance(t.element_type, BoolType):
            return "ListBool"
        if isinstance(t.element_type, StringType):
            return "ListString"
    return "Int"


def _set_elem_suffix(t: Type) -> str:
    if isinstance(t, IntType):
        return "Int"
    from phoenix.types import StringType  # local import to avoid cycle
    if isinstance(t, StringType):
        return "String"
    return "Int"


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
