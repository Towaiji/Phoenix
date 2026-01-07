import ast
from typing import List

from phoenix.errors import PhoenixError
from phoenix.type_inference import TypeContext, infer_types

BANNED_CALLS = {"eval", "exec", "__import__"}
BANNED_ATTRS = {("importlib", "import_module")}


def _error(msg: str, node: ast.AST, filename: str, lines: List[str]) -> PhoenixError:
    return PhoenixError(
        msg,
        lineno=node.lineno,
        col=node.col_offset + 1,
        source=lines[node.lineno - 1],
        filename=filename,
    )


def _check_control_flow(tree: ast.AST, filename: str, lines: List[str]) -> None:
    def _is_int_literal(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, int)

    def _extract_compare(test: ast.AST, node: ast.AST) -> (str, str):
        if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
            raise _error(
                "while condition must compare a loop counter to an integer literal.",
                node,
                filename,
                lines,
            )

        op = test.ops[0]
        if not isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            raise _error(
                "while condition must use <, <=, >, or >=.",
                node,
                filename,
                lines,
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
                )
            step = stmt.value.value
            if step == 0:
                raise _error(
                    "while counter update must use a non-zero integer literal step.",
                    node,
                    filename,
                    lines,
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

    def _check_for(node: ast.For) -> None:
        if not isinstance(node.iter, ast.Call):
            raise _error(
                "For-loop iterable must be a statically known range().",
                node,
                filename,
                lines,
            )

        if not isinstance(node.iter.func, ast.Name) or node.iter.func.id != "range":
            raise _error(
                "For-loops must use range() with static bounds.",
                node,
                filename,
                lines,
            )

        for arg in node.iter.args:
            if not _is_int_literal(arg):
                raise _error(
                    "range() bounds must be integer literals.",
                    node,
                    filename,
                    lines,
                )

    def _check_while(node: ast.While, assigned: set) -> None:
        counter, direction = _extract_compare(node.test, node)
        if counter not in assigned:
            raise _error(
                "while counter must be initialized before the loop.",
                node,
                filename,
                lines,
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
                )

        if len(updates) != 1:
            raise _error(
                "while counter must be updated exactly once per iteration.",
                node,
                filename,
                lines,
            )

        step = updates[0]
        if step == 0:
            raise _error(
                "while counter update must use a non-zero integer literal step.",
                node,
                filename,
                lines,
            )
        if direction == "up" and step <= 0:
            raise _error(
                "while counter must increase toward the bound.",
                node,
                filename,
                lines,
            )
        if direction == "down" and step >= 0:
            raise _error(
                "while counter must decrease toward the bound.",
                node,
                filename,
                lines,
            )

    def _collect_assigned(stmts: List[ast.stmt]) -> set:
        names: set = set()
        for stmt in stmts:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.target, ast.Name):
                    names.add(stmt.target.id)
        return names

    def _check_block(stmts: List[ast.stmt], assigned: set) -> None:
        for stmt in stmts:
            if isinstance(stmt, ast.FunctionDef):
                func_assigned = {arg.arg for arg in stmt.args.args}
                _check_block(stmt.body, func_assigned)
                continue

            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)
                continue

            if isinstance(stmt, ast.AugAssign):
                if isinstance(stmt.target, ast.Name):
                    assigned.add(stmt.target.id)
                continue

            if isinstance(stmt, ast.For):
                _check_for(stmt)
                if isinstance(stmt.target, ast.Name):
                    assigned.add(stmt.target.id)
                _check_block(stmt.body, set(assigned))
                continue

            if isinstance(stmt, ast.While):
                _check_while(stmt, assigned)
                _check_block(stmt.body, set(assigned))
                continue

            if isinstance(stmt, ast.If):
                _check_block(stmt.body, set(assigned))
                _check_block(stmt.orelse, set(assigned))
                if stmt.orelse:
                    body_assigned = _collect_assigned(stmt.body)
                    else_assigned = _collect_assigned(stmt.orelse)
                    assigned.update(body_assigned & else_assigned)
                continue

    _check_block(tree.body, set())


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
                    )


def check_types(tree: ast.AST, filename: str, lines: List[str]) -> TypeContext:
    _check_control_flow(tree, filename, lines)
    _check_dynamic_features(tree, filename, lines)
    # Inference enforces type stability and homogeneous aggregates.
    return infer_types(tree, filename, lines)
