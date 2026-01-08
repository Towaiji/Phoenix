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
        self.loop_index = 0

    def emit(self, line: str = ""):
        self.lines.append("    " * self.indent + line)

    def emit_helpers(self):
        if self.type_ctx.uses_sum_int:
            self.emit("int phoenix_sum_int(const int *arr, int len) {")
            self.indent += 1
            self.emit("int total = 0;")
            self.emit("for (int i = 0; i < len; i++) {")
            self.indent += 1
            self.emit("total += arr[i];")
            self.indent -= 1
            self.emit("}")
            self.emit("return total;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_sum_float:
            self.emit("double phoenix_sum_double(const double *arr, int len) {")
            self.indent += 1
            self.emit("double total = 0.0;")
            self.emit("for (int i = 0; i < len; i++) {")
            self.indent += 1
            self.emit("total += arr[i];")
            self.indent -= 1
            self.emit("}")
            self.emit("return total;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_min_int_list:
            self.emit("int phoenix_min_int_list(const int *arr, int len) {")
            self.indent += 1
            self.emit("int minv = arr[0];")
            self.emit("for (int i = 1; i < len; i++) {")
            self.indent += 1
            self.emit("if (arr[i] < minv) minv = arr[i];")
            self.indent -= 1
            self.emit("}")
            self.emit("return minv;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_max_int_list:
            self.emit("int phoenix_max_int_list(const int *arr, int len) {")
            self.indent += 1
            self.emit("int maxv = arr[0];")
            self.emit("for (int i = 1; i < len; i++) {")
            self.indent += 1
            self.emit("if (arr[i] > maxv) maxv = arr[i];")
            self.indent -= 1
            self.emit("}")
            self.emit("return maxv;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_min_float_list:
            self.emit("double phoenix_min_double_list(const double *arr, int len) {")
            self.indent += 1
            self.emit("double minv = arr[0];")
            self.emit("for (int i = 1; i < len; i++) {")
            self.indent += 1
            self.emit("if (arr[i] < minv) minv = arr[i];")
            self.indent -= 1
            self.emit("}")
            self.emit("return minv;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_max_float_list:
            self.emit("double phoenix_max_double_list(const double *arr, int len) {")
            self.indent += 1
            self.emit("double maxv = arr[0];")
            self.emit("for (int i = 1; i < len; i++) {")
            self.indent += 1
            self.emit("if (arr[i] > maxv) maxv = arr[i];")
            self.indent -= 1
            self.emit("}")
            self.emit("return maxv;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_str_int:
            self.emit("const char *phoenix_str_int(int value) {")
            self.indent += 1
            self.emit("static char buf[32];")
            self.emit("snprintf(buf, sizeof(buf), \"%d\", value);")
            self.emit("return buf;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_str_float:
            self.emit("const char *phoenix_str_double(double value) {")
            self.indent += 1
            self.emit("static char buf[64];")
            self.emit("snprintf(buf, sizeof(buf), \"%f\", value);")
            self.emit("return buf;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_str_concat:
            self.emit("const char *phoenix_str_concat(const char *a, const char *b) {")
            self.indent += 1
            self.emit("static char buf[256];")
            self.emit("snprintf(buf, sizeof(buf), \"%s%s\", a, b);")
            self.emit("return buf;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_bounds_check:
            self.emit("int phoenix_bounds_check(int idx, int len) {")
            self.indent += 1
            self.emit("if (idx < 0 || idx >= len) {")
            self.indent += 1
            self.emit('fprintf(stderr, "PhoenixError: index %d out of bounds for length %d\\n", idx, len);')
            self.emit("exit(1);")
            self.indent -= 1
            self.emit("}")
            self.emit("return idx;")
            self.indent -= 1
            self.emit("}")
            self.emit()

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
        elif isinstance(node, ast.While):
            self.emit_while(node)
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
        if isinstance(node.iter, ast.List):
            list_type = self._type_of(node.iter)
            if not isinstance(list_type, ListType) or list_type.length is None:
                raise Exception("Unsupported for-loop iterable")
            temp_name = f"__phoenix_list{self.loop_index}"
            self.loop_index += 1
            elem_type = c_type_name(list_type.element_type)
            elems = [self.expr(e) for e in node.iter.elts]
            size = list_type.length
            init = ", ".join(elems)
            self.emit(f"{elem_type} {temp_name}[{size}] = {{{init}}};")
            list_expr = temp_name
            idx = f"__phoenix_i{self.loop_index}"
            self.loop_index += 1
            var = node.target.id
            self.emit(f"for (int {idx} = 0; {idx} < {size}; {idx}++) {{")
            self.indent += 1
            self.emit(f"{elem_type} {var} = {list_expr}[{idx}];")
            for stmt in node.body:
                self.emit_stmt(stmt)
            self.indent -= 1
            self.emit("}")
            return

        if isinstance(node.iter, ast.Call):
            iter_call = node.iter
            args = iter_call.args
            if len(args) == 1:
                start = "0"
                stop = self.expr(args[0])
                step = "1"
            elif len(args) == 2:
                start = self.expr(args[0])
                stop = self.expr(args[1])
                step = "1"
            else:
                start = self.expr(args[0])
                stop = self.expr(args[1])
                step = self.expr(args[2])

            var = node.target.id
            c_type = c_type_name(self._type_of(node.target))
            step_sign = getattr(iter_call, "_phoenix_range_step_sign", 1)
            op = "<" if step_sign > 0 else ">"
            self.emit(f"for ({c_type} {var} = {start}; {var} {op} {stop}; {var} += {step}) {{")
            self.emit_block(node.body)
            self.emit("}")
            return

        list_expr = self.expr(node.iter)
        list_type = self._type_of(node.iter)
        if isinstance(list_type, ListType) and list_type.length is not None:
            idx = f"__phoenix_i{self.loop_index}"
            self.loop_index += 1
            elem_type = c_type_name(list_type.element_type)
            var = node.target.id
            self.emit(f"for (int {idx} = 0; {idx} < {list_type.length}; {idx}++) {{")
            self.indent += 1
            self.emit(f"{elem_type} {var} = {list_expr}[{idx}];")
            for stmt in node.body:
                self.emit_stmt(stmt)
            self.indent -= 1
            self.emit("}")
            return
        raise Exception("Unsupported for-loop iterable")

    def emit_while(self, node: ast.While):
        cond = self.expr(node.test)
        self.emit(f"while ({cond}) {{")
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
                return "1" if node.value else "0"
            if isinstance(node.value, str):
                return json.dumps(node.value)
            return str(node.value)

        if isinstance(node, ast.Subscript):
            arr = self.expr(node.value)
            slice_expr = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
            idx = self.expr(slice_expr)
            list_type = self._type_of(node.value)
            if (
                node in self.type_ctx.runtime_bounds_checks
                and isinstance(list_type, ListType)
                and list_type.length is not None
            ):
                return f"{arr}[phoenix_bounds_check({idx}, {list_type.length})]"
            return f"{arr}[{idx}]"

        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                op = "&&"
            elif isinstance(node.op, ast.Or):
                op = "||"
            else:
                op = "&&"
            parts = [self.expr(v) for v in node.values]
            joined = f" {op} ".join(parts)
            if len(parts) == 1:
                return joined
            return f"({joined})"

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            operand = self.expr(node.operand)
            return f"!({operand})"

        if isinstance(node, ast.Compare):
            left = self.expr(node.left)
            comparator_exprs = [self.expr(c) for c in node.comparators]
            comparisons: List[str] = []
            current_left = left

            def _op_str(op_node: ast.AST) -> str:
                if isinstance(op_node, ast.Eq):
                    return "=="
                if isinstance(op_node, ast.NotEq):
                    return "!="
                if isinstance(op_node, ast.Lt):
                    return "<"
                if isinstance(op_node, ast.LtE):
                    return "<="
                if isinstance(op_node, ast.Gt):
                    return ">"
                if isinstance(op_node, ast.GtE):
                    return ">="
                return "=="

            for op_node, right in zip(node.ops, comparator_exprs):
                comparisons.append(f"{current_left} {_op_str(op_node)} {right}")
                current_left = right

            if len(comparisons) == 1:
                return comparisons[0]
            return "(" + " && ".join(comparisons) + ")"

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "int":
                arg = self.expr(node.args[0])
                return f"(int)({arg})"

            if isinstance(node.func, ast.Name) and node.func.id == "abs":
                arg = self.expr(node.args[0])
                arg_t = self._type_of(node.args[0])
                if isinstance(arg_t, FloatType):
                    return f"fabs({arg})"
                return f"abs({arg})"

            if isinstance(node.func, ast.Name) and node.func.id in {"min", "max"}:
                if len(node.args) == 2:
                    left = self.expr(node.args[0])
                    right = self.expr(node.args[1])
                    if node.func.id == "min":
                        return f"({left} < {right} ? {left} : {right})"
                    return f"({left} > {right} ? {left} : {right})"
                arg = node.args[0]
                arg_t = self._type_of(arg)
                if isinstance(arg_t, ListType) and arg_t.length is not None:
                    if isinstance(arg, ast.List):
                        elem_c = c_type_name(arg_t.element_type)
                        elems = ", ".join(self.expr(e) for e in arg.elts)
                        list_expr = f"({elem_c}[]){{{elems}}}"
                    else:
                        list_expr = self.expr(arg)
                    if isinstance(arg_t.element_type, FloatType):
                        fn = "phoenix_min_double_list" if node.func.id == "min" else "phoenix_max_double_list"
                    else:
                        fn = "phoenix_min_int_list" if node.func.id == "min" else "phoenix_max_int_list"
                    return f"{fn}({list_expr}, {arg_t.length})"

            if isinstance(node.func, ast.Name) and node.func.id == "pow":
                left = self.expr(node.args[0])
                right = self.expr(node.args[1])
                result_t = self._type_of(node)
                if isinstance(result_t, IntType):
                    return f"(int)pow({left}, {right})"
                return f"pow({left}, {right})"

            if isinstance(node.func, ast.Name) and node.func.id == "len":
                arg = node.args[0]
                arg_t = self._type_of(arg)
                if isinstance(arg_t, ListType) and arg_t.length is not None:
                    return str(arg_t.length)
                if isinstance(arg_t, StringType):
                    return f"(int)strlen({self.expr(arg)})"

            if isinstance(node.func, ast.Name) and node.func.id == "sum":
                arg = node.args[0]
                arg_t = self._type_of(arg)
                if isinstance(arg_t, ListType) and arg_t.length is not None:
                    if isinstance(arg, ast.List):
                        elem_c = c_type_name(arg_t.element_type)
                        elems = ", ".join(self.expr(e) for e in arg.elts)
                        list_expr = f"({elem_c}[]){{{elems}}}"
                    else:
                        list_expr = self.expr(arg)
                    if isinstance(arg_t.element_type, FloatType):
                        return f"phoenix_sum_double({list_expr}, {arg_t.length})"
                    return f"phoenix_sum_int({list_expr}, {arg_t.length})"

            if isinstance(node.func, ast.Name) and node.func.id == "round":
                arg = node.args[0]
                arg_t = self._type_of(arg)
                if isinstance(arg_t, IntType):
                    return self.expr(arg)
                return f"round({self.expr(arg)})"

            if isinstance(node.func, ast.Name) and node.func.id == "str":
                arg = node.args[0]
                arg_t = self._type_of(arg)
                if isinstance(arg_t, StringType):
                    return self.expr(arg)
                if isinstance(arg_t, BoolType):
                    return f"({self.expr(arg)} ? \"true\" : \"false\")"
                if isinstance(arg_t, FloatType):
                    return f"phoenix_str_double({self.expr(arg)})"
                if isinstance(arg_t, IntType):
                    return f"phoenix_str_int({self.expr(arg)})"

            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "math"
                    and node.func.attr == "sqrt"
                ):
                    arg = self.expr(node.args[0])
                    return f"sqrt({arg})"
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "math"
                    and node.func.attr in {"sin", "cos", "tan", "floor", "ceil", "log", "exp"}
                ):
                    arg = self.expr(node.args[0])
                    return f"{node.func.attr}({arg})"

            if isinstance(node.func, ast.Name):
                func = node.func.id
                args = ", ".join(self.expr(a) for a in node.args)
                return f"{func}({args})"

            raise Exception("Unsupported function call")

        if isinstance(node, ast.BinOp):
            left = self.expr(node.left)
            right = self.expr(node.right)

            left_t = self._type_of(node.left)
            right_t = self._type_of(node.right)
            if isinstance(node.op, ast.Add) and (
                isinstance(left_t, StringType) or isinstance(right_t, StringType)
            ):
                def _as_str(expr: str, t: Type) -> str:
                    if isinstance(t, StringType):
                        return expr
                    if isinstance(t, IntType):
                        return f"phoenix_str_int({expr})"
                    if isinstance(t, FloatType):
                        return f"phoenix_str_double({expr})"
                    return expr

                left_s = _as_str(left, left_t)
                right_s = _as_str(right, right_t)
                return f"phoenix_str_concat({left_s}, {right_s})"
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
    if type_ctx.uses_string:
        headers.add("<string.h>")
    if type_ctx.uses_stdlib:
        headers.add("<stdlib.h>")
    if type_ctx.uses_str_int or type_ctx.uses_str_float or type_ctx.uses_str_concat:
        headers.add("<stdio.h>")
    if type_ctx.uses_bounds_check:
        headers.update({"<stdio.h>", "<stdlib.h>"})

    for h in sorted(headers):
        emitter.emit(f"#include {h}")
    emitter.emit()

    emitter.emit_helpers()

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
