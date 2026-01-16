from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple

from phoenix.errors import PhoenixError


def annotate_source(tree: ast.AST, filename: str, lines: List[str]) -> None:
    for node in ast.walk(tree):
        node.phoenix_filename = filename
        node.phoenix_lines = lines


def _import_error(
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
        rule_id="R3",
    )


def _collect_module_globals(tree: ast.AST) -> Set[str]:
    names: Set[str] = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef):
            names.add(stmt.name)
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.add(stmt.target.id)
    return names


def _collect_function_locals(node: ast.FunctionDef) -> Set[str]:
    names: Set[str] = {arg.arg for arg in node.args.args}
    for stmt in node.body:
        for inner in ast.walk(stmt):
            if isinstance(inner, ast.Assign):
                for target in inner.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            if isinstance(inner, ast.AnnAssign) and isinstance(inner.target, ast.Name):
                names.add(inner.target.id)
            if isinstance(inner, ast.For) and isinstance(inner.target, ast.Name):
                names.add(inner.target.id)
    return names


class ModuleRenamer(ast.NodeTransformer):
    def __init__(self, globals_map: Set[str], prefix: str):
        self.globals_map = globals_map
        self.prefix = prefix
        self.local_stack: List[Set[str]] = []

    def _is_local(self, name: str) -> bool:
        return any(name in scope for scope in self.local_stack)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        if not self.local_stack and node.name in self.globals_map:
            node.name = f"{self.prefix}{node.name}"
        self.local_stack.append(_collect_function_locals(node))
        self.generic_visit(node)
        self.local_stack.pop()
        return node

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        if not self.local_stack:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in self.globals_map:
                    target.id = f"{self.prefix}{target.id}"
        self.generic_visit(node)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:
        if not self.local_stack and isinstance(node.target, ast.Name) and node.target.id in self.globals_map:
            node.target.id = f"{self.prefix}{node.target.id}"
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.globals_map and not self._is_local(node.id):
            node.id = f"{self.prefix}{node.id}"
        return node


class ModuleAttrRewriter(ast.NodeTransformer):
    def __init__(self, module_exports: Dict[str, Set[str]], errors: List[PhoenixError]):
        self.module_exports = module_exports
        self.errors = errors

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        if isinstance(node.value, ast.Name) and node.value.id in self.module_exports:
            module = node.value.id
            exports = self.module_exports[module]
            if node.attr not in exports:
                filename = getattr(node, "phoenix_filename", None)
                lines = getattr(node, "phoenix_lines", None)
                if filename and lines:
                    self.errors.append(
                        _import_error(
                            f"Module '{module}' has no attribute '{node.attr}'",
                            node,
                            filename,
                            lines,
                            hint="Check the module exports or spelling.",
                        )
                    )
                return node
            new_name = ast.Name(id=f"{module}__{node.attr}", ctx=node.ctx)
            return ast.copy_location(new_name, node)
        return self.generic_visit(node)


def resolve_imports(
    tree: ast.AST,
    filename: str,
    lines: List[str],
    base_dir: Path,
) -> Tuple[ast.AST, List[PhoenixError]]:
    errors: List[PhoenixError] = []
    module_exports: Dict[str, Set[str]] = {}
    module_defs: List[ast.stmt] = []
    new_body: List[ast.stmt] = []
    seen_modules: Set[str] = set()

    for stmt in tree.body:
        if isinstance(stmt, ast.ImportFrom):
            errors.append(
                _import_error(
                    "from-imports are not supported for local modules",
                    stmt,
                    filename,
                    lines,
                    hint="Use `import module` and access names as module.name.",
                )
            )
            continue

        if isinstance(stmt, ast.Import):
            keep_stmt = True
            for alias in stmt.names:
                name = alias.name
                if name == "math":
                    continue
                keep_stmt = False
                if alias.asname is not None:
                    errors.append(
                        _import_error(
                            "Import aliases are not supported for local modules",
                            stmt,
                            filename,
                            lines,
                            hint="Use `import module` without an alias.",
                        )
                    )
                    continue
                module_path = base_dir / f"{name}.py"
                if not module_path.exists():
                    errors.append(
                        _import_error(
                            f"Module '{name}' not found",
                            stmt,
                            filename,
                            lines,
                            hint="Ensure the module file exists next to the entry file.",
                        )
                    )
                    continue
                if name in seen_modules:
                    continue
                source = module_path.read_text()
                mod_lines = source.splitlines()
                mod_tree = ast.parse(source)
                annotate_source(mod_tree, str(module_path), mod_lines)
                for mod_stmt in mod_tree.body:
                    if isinstance(mod_stmt, ast.Import) and any(
                        alias.name != "math" for alias in mod_stmt.names
                    ):
                        errors.append(
                            _import_error(
                                "Local modules may only import math",
                                mod_stmt,
                                str(module_path),
                                mod_lines,
                                hint="Keep local modules self-contained or use math only.",
                            )
                        )
                globals_map = _collect_module_globals(mod_tree)
                module_exports[name] = globals_map
                prefix = f"{name}__"
                renamer = ModuleRenamer(globals_map, prefix)
                renamer.visit(mod_tree)
                module_defs.extend(mod_tree.body)
                seen_modules.add(name)
            if keep_stmt:
                new_body.append(stmt)
            continue

        new_body.append(stmt)

    tree.body = module_defs + new_body
    rewriter = ModuleAttrRewriter(module_exports, errors)
    rewriter.visit(tree)
    return tree, errors
