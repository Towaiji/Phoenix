import ast

def transpile(tree):
    lines = []
    lines.append("#include <stdio.h>")
    lines.append("")
    lines.append("int main() {")

    indent = "    "

    for node in ast.walk(tree):

        # int variable assignment
        if isinstance(node, ast.Assign):
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue

            name = target.id
            value = node.value

            # int literal
            if isinstance(value, ast.Constant) and isinstance(value.value, int):
                lines.append(f"{indent}int {name} = {value.value};")

            # list[int]
            elif isinstance(value, ast.List):
                elems = [str(e.value) for e in value.elts]
                size = len(elems)
                init = ", ".join(elems)
                lines.append(
                    f"{indent}int {name}[{size}] = {{{init}}};"
                )

        # for i in range(N)
        if isinstance(node, ast.For):
            if (
                isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"
            ):
                bound = node.iter.args[0].value
                var = node.target.id
                lines.append(
                    f"{indent}for (int {var} = 0; {var} < {bound}; {var}++) {{"
                )

                # body
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        t = stmt.targets[0].id
                        v = stmt.value
                        if isinstance(v, ast.BinOp):
                            left = v.left.id
                            right = f"{v.right.value.id}[{var}]"
                            lines.append(
                                f"{indent*2}{t} = {left} + {right};"
                            )

                lines.append(f"{indent}}}")

    lines.append("")
    lines.append(f"{indent}return 0;")
    lines.append("}")

    return "\n".join(lines)
