import ast

class CEmitter:
    def __init__(self):
        self.lines = []
        self.indent = 0
        self.last_int_var = None

    def emit(self, line=""):
        self.lines.append("    " * self.indent + line)

    def emit_block(self, body):
        self.indent += 1
        for stmt in body:
            self.emit_stmt(stmt)
        self.indent -= 1

    def emit_stmt(self, node):
        # x = 5
        if isinstance(node, ast.Assign):
            self.emit_assign(node)

        # for i in range(N)
        elif isinstance(node, ast.For):
            self.emit_for(node)

        # ignore anything else for now

    def emit_assign(self, node):
        target = node.targets[0]

        # x = <expr>
        if isinstance(target, ast.Name):
            name = target.id
            value = node.value

            # int literal
            if isinstance(value, ast.Constant) and isinstance(value.value, int):
                self.emit(f"int {name} = {value.value};")
                self.last_int_var = name

            # list[int]
            elif isinstance(value, ast.List):
                elems = [str(e.value) for e in value.elts]
                size = len(elems)
                init = ", ".join(elems)
                self.emit(f"int {name}[{size}] = {{{init}}};")

            # binary op: x = a + b
            elif isinstance(value, ast.BinOp):
                left = self.expr(value.left)
                right = self.expr(value.right)
                self.emit(f"{name} = {left} + {right};")
                self.last_int_var = name

    def emit_for(self, node):
        # for i in range(N)
        iter_call = node.iter
        bound = iter_call.args[0].value
        var = node.target.id

        self.emit(f"for (int {var} = 0; {var} < {bound}; {var}++) {{")
        self.emit_block(node.body)
        self.emit("}")

    def expr(self, node):
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Constant):
            return str(node.value)

        if isinstance(node, ast.Subscript):
            arr = self.expr(node.value)
            idx = self.expr(node.slice)
            return f"{arr}[{idx}]"

        return "0"


def transpile(tree):
    emitter = CEmitter()

    emitter.emit("#include <stdio.h>")
    emitter.emit()
    emitter.emit("int main() {")

    emitter.indent += 1
    for stmt in tree.body:
        emitter.emit_stmt(stmt)

    # print result
    if emitter.last_int_var:
        emitter.emit()
        emitter.emit(f'printf("%d\\n", {emitter.last_int_var});')

    emitter.emit("return 0;")
    emitter.indent -= 1
    emitter.emit("}")

    return "\n".join(emitter.lines)
