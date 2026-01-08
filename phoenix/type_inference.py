from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from phoenix.errors import PhoenixError
from phoenix.types import (
    BoolType,
    FloatType,
    FunctionType,
    IntType,
    ListType,
    StringType,
    Type,
    UnknownType,
)


def _error(
    msg: str,
    node: ast.AST,
    filename: str,
    lines: List[str],
    hint: str | None = None,
) -> PhoenixError:
    lineno = getattr(node, "lineno", None)
    col = getattr(node, "col_offset", None)
    return PhoenixError(
        msg,
        lineno=lineno,
        col=col + 1 if col is not None else None,
        source=lines[lineno - 1] if lineno is not None and lineno - 1 < len(lines) else None,
        filename=filename,
        hint=hint,
    )


@dataclass
class TypeContext:
    globals: Dict[str, Type] = field(default_factory=dict)
    node_types: Dict[ast.AST, Type] = field(default_factory=dict)
    functions: Dict[str, FunctionType] = field(default_factory=dict)
    uses_math: bool = False
    uses_string: bool = False
    uses_stdlib: bool = False
    uses_sum_int: bool = False
    uses_sum_float: bool = False
    uses_str_int: bool = False
    uses_str_float: bool = False
    uses_str_concat: bool = False
    uses_bounds_check: bool = False
    runtime_bounds_checks: set = field(default_factory=set)
    uses_min_int_list: bool = False
    uses_max_int_list: bool = False
    uses_min_float_list: bool = False
    uses_max_float_list: bool = False


