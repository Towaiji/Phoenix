import ast
import json
from typing import Iterable, Set, List 

from phoenix.c_types import c_type_name, required_headers
from phoenix.type_inference import TypeContext
from phoenix.types import (
    BoolType,
    FloatType,
    IntType,
    ListType,
    StringType,
    Type,
    UnknownType,
)


class CEmitter:
    def __init__(self, type_ctx: TypeContext):
        self.lines = []
        self.indent = 0
        self.declared: Set[str] = set()
        self.functions = []
        self.type_ctx = type_ctx

    def emit(self, line: str = ""):
        self.lines.append("    " * self.indent + line)

    def emit_block(self, body):
        self.indent += 1
        for stmt in body:
            self.emit_stmt(stmt)
        self.indent -= 1

    # ---- helpers -------------------------------------------------
    def _type_of(self, node: ast.AST) -> Type:
        return self.type_ctx.node_types.get(node, UnknownType())

    def emit_stmt(self, node):
        if isinstance(node, ast.Assign):
            self.emit_assign(node)
        elif isinstance(node, ast.For):
            self.emit_for(node)
        elif isinstance(node, ast.If):
            self.emit_if(node)
        elif isinstance(node, ast.Expr):
            self.emit_expr(node)

    def emit_assign(self, node: ast.Assign):
        target = node.targets[0]
        value = node.value

        if isinstance(target, ast.Name):
            name = target.id
            is_new = name not in self.declared
            t = self._type_of(target)
            c_type = c_type_name(t)

            if isinstance(value, ast.List) and isinstance(t, ListType):
                elems = [self.expr(e) for e in value.elts]
                size = t.length if t.length is not None else len(elems)
                init = ", ".join(elems)
                self.emit(f"{c_type} {name}[{size}] = {{{init}}};")
                self.declared.add(name)
                return

            rhs = self.expr(value)
            if is_new:
                self.emit(f"{c_type} {name} = {rhs};")
                self.declared.add(name)
            else:
                self.emit(f"{name} = {rhs};")

        elif isinstance(target, ast.Subscript):
            lhs = self.expr(target)
            rhs = self.expr(value)
            self.emit(f"{lhs} = {rhs};")

    def emit_function(self, node: ast.FunctionDef):
        name = node.name
        args = [arg.arg for arg in node.args.args]
        func_type = self.type_ctx.functions.get(name)

        param_types = func_type.param_types if func_type else [UnknownType()] * len(args)
        return_type = func_type.return_type if func_type else IntType()

        old_declared = self.declared
        self.declared = set(args)

        def _param_decl(t: Type, name: str) -> str:
            if isinstance(t, ListType):
                return f"{c_type_name(t.element_type)} {name}[]"
            return f"{c_type_name(t)} {name}"

        params = ", ".join(_param_decl(t, a) for t, a in zip(param_types, args))
        self.emit(f"{c_type_name(return_type)} {name}({params}) {{")

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
        self.declared = old_declared

    def emit_for(self, node):
        iter_call = node.iter
        bound = iter_call.args[0].value
        var = node.target.id

        c_type = c_type_name(self._type_of(node.target))
        self.emit(f"for ({c_type} {var} = 0; {var} < {bound}; {var}++) {{")
        self.emit_block(node.body)
        self.emit("}")

    def emit_if(self, node: ast.If):
        cond = self.expr(node.test)
        self.emit(f"if ({cond}) {{")
        self.emit_block(node.body)
        if node.orelse:
            self.emit("} else {")
            self.emit_block(node.orelse)
        self.emit("}")

    def emit_expr(self, node):
        if isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "print":
                arg = call.args[0]
                expr = self.expr(arg)
                t = self._type_of(arg)
                if isinstance(t, FloatType):
                    fmt = "%f"
                elif isinstance(t, StringType):
                    fmt = "%s"
                else:
                    fmt = "%d"
                self.emit(f'printf("{fmt}\\n", {expr});')

    def expr(self, node):
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "true" if node.value else "false"
            if isinstance(node.value, str):
                return json.dumps(node.value)
            return str(node.value)

        if isinstance(node, ast.Subscript):
            arr = self.expr(node.value)
            idx = self.expr(node.slice)
            return f"{arr}[{idx}]"

        if isinstance(node, ast.Compare):
            left = self.expr(node.left)
            right = self.expr(node.comparators[0])
            op = node.ops[0]
            if isinstance(op, ast.Eq):
                op_str = "=="
            elif isinstance(op, ast.NotEq):
                op_str = "!="
            elif isinstance(op, ast.Lt):
                op_str = "<"
            elif isinstance(op, ast.LtE):
                op_str = "<="
            elif isinstance(op, ast.Gt):
                op_str = ">"
            elif isinstance(op, ast.GtE):
                op_str = ">="
            else:
                op_str = "=="
            return f"{left} {op_str} {right}"

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "int":
                arg = self.expr(node.args[0])
                return f"(int)({arg})"

            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "math"
                    and node.func.attr == "sqrt"
                ):
                    arg = self.expr(node.args[0])
                    return f"sqrt({arg})"

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


def _collect_types(type_ctx: TypeContext) -> Iterable[Type]:
    seen: List[Type] = []
    seen.extend(type_ctx.globals.values())
    for ft in type_ctx.functions.values():
        seen.extend(list(ft.param_types))
        seen.append(ft.return_type)
    return seen


def transpile(tree, type_ctx: TypeContext):
    emitter = CEmitter(type_ctx)

    headers = {"<stdio.h>"}
    headers.update(required_headers(_collect_types(type_ctx)))
    if type_ctx.uses_math:
        headers.add("<math.h>")

    for h in sorted(headers):
        emitter.emit(f"#include {h}")
    emitter.emit()

    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef):
            emitter.emit_function(stmt)

    emitter.emit("int main() {")
    emitter.indent += 1
    emitter.declared = set()

    for stmt in tree.body:
        if not isinstance(stmt, ast.FunctionDef):
            emitter.emit_stmt(stmt)

    emitter.emit("return 0;")
    emitter.indent -= 1
    emitter.emit("}")

    return "\n".join(emitter.lines)
