import ast

class CEmitter:
    def __init__(self):
        self.lines = []
        self.indent = 0
        self.declared = set()
        self.functions = []
        self.uses_math = False

    def emit(self, line=""):
        self.lines.append("    " * self.indent + line)

    def emit_block(self, body):
        self.indent += 1
        for stmt in body:
            self.emit_stmt(stmt)
        self.indent -= 1

    def emit_stmt(self, node):
        # Assignment
        if isinstance(node, ast.Assign):
            self.emit_assign(node)

        # For loop
        elif isinstance(node, ast.For):
            self.emit_for(node)

        # Expression (used for print)
        elif isinstance(node, ast.Expr):
            self.emit_expr(node)

        # Ignore everything else for now

    def emit_assign(self, node):
        target = node.targets[0]
        value = node.value

        # x = ...
        if isinstance(target, ast.Name):
            name = target.id
            is_new = name not in self.declared

            # int literal
            if isinstance(value, ast.Constant) and isinstance(value.value, int):
                if is_new:
                    self.emit(f"int {name} = {value.value};")
                    self.declared.add(name)
                else:
                    self.emit(f"{name} = {value.value};")

            # list[int]
            elif isinstance(value, ast.List):
                elems = [str(e.value) for e in value.elts]
                size = len(elems)
                init = ", ".join(elems)
                self.emit(f"int {name}[{size}] = {{{init}}};")
                self.declared.add(name)

            # x = array[i]
            elif isinstance(value, ast.Subscript):
                rhs = self.expr(value)
                if is_new:
                    self.emit(f"int {name} = {rhs};")
                    self.declared.add(name)
                else:
                    self.emit(f"{name} = {rhs};")

            # x = expression
            elif isinstance(value, ast.BinOp):
                expr = self.expr(value)
                if is_new:
                    self.emit(f"int {name} = {expr};")
                    self.declared.add(name)
                else:
                    self.emit(f"{name} = {expr};")
                    
            # x = function_call(...)
            elif isinstance(value, ast.Call):
                expr = self.expr(value)
                if is_new:
                    self.emit(f"int {name} = {expr};")
                    self.declared.add(name)
                else:
                    self.emit(f"{name} = {expr};")
                    
        # array[i] = expr
        elif isinstance(target, ast.Subscript):
            lhs = self.expr(target)
            rhs = self.expr(value)
            self.emit(f"{lhs} = {rhs};")


    def emit_function(self, node):
        name = node.name
        args = [arg.arg for arg in node.args.args]

        # new scope for function
        old_declared = self.declared
        self.declared = set(args)  # parameters are already declared

        params = ", ".join(f"int {a}" for a in args)
        self.emit(f"int {name}({params}) {{")

        self.indent += 1
        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                expr = self.expr(stmt.value)
                self.emit(f"return {expr};")
            else:
                self.emit_stmt(stmt)
        self.indent -= 1

        self.emit("}")
        self.emit()

        # restore previous scope
        self.declared = old_declared

    def emit_for(self, node):
        iter_call = node.iter
        bound = iter_call.args[0].value
        var = node.target.id

        self.emit(f"for (int {var} = 0; {var} < {bound}; {var}++) {{")
        self.emit_block(node.body)
        self.emit("}")

    def emit_expr(self, node):
        # print(x)
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "print":
                arg = call.args[0]
                expr = self.expr(arg)
                self.emit(f'printf("%d\\n", {expr});')

    def expr(self, node):
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Constant):
            return str(node.value)

        if isinstance(node, ast.Subscript):
            arr = self.expr(node.value)
            idx = self.expr(node.slice)
            return f"{arr}[{idx}]"

        if isinstance(node, ast.Call):
            # int(x) → (int)(x)
            if isinstance(node.func, ast.Name) and node.func.id == "int":
                arg = self.expr(node.args[0])
                return f"(int)({arg})"

            # math.sqrt(x) → sqrt(x)
            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "math"
                    and node.func.attr == "sqrt"
                ):
                    self.uses_math = True
                    arg = self.expr(node.args[0])
                    return f"sqrt({arg})"

            # normal Phoenix function call
            if isinstance(node.func, ast.Name):
                func = node.func.id
                args = ", ".join(self.expr(a) for a in node.args)
                return f"{func}({args})"

            raise Exception("Unsupported function call")



        if isinstance(node, ast.BinOp):
            left = self.expr(node.left)
            right = self.expr(node.right)

            if isinstance(node.op, ast.Add):
                op = "+"
            elif isinstance(node.op, ast.Sub):
                op = "-"
            elif isinstance(node.op, ast.Mult):
                op = "*"
            elif isinstance(node.op, ast.Div):
                op = "/"
            else:
                op = "+"

            return f"{left} {op} {right}"

        return "0"


def transpile(tree):
    emitter = CEmitter()

    emitter.emit("#include <stdio.h>")

    # emit math header only if needed
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if (
                isinstance(n.func.value, ast.Name)
                and n.func.value.id == "math"
                and n.func.attr == "sqrt"
            ):
                emitter.emit("#include <math.h>")
                break

    emitter.emit()


    # pass 1: collect functions
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef):
            emitter.emit_function(stmt)

    emitter.emit("int main() {")
    emitter.indent += 1
    emitter.declared = set()

    # pass 2: main body
    for stmt in tree.body:
        if not isinstance(stmt, ast.FunctionDef):
            emitter.emit_stmt(stmt)

    emitter.emit("return 0;")
    emitter.indent -= 1
    emitter.emit("}")

    return "\n".join(emitter.lines)

