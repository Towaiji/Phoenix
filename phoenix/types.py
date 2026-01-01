from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


class Type:
    """Base Phoenix type."""

    name: str = "type"

    def is_numeric(self) -> bool:
        return False

    def __repr__(self) -> str:
        return self.__class__.__name__


@dataclass(frozen=True)
class UnknownType(Type):
    name: str = "unknown"


@dataclass(frozen=True)
class IntType(Type):
    name: str = "int"

    def is_numeric(self) -> bool:
        return True


@dataclass(frozen=True)
class FloatType(Type):
    name: str = "float"

    def is_numeric(self) -> bool:
        return True


@dataclass(frozen=True)
class BoolType(Type):
    name: str = "bool"


@dataclass(frozen=True)
class ListType(Type):
    element_type: Type
    length: Optional[int] = None
    name: str = "list"


@dataclass(frozen=True)
class FunctionType(Type):
    param_types: Tuple[Type, ...]
    return_type: Type
    name: str = "function"
