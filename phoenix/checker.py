import ast
from phoenix.errors import PhoenixError

BANNED_CALLS = {"eval", "exec", "__import__"}
BANNED_ATTRS = {("importlib", "import_module")}


def error(msg, node, filename, lines):
    raise PhoenixError(
        msg,
        lineno=node.lineno,
        col=node.col_offset + 1,
        source=lines[node.lineno - 1],
        filename=filename,
    )


def infer_expr_type(expr, types):
    if isinstance(expr, ast.Constant):
        return type(expr.value).__name__

    if isinstance(expr, ast.Name):
        return types.get(expr.id, "unknown")

    if isinstance(expr, ast.BinOp):
        left = infer_expr_type(expr.left, types)
        right = infer_expr_type(expr.right, types)
        if left == right:
            return left
        return "unknown"

    if isinstance(expr, ast.Subscript):
        return "int"  # assume list[int] indexing for now

    return "unknown"


def check_types(tree, filename, lines):
    types = {}

    for node in ast.walk(tree):

        # -------- Rule 4: static loop bounds --------
        if isinstance(node, ast.While):
            error(
                "While-loops are forbidden. Loop bounds must be statically known.",
                node,
                filename,
                lines,
            )

        if isinstance(node, ast.For):
            if not isinstance(node.iter, ast.Call):
                error(
                    "For-loop iterable must be a statically known range().",
                    node,
                    filename,
                    lines,
                )

            if not isinstance(node.iter.func, ast.Name) or node.iter.func.id != "range":
                error(
                    "For-loops must use range() with static bounds.",
                    node,
                    filename,
                    lines,
                )

            for arg in node.iter.args:
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, int):
                    error(
                        "range() bounds must be integer literals.",
                        node,
                        filename,
                        lines,
                    )

        # -------- Rule 3: ban dynamic execution/imports --------
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
                error(
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
                    error(
                        "Dynamic imports are forbidden. Performance cannot be proven.",
                        node,
                        filename,
                        lines,
                    )

        # -------- Rule 1 & 2: assignments --------
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue

            name = target.id
            value = node.value

            # Rule 2: homogeneous lists
            if isinstance(value, ast.List):
                elem_types = set()
                for elem in value.elts:
                    if isinstance(elem, ast.Constant):
                        elem_types.add(type(elem.value).__name__)
                    else:
                        elem_types.add(type(elem).__name__)

                if len(elem_types) > 1:
                    error(
                        f"List assigned to '{name}' has mixed element types: "
                        f"{', '.join(elem_types)}",
                        node,
                        filename,
                        lines,
                    )

                inferred = f"list[{elem_types.pop()}]" if elem_types else "list[empty]"

            else:
                inferred = infer_expr_type(value, types)

            # Rule 1: type stability
            if name in types and types[name] != inferred:
                error(
                    f"Variable '{name}' changed type "
                    f"({types[name]} → {inferred})",
                    node,
                    filename,
                    lines,
                )

            types[name] = inferred
