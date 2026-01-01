import ast
from typing import List

from phoenix.errors import PhoenixError
from phoenix.type_inference import TypeContext, infer_types

BANNED_CALLS = {"eval", "exec", "__import__"}
BANNED_ATTRS = {("importlib", "import_module")}


def _error(msg: str, node: ast.AST, filename: str, lines: List[str]) -> PhoenixError:
    return PhoenixError(
        msg,
        lineno=node.lineno,
        col=node.col_offset + 1,
        source=lines[node.lineno - 1],
        filename=filename,
    )


def _check_control_flow(tree: ast.AST, filename: str, lines: List[str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            raise _error(
                "While-loops are forbidden. Loop bounds must be statically known.",
                node,
                filename,
                lines,
            )

        if isinstance(node, ast.For):
            if not isinstance(node.iter, ast.Call):
                raise _error(
                    "For-loop iterable must be a statically known range().",
                    node,
                    filename,
                    lines,
                )

            if not isinstance(node.iter.func, ast.Name) or node.iter.func.id != "range":
                raise _error(
                    "For-loops must use range() with static bounds.",
                    node,
                    filename,
                    lines,
                )

            for arg in node.iter.args:
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, int):
                    raise _error(
                        "range() bounds must be integer literals.",
                        node,
                        filename,
                        lines,
                    )


def _check_dynamic_features(tree: ast.AST, filename: str, lines: List[str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
                raise _error(
                    f"Use of '{node.func.id}' is forbidden. "
                    "Dynamic execution breaks performance guarantees.",
                    node,
                    filename,
                    lines,
                )

            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in BANNED_ATTRS
                ):
                    raise _error(
                        "Dynamic imports are forbidden. Performance cannot be proven.",
                        node,
                        filename,
                        lines,
                    )


def check_types(tree: ast.AST, filename: str, lines: List[str]) -> TypeContext:
    _check_control_flow(tree, filename, lines)
    _check_dynamic_features(tree, filename, lines)
    # Inference enforces type stability and homogeneous aggregates.
    return infer_types(tree, filename, lines)
