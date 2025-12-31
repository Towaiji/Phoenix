import ast

BANNED_CALLS = {"eval", "exec", "__import__"}
BANNED_ATTRS = {("importlib", "import_module")}

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


def check_types(tree):
    types = {}

    for node in ast.walk(tree):

        # -------- Rule 3: ban dynamic execution/imports --------
        if isinstance(node, ast.Call):
            # eval(...), exec(...), __import__(...)
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
                raise Exception(
                    f"Use of '{node.func.id}' is forbidden. "
                    "Dynamic execution breaks performance guarantees."
                )

            # importlib.import_module(...)
            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in BANNED_ATTRS
                ):
                    raise Exception(
                        "Dynamic imports are forbidden. "
                        "Performance cannot be proven."
                    )

        # -------- existing Rule 1 & 2 logic (keep as-is) --------
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue

            name = target.id
            value = node.value

            if isinstance(value, ast.List):
                elem_types = set()
                for elem in value.elts:
                    if isinstance(elem, ast.Constant):
                        elem_types.add(type(elem.value).__name__)
                    else:
                        elem_types.add(type(elem).__name__)

                if len(elem_types) > 1:
                    raise Exception(
                        f"List assigned to '{name}' has mixed element types: "
                        f"{', '.join(elem_types)}"
                    )

                inferred = f"list[{elem_types.pop()}]" if elem_types else "list[empty]"
            else:
                inferred = infer_expr_type(value, types)

            if name in types and types[name] != inferred:
                raise Exception(
                    f"Variable '{name}' changed type "
                    f"({types[name]} → {inferred})"
                )

            types[name] = inferred