class TypeInferencer(ast.NodeVisitor):
    def __init__(self, filename: str, lines: List[str]):
        self.filename = filename
        self.lines = lines
        self.ctx = TypeContext()
        self.env_stack: List[Dict[str, Type]] = [self.ctx.globals]
        self.current_function: Optional[str] = None
        self.return_types: List[Type] = []
        self.function_defs: Dict[str, ast.FunctionDef] = {}
        self.function_param_hints: Dict[str, List[Type]] = {}
        self.in_if: bool = False
        self.conditional_depth: int = 0
        self.branch_assignments: Dict[str, ast.AST] = {}
        self.analysis_pass: str = "init"

    def infer(self, tree: ast.AST) -> TypeContext:
        function_defs = [stmt for stmt in tree.body if isinstance(stmt, ast.FunctionDef)]

        # Register function stubs so calls can record argument types even before analysis.
        for func in function_defs:
            param_types: List[Type] = [UnknownType() for _ in func.args.args]
            self.ctx.functions[func.name] = FunctionType(tuple(param_types), UnknownType())
            self.function_defs[func.name] = func

        # First pass: globals and calls (skip function bodies).
        self.analysis_pass = "globals_first"
        for stmt in tree.body:
            if not isinstance(stmt, ast.FunctionDef):
                self.visit(stmt)

        # Second pass: analyze functions with any recorded parameter hints.
        self.analysis_pass = "functions"
        for func in function_defs:
            self.visit(func)

        # Third pass: refresh globals now that function return types are known.
        self.analysis_pass = "globals_final"
        for stmt in tree.body:
            if not isinstance(stmt, ast.FunctionDef):
                self.visit(stmt)
        return self.ctx

    # ---- helpers -------------------------------------------------
    def error(self, msg: str, node: ast.AST, hint: str | None = None) -> None:
        raise _error(msg, node, self.filename, self.lines, hint=hint)

    def annotate(self, node: ast.AST, t: Type) -> Type:
        self.ctx.node_types[node] = t
        return t

    def lookup(self, name: str) -> Type:
        for env in reversed(self.env_stack):
            if name in env:
                return env[name]
        return UnknownType()

    def bind(self, name: str, t: Type, node: ast.AST) -> None:
        env = self.env_stack[-1]
        existing = env.get(name)
        if existing and not isinstance(existing, UnknownType) and existing != t:
            self.error(
                f"Variable '{name}' changed type ({existing} → {t})",
                node,
                hint="Keep a single type or use a new variable.",
            )
        env[name] = t

    # ---- visitors ------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        hinted_params = self.function_param_hints.get(
            node.name, [UnknownType() for _ in node.args.args]
        )
        # Pad/truncate in case of mismatch; zip below handles differing lengths safely.
        param_types: List[Type] = list(hinted_params[: len(node.args.args)])
        if len(param_types) < len(node.args.args):
            param_types.extend([UnknownType()] * (len(node.args.args) - len(param_types)))
        func_type = FunctionType(tuple(param_types), UnknownType())
        self.ctx.functions[node.name] = func_type

        # new scope for function body
        self.env_stack.append({arg.arg: t for arg, t in zip(node.args.args, param_types)})
        self.current_function = node.name
        self.return_types = []

        for stmt in node.body:
            self.visit(stmt)

        return_type = self._resolve_return_type(node)
        self.ctx.functions[node.name] = FunctionType(tuple(param_types), return_type)

        self.env_stack.pop()
        self.current_function = None
        self.return_types = []

    def visit_Assign(self, node: ast.Assign) -> None:
        target = node.targets[0]
        value_type = self.infer_expr(node.value)
        if isinstance(target, ast.Name):
            if self.conditional_depth > 0 and target.id not in self.env_stack[-1]:
                self.error(
                    f"Variable '{target.id}' must exist before conditional assignment",
                    node,
                    hint="Initialize the variable before the if/else.",
                )
            self.bind(target.id, value_type, node)
            self.annotate(target, value_type)
        self.annotate(node, value_type)

    def visit_Expr(self, node: ast.Expr) -> None:
        value_type = self.infer_expr(node.value)
        self.annotate(node, value_type)

    def visit_For(self, node: ast.For) -> None:
        iter_type = self.infer_expr(node.iter)
        target_type: Type = IntType()
        if isinstance(iter_type, ListType):
            target_type = iter_type.element_type
        if isinstance(node.target, ast.Name):
            self.bind(node.target.id, target_type, node)
            self.annotate(node.target, target_type)
        for stmt in node.body:
            self.visit(stmt)

    def visit_While(self, node: ast.While) -> None:
        cond_type = self.infer_expr(node.test)
        if not isinstance(cond_type, BoolType):
            if not (isinstance(cond_type, UnknownType) and self.analysis_pass == "globals_first"):
                self.error(
                    "while condition must be a bool",
                    node.test,
                    hint="Use comparisons/logical ops to produce a boolean.",
                )

        for stmt in node.body:
            self.visit(stmt)

    def visit_If(self, node: ast.If) -> None:
        if self.in_if:
            self.error(
                "Nested if-statements are not supported",
                node,
                hint="Flatten the logic into a single if/else.",
            )
        if node.orelse and isinstance(node.orelse[0], ast.If):
            self.error(
                "elif is not supported",
                node,
                hint="Use a separate if/else or rewrite the condition.",
            )

        cond_type = self.infer_expr(node.test)
        if not isinstance(cond_type, BoolType):
            if isinstance(cond_type, UnknownType) and self.analysis_pass == "globals_first":
                pass
            else:
                self.error(
                    "if condition must be a bool",
                    node.test,
                    hint="Use comparisons/logical ops to produce a boolean.",
                )

        body_assigned, body_first = self._collect_assignments(node.body)
        else_assigned, else_first = self._collect_assignments(node.orelse)

        if not node.orelse and body_assigned:
            first_var = next(iter(body_assigned))
            self.error(
                f"Variable '{first_var}' assigned only in one branch",
                body_first[first_var],
                hint="Assign the variable before the if or in both branches.",
            )

        missing_in_else = body_assigned - else_assigned
        missing_in_body = else_assigned - body_assigned
        if missing_in_else:
            var = next(iter(missing_in_else))
            self.error(
                f"Variable '{var}' assigned only in one branch",
                body_first[var],
                hint="Assign the variable in both branches.",
            )
        if missing_in_body:
            var = next(iter(missing_in_body))
            self.error(
                f"Variable '{var}' assigned only in one branch",
                else_first[var],
                hint="Assign the variable in both branches.",
            )

        self.in_if = True
        self.conditional_depth += 1
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        self.conditional_depth -= 1
        self.in_if = False

    def visit_Return(self, node: ast.Return) -> None:
        if node.value is None:
            self.return_types.append(UnknownType())
        else:
            ret_type = self.infer_expr(node.value)
            self.return_types.append(ret_type)

    def generic_visit(self, node: ast.AST) -> None:
        super().generic_visit(node)

    # ---- expression inference -----------------------------------
    def infer_expr(self, expr: ast.AST) -> Type:
        if isinstance(expr, ast.Constant):
            value = expr.value
            if isinstance(value, bool):
                return self.annotate(expr, BoolType())
            if isinstance(value, float):
                return self.annotate(expr, FloatType())
            if isinstance(value, int):
                return self.annotate(expr, IntType())
            if isinstance(value, str):
                return self.annotate(expr, StringType())
            return self.annotate(expr, UnknownType())

        if isinstance(expr, ast.Name):
            t = self.lookup(expr.id)
            return self.annotate(expr, t)

        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, (ast.USub, ast.UAdd)):
            operand = self.infer_expr(expr.operand)
            if operand.is_numeric():
                return self.annotate(expr, operand)
            return self.annotate(expr, UnknownType())

        if isinstance(expr, ast.List):
            if not expr.elts:
                return self.annotate(expr, ListType(UnknownType(), length=0))

            elem_types = [self.infer_expr(e) for e in expr.elts]
            element_type: Type = UnknownType()
            for t in elem_types:
                if isinstance(t, UnknownType):
                    if not isinstance(element_type, UnknownType):
                        self.error(
                            "List elements must share a single static type",
                            expr,
                            hint="Use a single element type in each list.",
                        )
                    continue
                if isinstance(element_type, UnknownType):
                    element_type = t
                    continue
                if t != element_type:
                    self.error(
                        "List elements must share a single static type",
                        expr,
                        hint="Use a single element type in each list.",
                    )
            return self.annotate(expr, ListType(element_type, length=len(expr.elts)))

        if isinstance(expr, ast.Subscript):
            value_type = self.infer_expr(expr.value)
            slice_expr = expr.slice.value if isinstance(expr.slice, ast.Index) else expr.slice
            index_type = self.infer_expr(slice_expr)
            if not isinstance(index_type, IntType):
                self.error(
                    "List index must be an int",
                    slice_expr,
                    hint="Use an integer index.",
                )
            if isinstance(value_type, ListType):
                result = value_type.element_type
            else:
                result = UnknownType()
            return self.annotate(expr, result)

        if isinstance(expr, ast.BoolOp):
            operand_types = [self.infer_expr(v) for v in expr.values]
            for t in operand_types:
                if not isinstance(t, BoolType):
                    self.error(
                        "Logical operations require boolean operands",
                        expr,
                        hint="Compare values first, e.g. `x < y`.",
                    )
            return self.annotate(expr, BoolType())

        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
            operand_type = self.infer_expr(expr.operand)
            if not isinstance(operand_type, BoolType):
                self.error(
                    "Logical operations require boolean operands",
                    expr,
                    hint="Compare values first, e.g. `x < y`.",
                )
            return self.annotate(expr, BoolType())

        if isinstance(expr, ast.Compare):
            allowed_ops = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
            for op in expr.ops:
                if not isinstance(op, allowed_ops):
                    self.error(
                        "Unsupported comparison operator",
                        expr,
                        hint="Use ==, !=, <, <=, >, or >=.",
                    )

            operands = [expr.left] + list(expr.comparators)
            operand_types = [self.infer_expr(o) for o in operands]
            for t in operand_types:
                if not t.is_numeric():
                    self.error(
                        "Comparisons are only supported for numeric types",
                        expr,
                        hint="Compare ints/floats only.",
                    )

            return self.annotate(expr, BoolType())

        if isinstance(expr, ast.BinOp):
            left = self.infer_expr(expr.left)
            right = self.infer_expr(expr.right)
            if isinstance(expr.op, ast.Add) and isinstance(left, StringType) and isinstance(right, StringType):
                self.ctx.uses_str_concat = True
                return self.annotate(expr, StringType())
            if isinstance(expr.op, ast.Add) and isinstance(left, StringType) and isinstance(
                right, (IntType, FloatType)
            ):
                if isinstance(right, IntType):
                    self.ctx.uses_str_int = True
                else:
                    self.ctx.uses_str_float = True
                self.ctx.uses_str_concat = True
                return self.annotate(expr, StringType())
            if isinstance(expr.op, ast.Add) and isinstance(right, StringType) and isinstance(
                left, (IntType, FloatType)
            ):
                if isinstance(left, IntType):
                    self.ctx.uses_str_int = True
                else:
                    self.ctx.uses_str_float = True
                self.ctx.uses_str_concat = True
                return self.annotate(expr, StringType())
            if isinstance(left, FloatType) or isinstance(right, FloatType):
                return self.annotate(expr, FloatType())
            if isinstance(left, IntType) and isinstance(right, IntType):
                return self.annotate(expr, IntType())
            if left.is_numeric() and right.is_numeric():
                return self.annotate(expr, FloatType())
            return self.annotate(expr, UnknownType())

        if isinstance(expr, ast.Call):
            return self._infer_call(expr)

        return self.annotate(expr, UnknownType())

    def _infer_call(self, expr: ast.Call) -> Type:
        arg_types = [self.infer_expr(a) for a in expr.args]

        # int(x)
        if isinstance(expr.func, ast.Name) and expr.func.id == "int":
            return self.annotate(expr, IntType())

        # abs(x)
        if isinstance(expr.func, ast.Name) and expr.func.id == "abs":
            if len(arg_types) != 1 or not arg_types[0].is_numeric():
                self.error(
                    "abs() expects a single numeric argument",
                    expr,
                    hint="Use abs(<int|float>).",
                )
            if isinstance(arg_types[0], FloatType):
                self.ctx.uses_math = True
                return self.annotate(expr, FloatType())
            self.ctx.uses_stdlib = True
            return self.annotate(expr, IntType())

        # min(a, b) / max(a, b)
        if isinstance(expr.func, ast.Name) and expr.func.id in {"min", "max"}:
            if len(arg_types) == 2:
                if not (arg_types[0].is_numeric() and arg_types[1].is_numeric()):
                    self.error(
                        f"{expr.func.id}() expects two numeric arguments",
                        expr,
                        hint="Use min(a, b) or max(a, b) with numbers.",
                    )
                return self.annotate(expr, self._unify_types(arg_types[0], arg_types[1]))
            if len(arg_types) == 1 and isinstance(arg_types[0], ListType):
                list_t = arg_types[0]
                if list_t.length is None:
                    self.error(
                        f"{expr.func.id}() requires a list with known length",
                        expr,
                        hint="Use a list literal or assign from a literal first.",
                    )
                if list_t.length == 0:
                    self.error(
                        f"{expr.func.id}() cannot operate on an empty list",
                        expr,
                        hint="Provide at least one element.",
                    )
                if not list_t.element_type.is_numeric():
                    self.error(
                        f"{expr.func.id}() requires a list of numbers",
                        expr,
                        hint="Use a list of ints or floats.",
                    )
                if isinstance(list_t.element_type, FloatType):
                    if expr.func.id == "min":
                        self.ctx.uses_min_float_list = True
                    else:
                        self.ctx.uses_max_float_list = True
                else:
                    if expr.func.id == "min":
                        self.ctx.uses_min_int_list = True
                    else:
                        self.ctx.uses_max_int_list = True
                return self.annotate(expr, list_t.element_type)
            self.error(
                f"{expr.func.id}() expects two numbers or one list",
                expr,
                hint="Use min(a, b), max(a, b), or min(list)/max(list).",
            )

        # pow(a, b)
        if isinstance(expr.func, ast.Name) and expr.func.id == "pow":
            if len(arg_types) != 2 or not (arg_types[0].is_numeric() and arg_types[1].is_numeric()):
                self.error(
                    "pow() expects two numeric arguments",
                    expr,
                    hint="Use pow(base, exp) with numbers.",
                )
            self.ctx.uses_math = True
            if isinstance(arg_types[0], FloatType) or isinstance(arg_types[1], FloatType):
                return self.annotate(expr, FloatType())
            return self.annotate(expr, IntType())

        # len(x)
        if isinstance(expr.func, ast.Name) and expr.func.id == "len":
            if len(arg_types) != 1:
                self.error(
                    "len() expects a single argument",
                    expr,
                    hint="Use len(list) or len(string).",
                )
            arg_t = arg_types[0]
            if isinstance(arg_t, ListType):
                if arg_t.length is None:
                    self.error(
                        "len() requires a list with known length",
                        expr,
                        hint="Use a list literal or assign from a literal first.",
                    )
                return self.annotate(expr, IntType())
            if isinstance(arg_t, StringType):
                self.ctx.uses_string = True
                return self.annotate(expr, IntType())
            self.error(
                "len() is only supported for lists or strings",
                expr,
                hint="Use len(list) or len(\"text\").",
            )

        # sum(list)
        if isinstance(expr.func, ast.Name) and expr.func.id == "sum":
            if len(arg_types) != 1:
                self.error(
                    "sum() expects a single list argument",
                    expr,
                    hint="Use sum(list_of_numbers).",
                )
            arg_t = arg_types[0]
            if not isinstance(arg_t, ListType) or not arg_t.element_type.is_numeric():
                self.error(
                    "sum() requires a list of numbers",
                    expr,
                    hint="Use a list of ints or floats.",
                )
            if arg_t.length is None:
                self.error(
                    "sum() requires a list with known length",
                    expr,
                    hint="Use a list literal or assign from a literal first.",
                )
            if isinstance(arg_t.element_type, FloatType):
                self.ctx.uses_sum_float = True
                return self.annotate(expr, FloatType())
            self.ctx.uses_sum_int = True
            return self.annotate(expr, IntType())

        # round(x)
        if isinstance(expr.func, ast.Name) and expr.func.id == "round":
            if len(arg_types) != 1 or not arg_types[0].is_numeric():
                self.error(
                    "round() expects a single numeric argument",
                    expr,
                    hint="Use round(<int|float>).",
                )
            if isinstance(arg_types[0], FloatType):
                self.ctx.uses_math = True
                return self.annotate(expr, FloatType())
            return self.annotate(expr, IntType())

        # str(x)
        if isinstance(expr.func, ast.Name) and expr.func.id == "str":
            if len(arg_types) != 1:
                self.error(
                    "str() expects a single argument",
                    expr,
                    hint="Use str(int|float|bool|string).",
                )
            arg_t = arg_types[0]
            if isinstance(arg_t, StringType):
                return self.annotate(expr, StringType())
            if isinstance(arg_t, BoolType):
                return self.annotate(expr, StringType())
            if isinstance(arg_t, FloatType):
                self.ctx.uses_str_float = True
                return self.annotate(expr, StringType())
            if isinstance(arg_t, IntType):
                self.ctx.uses_str_int = True
                return self.annotate(expr, StringType())
            self.error(
                "str() only supports int, float, bool, or string",
                expr,
                hint="Use str on basic scalar types.",
            )

        # math.sqrt(x)
        if isinstance(expr.func, ast.Attribute):
            if (
                isinstance(expr.func.value, ast.Name)
                and expr.func.value.id == "math"
                and expr.func.attr == "sqrt"
            ):
                self.ctx.uses_math = True
                return self.annotate(expr, FloatType())
            if (
                isinstance(expr.func.value, ast.Name)
                and expr.func.value.id == "math"
                and expr.func.attr in {"sin", "cos", "tan", "floor", "ceil", "log", "exp"}
            ):
                if len(arg_types) != 1 or not arg_types[0].is_numeric():
                    self.error(
                        f"math.{expr.func.attr}() expects one numeric argument",
                        expr,
                        hint="Use a numeric input for math functions.",
                    )
                self.ctx.uses_math = True
                return self.annotate(expr, FloatType())

        # print(...) returns nothing usable
        if isinstance(expr.func, ast.Name) and expr.func.id == "print":
            return self.annotate(expr, UnknownType())

        if isinstance(expr.func, ast.Name):
            func_name = expr.func.id
            self._record_function_call(func_name, arg_types)
            func_type = self.ctx.functions.get(func_name, None)
            if func_type:
                return self.annotate(expr, func_type.return_type)
        return self.annotate(expr, UnknownType())

    def _resolve_return_type(self, node: ast.FunctionDef) -> Type:
        if not self.return_types:
            return UnknownType()
        first = self.return_types[0]
        for t in self.return_types[1:]:
            if t != first:
                self.error(
                    "Function returns must be type-stable",
                    node,
                    hint="Make all return paths return the same type.",
                )
        return first

    def _unify_types(self, existing: Type, new: Type) -> Type:
        if isinstance(existing, UnknownType):
            return new
        if isinstance(new, UnknownType):
            return existing
        if existing == new:
            return existing
        if (isinstance(existing, IntType) and isinstance(new, FloatType)) or (
            isinstance(existing, FloatType) and isinstance(new, IntType)
        ):
            return FloatType()
        if isinstance(existing, StringType) or isinstance(new, StringType):
            return UnknownType()
        if isinstance(existing, ListType) and isinstance(new, ListType):
            element = self._unify_types(existing.element_type, new.element_type)
            length = existing.length if existing.length == new.length else None
            return ListType(element, length=length)
        return UnknownType()

    def _record_function_call(self, func_name: str, arg_types: List[Type]) -> None:
        func_def = self.function_defs.get(func_name)
        if not func_def or len(func_def.args.args) != len(arg_types):
            return

        current = self.function_param_hints.get(
            func_name, [UnknownType() for _ in arg_types]
        )
        merged = [
            self._unify_types(old, new) for old, new in zip(current, arg_types)
        ]
        self.function_param_hints[func_name] = merged

    def _collect_assignments(self, stmts: List[ast.stmt]) -> (set, Dict[str, ast.AST]):
        assigned: set = set()
        first: Dict[str, ast.AST] = {}

        for stmt in stmts:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Assign):
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        name = target.id
                        assigned.add(name)
                        first.setdefault(name, node)
        return assigned, first


def infer_types(tree: ast.AST, filename: str, lines: List[str]) -> TypeContext:
    inferencer = TypeInferencer(filename, lines)
    return inferencer.infer(tree)
