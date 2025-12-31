import ast

def infer_value_type(value):
    if isinstance(value, ast.Constant):
        return type(value.value).__name__
    elif isinstance(value, ast.List):
        return "list"
    else:
        return type(value).__name__

def check_types(tree):
    types = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue

            name = target.id
            value = node.value

            # -------- Rule 2: homogeneous lists --------
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

            # -------- Rule 1: normal values --------
            else:
                inferred = infer_value_type(value)

            # -------- Rule 1: type stability --------
            if name in types and types[name] != inferred:
                raise Exception(
                    f"Variable '{name}' changed type "
                    f"({types[name]} → {inferred})"
                )

            types[name] = inferred
