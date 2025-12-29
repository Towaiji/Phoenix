import ast

def check_types(tree):
    types = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if isinstance(target, ast.Name):
                name = target.id
                value = node.value

                if isinstance(value, ast.Constant):
                    inferred = type(value.value).__name__
                else:
                    inferred = type(value).__name__

                if name in types and types[name] != inferred:
                    raise Exception(
                        f"Variable '{name}' changed type "
                        f"({types[name]} → {inferred})"
                    )

                types[name] = inferred
