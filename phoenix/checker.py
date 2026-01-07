import ast
from typing import List

from phoenix.errors import PhoenixError
from phoenix.type_inference import TypeContext, infer_types

BANNED_CALLS = {"eval", "exec", "__import__"}
BANNED_ATTRS = {("importlib", "import_module")}


def _error(
    msg: str,
    node: ast.AST,
    filename: str,
    lines: List[str],
    hint: str | None = None,
) -> PhoenixError:
    return PhoenixError(
        msg,
        lineno=node.lineno,
        col=node.col_offset + 1,
        source=lines[node.lineno - 1],
        filename=filename,
        hint=hint,
    )


def _check_control_flow(tree: ast.AST, filename: str, lines: List[str]) -> None:
    def _is_int_literal(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, int)

    def _range_arg_value(node: ast.AST, const_ints: dict) -> int:
        if _is_int_literal(node):
            return node.value
        if isinstance(node, ast.Name) and node.id in const_ints:
            return const_ints[node.id]
        raise _error(
            "range() bounds must be integer literals or constants.",
            node,
            filename,
            lines,
            hint="Assign a literal first (e.g. `n = 10`) and use `range(n)`.",
        )

    def _extract_compare(test: ast.AST, node: ast.AST) -> (str, str):
        if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
            raise _error(
                "while condition must compare a loop counter to an integer literal.",
                node,
                filename,
                lines,
                hint="Use a simple bound like `while i < 10:`.",
            )

        op = test.ops[0]
        if not isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            raise _error(
                "while condition must use <, <=, >, or >=.",
                node,
                filename,
                lines,
                hint="Use a strict inequality against the literal bound.",
            )

        left = test.left
        right = test.comparators[0]

        if isinstance(left, ast.Name) and _is_int_literal(right):
            counter = left.id
            counter_on_left = True
        elif isinstance(right, ast.Name) and _is_int_literal(left):
            counter = right.id
            counter_on_left = False
        else:
            raise _error(
                "while condition must compare a loop counter to an integer literal.",
                node,
                filename,
                lines,
                hint="Make the counter a variable and the bound a literal.",
            )

        if isinstance(op, (ast.Lt, ast.LtE)):
            direction = "up" if counter_on_left else "down"
        else:
            direction = "down" if counter_on_left else "up"

        return counter, direction

    def _parse_update(stmt: ast.stmt, counter: str, node: ast.AST) -> int:
        if isinstance(stmt, ast.AugAssign):
            if not isinstance(stmt.target, ast.Name) or stmt.target.id != counter:
                return 0
            if not _is_int_literal(stmt.value):
                raise _error(
                    "while counter update must use an integer literal step.",
                    node,
                    filename,
                    lines,
                    hint="Use a literal step like `i += 1`.",
                )
            step = stmt.value.value
            if step == 0:
                raise _error(
                    "while counter update must use a non-zero integer literal step.",
                    node,
                    filename,
                    lines,
                    hint="Use a non-zero literal step like `i += 1`.",
                )
            if isinstance(stmt.op, ast.Add):
                return step
            if isinstance(stmt.op, ast.Sub):
                return -step
            raise _error(
                "while counter update must add or subtract an integer literal.",
                node,
                filename,
                lines,
                hint="Use `i += 1` or `i = i + 1`.",
            )

        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                return 0
            if stmt.targets[0].id != counter:
                return 0
            if not isinstance(stmt.value, ast.BinOp):
                raise _error(
                    "while counter update must be counter +/- <int literal>.",
                    node,
                    filename,
                    lines,
                )
            binop = stmt.value
            left = binop.left
            right = binop.right
            if isinstance(left, ast.Name) and left.id == counter and _is_int_literal(right):
                step = right.value
                if step == 0:
                    raise _error(
                        "while counter update must use a non-zero integer literal step.",
                        node,
                        filename,
                        lines,
                        hint="Use a non-zero literal step like `i += 1`.",
                    )
                if isinstance(binop.op, ast.Add):
                    return step
                if isinstance(binop.op, ast.Sub):
                    return -step
            raise _error(
                "while counter update must be counter +/- <int literal>.",
                node,
                filename,
                lines,
                hint="Use `i = i + 1` or `i = i - 1`.",
            )

        return 0

    def _contains_counter_mutation(stmt: ast.stmt, counter: str) -> bool:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == counter:
                        return True
            if isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name) and node.target.id == counter:
                    return True
        return False

    def _check_for(node: ast.For, const_ints: dict, list_lengths: dict) -> None:
        if isinstance(node.iter, ast.Call):
            if not isinstance(node.iter.func, ast.Name) or node.iter.func.id != "range":
                raise _error(
                    "For-loops must use range() with static bounds.",
                    node,
                    filename,
                    lines,
                    hint="Use `range(...)` or a list with known length.",
                )

            if not (1 <= len(node.iter.args) <= 3):
                raise _error(
                    "range() must have 1 to 3 arguments.",
                    node,
                    filename,
                    lines,
                    hint="Use `range(stop)`, `range(start, stop)`, or `range(start, stop, step)`.",
                )

            for arg in node.iter.args:
                _range_arg_value(arg, const_ints)

            if len(node.iter.args) == 3:
                step = _range_arg_value(node.iter.args[2], const_ints)
                if step <= 0:
                    raise _error(
                        "range() step must be a positive integer literal or constant.",
                        node,
                        filename,
                        lines,
                        hint="Use a positive literal step like `range(0, 10, 1)`.",
                    )
            return

        if isinstance(node.iter, ast.List):
            return

        if isinstance(node.iter, ast.Name) and node.iter.id in list_lengths:
            return

        raise _error(
            "For-loop iterable must be range(...) or a list with known length.",
            node,
            filename,
            lines,
            hint="Use a list literal or a list assigned from a literal.",
        )

    def _check_while(node: ast.While, assigned: set) -> None:
        counter, direction = _extract_compare(node.test, node)
        if counter not in assigned:
            raise _error(
                "while counter must be initialized before the loop.",
                node,
                filename,
                lines,
                hint="Initialize the counter above the loop, e.g. `i = 0`.",
            )

        updates = []
        for stmt in node.body:
            step = _parse_update(stmt, counter, node)
            if step != 0:
                updates.append(step)
                continue
            if _contains_counter_mutation(stmt, counter):
                raise _error(
                    "while counter may only be updated once per iteration.",
                    node,
                    filename,
                    lines,
                    hint="Keep a single counter update in the loop body.",
                )

        if len(updates) != 1:
            raise _error(
                "while counter must be updated exactly once per iteration.",
                node,
                filename,
                lines,
                hint="Add one counter update, no more and no less.",
            )

        step = updates[0]
        if step == 0:
            raise _error(
                "while counter update must use a non-zero integer literal step.",
                node,
                filename,
                lines,
                hint="Use `i += 1` or `i = i + 1`.",
            )
        if direction == "up" and step <= 0:
            raise _error(
                "while counter must increase toward the bound.",
                node,
                filename,
                lines,
                hint="Use `i += 1` when the condition is `i < bound`.",
            )
        if direction == "down" and step >= 0:
            raise _error(
                "while counter must decrease toward the bound.",
                node,
                filename,
                lines,
                hint="Use `i -= 1` when the condition is `i > bound`.",
            )

    def _check_block(stmts: List[ast.stmt], assigned: set, const_ints: dict, list_lengths: dict) -> None:
        for stmt in stmts:
            if isinstance(stmt, ast.FunctionDef):
                func_assigned = {arg.arg for arg in stmt.args.args}
                _check_block(stmt.body, func_assigned, {}, {})
                continue

            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)
                        if _is_int_literal(stmt.value):
                            const_ints[target.id] = stmt.value.value
                            list_lengths.pop(target.id, None)
                        elif isinstance(stmt.value, ast.List):
                            list_lengths[target.id] = len(stmt.value.elts)
                            const_ints.pop(target.id, None)
                        else:
                            const_ints.pop(target.id, None)
                            list_lengths.pop(target.id, None)
                continue

            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.target, ast.Name):
                    assigned.add(stmt.target.id)
                    const_ints.pop(stmt.target.id, None)
                    list_lengths.pop(stmt.target.id, None)
                continue

            if isinstance(stmt, ast.For):
                _check_for(stmt, const_ints, list_lengths)
                if isinstance(stmt.target, ast.Name):
                    assigned.add(stmt.target.id)
                _check_block(stmt.body, set(assigned), dict(const_ints), dict(list_lengths))
                continue

            if isinstance(stmt, ast.While):
                _check_while(stmt, assigned)
                _check_block(stmt.body, set(assigned), dict(const_ints), dict(list_lengths))
                continue

            if isinstance(stmt, ast.If):
                body_assigned = set(assigned)
                else_assigned = set(assigned)
                body_consts = dict(const_ints)
                else_consts = dict(const_ints)
                body_lists = dict(list_lengths)
                else_lists = dict(list_lengths)
                _check_block(stmt.body, body_assigned, body_consts, body_lists)
                _check_block(stmt.orelse, else_assigned, else_consts, else_lists)
                if stmt.orelse:
                    assigned.update(body_assigned & else_assigned)
                    const_ints.clear()
                    for name in body_consts:
                        if name in else_consts and body_consts[name] == else_consts[name]:
                            const_ints[name] = body_consts[name]
                    list_lengths.clear()
                    for name in body_lists:
                        if name in else_lists and body_lists[name] == else_lists[name]:
                            list_lengths[name] = body_lists[name]
                continue

    _check_block(tree.body, set(), {}, {})


def _check_dynamic_features(tree: ast.AST, filename: str, lines: List[str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
                raise _error(
                    f"Use of '{node.func.id}' is forbidden. "
                    "Dynamic execution breaks performance guarantees.",
                    node,
                    filename,
                    lines,
                    hint="Remove dynamic execution and use static code instead.",
                )

            if isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and (node.func.value.id, node.func.attr) in BANNED_ATTRS
                ):
                    raise _error(
                        "Dynamic imports are forbidden. Performance cannot be proven.",
                        node,
                        filename,
                        lines,
                        hint="Use static imports at the top of the file.",
                    )


def check_types(tree: ast.AST, filename: str, lines: List[str]) -> TypeContext:
    _check_control_flow(tree, filename, lines)
    _check_dynamic_features(tree, filename, lines)
    # Inference enforces type stability and homogeneous aggregates.
    return infer_types(tree, filename, lines)
