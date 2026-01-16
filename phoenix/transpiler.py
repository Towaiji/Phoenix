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
    DictType,
    SetType,
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

    def _list_suffix(self, t: Type) -> str:
        if isinstance(t, IntType):
            return "int"
        if isinstance(t, FloatType):
            return "double"
        if isinstance(t, BoolType):
            return "bool"
        if isinstance(t, StringType):
            return "string"
        return "int"

    def _dict_key_suffix(self, t: Type) -> str:
        if isinstance(t, IntType):
            return "int"
        if isinstance(t, StringType):
            return "string"
        return "int"

    def _dict_val_suffix(self, t: Type) -> str:
        if isinstance(t, IntType):
            return "int"
        if isinstance(t, FloatType):
            return "double"
        if isinstance(t, BoolType):
            return "bool"
        if isinstance(t, StringType):
            return "string"
        if isinstance(t, ListType):
            return f"list_{self._list_suffix(t.element_type)}"
        return "int"

    def _dict_c_val(self, t: Type) -> str:
        if isinstance(t, StringType):
            return "const char *"
        if isinstance(t, BoolType):
            return "bool"
        if isinstance(t, ListType):
            return c_type_name(t)
        return c_type_name(t)

    def _set_elem_suffix(self, t: Type) -> str:
        if isinstance(t, IntType):
            return "int"
        if isinstance(t, StringType):
            return "string"
        return "int"

    def _list_c_elem(self, t: Type) -> str:
        if isinstance(t, BoolType):
            return "bool"
        if isinstance(t, StringType):
            return "const char *"
        return c_type_name(t)

    def emit(self, line: str = ""):
        self.lines.append("    " * self.indent + line)

    def emit_helpers(self):
        if self.type_ctx.uses_dyn_list_int:
            self._emit_dyn_list_helpers("int", "int")
        if self.type_ctx.uses_dyn_list_float:
            self._emit_dyn_list_helpers("double", "double")
        if self.type_ctx.uses_dyn_list_bool:
            self._emit_dyn_list_helpers("bool", "bool")
        if self.type_ctx.uses_dyn_list_string:
            self._emit_dyn_list_helpers("string", "const char *")
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

        if self.type_ctx.uses_str_upper:
            self.emit("const char *phoenix_str_upper(const char *s) {")
            self.indent += 1
            self.emit("static char buf[256];")
            self.emit("int i = 0;")
            self.emit("for (; s[i] != '\\0' && i < 255; i++) {")
            self.indent += 1
            self.emit("buf[i] = (char)toupper((unsigned char)s[i]);")
            self.indent -= 1
            self.emit("}")
            self.emit("buf[i] = '\\0';")
            self.emit("return buf;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_str_lower:
            self.emit("const char *phoenix_str_lower(const char *s) {")
            self.indent += 1
            self.emit("static char buf[256];")
            self.emit("int i = 0;")
            self.emit("for (; s[i] != '\\0' && i < 255; i++) {")
            self.indent += 1
            self.emit("buf[i] = (char)tolower((unsigned char)s[i]);")
            self.indent -= 1
            self.emit("}")
            self.emit("buf[i] = '\\0';")
            self.emit("return buf;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_str_strip:
            self.emit("const char *phoenix_str_strip(const char *s) {")
            self.indent += 1
            self.emit("static char buf[256];")
            self.emit("const char *start = s;")
            self.emit("while (*start && isspace((unsigned char)*start)) {")
            self.indent += 1
            self.emit("start++;")
            self.indent -= 1
            self.emit("}")
            self.emit("const char *end = start + strlen(start);")
            self.emit("while (end > start && isspace((unsigned char)*(end - 1))) {")
            self.indent += 1
            self.emit("end--;")
            self.indent -= 1
            self.emit("}")
            self.emit("int len = (int)(end - start);")
            self.emit("if (len > 255) len = 255;")
            self.emit("memcpy(buf, start, (size_t)len);")
            self.emit("buf[len] = '\\0';")
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

        for key_t, val_t in sorted(self.type_ctx.dict_types, key=lambda x: (repr(x[0]), repr(x[1]))):
            self._emit_dict_helpers(key_t, val_t)

        for elem_t in sorted(self.type_ctx.set_types, key=lambda x: repr(x)):
            self._emit_set_helpers(elem_t)

    def _emit_dyn_list_helpers(self, suffix: str, c_elem: str) -> None:
        struct_name = f"PhoenixList{suffix.capitalize()}"
        self.emit(f"typedef struct {{")
        self.indent += 1
        self.emit("int len;")
        self.emit("int cap;")
        self.emit(f"{c_elem} *data;")
        self.indent -= 1
        self.emit(f"}} {struct_name};")
        self.emit()

        self.emit(f"void phoenix_list_{suffix}_append({struct_name} *list, {c_elem} value) {{")
        self.indent += 1
        self.emit("if (list->len >= list->cap) {")
        self.indent += 1
        self.emit("int new_cap = list->cap ? list->cap * 2 : 4;")
        self.emit(f"list->data = ({c_elem} *)realloc(list->data, sizeof({c_elem}) * new_cap);")
        self.emit("list->cap = new_cap;")
        self.indent -= 1
        self.emit("}")
        self.emit("list->data[list->len++] = value;")
        self.indent -= 1
        self.emit("}")
        self.emit()

        self.emit(f"{c_elem} phoenix_list_{suffix}_pop({struct_name} *list) {{")
        self.indent += 1
        self.emit("if (list->len <= 0) {")
        self.indent += 1
        self.emit('fprintf(stderr, "PhoenixError: pop from empty list\\n");')
        self.emit("exit(1);")
        self.indent -= 1
        self.emit("}")
        self.emit("list->len -= 1;")
        self.emit("return list->data[list->len];")
        self.indent -= 1
        self.emit("}")
        self.emit()

        self.emit(f"{struct_name} phoenix_list_{suffix}_slice({struct_name} *list, int start, int end) {{")
        self.indent += 1
        self.emit("if (start < 0 || end < 0 || start > end || end > list->len) {")
        self.indent += 1
        self.emit('fprintf(stderr, "PhoenixError: invalid slice bounds\\n");')
        self.emit("exit(1);")
        self.indent -= 1
        self.emit("}")
        self.emit(f"{struct_name} out;")
        self.emit("out.len = end - start;")
        self.emit("out.cap = out.len;")
        self.emit(f"out.data = ({c_elem} *)malloc(sizeof({c_elem}) * out.cap);")
        self.emit("for (int i = 0; i < out.len; i++) {")
        self.indent += 1
        self.emit("out.data[i] = list->data[start + i];")
        self.indent -= 1
        self.emit("}")
        self.emit("return out;")
        self.indent -= 1
        self.emit("}")
        self.emit()

        if self.type_ctx.uses_str_upper:
            self.emit("const char *phoenix_str_upper(const char *s) {")
            self.indent += 1
            self.emit("static char buf[256];")
            self.emit("int i = 0;")
            self.emit("for (; s[i] != '\\0' && i < 255; i++) {")
            self.indent += 1
            self.emit("buf[i] = (char)toupper((unsigned char)s[i]);")
            self.indent -= 1
            self.emit("}")
            self.emit("buf[i] = '\\0';")
            self.emit("return buf;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_str_lower:
            self.emit("const char *phoenix_str_lower(const char *s) {")
            self.indent += 1
            self.emit("static char buf[256];")
            self.emit("int i = 0;")
            self.emit("for (; s[i] != '\\0' && i < 255; i++) {")
            self.indent += 1
            self.emit("buf[i] = (char)tolower((unsigned char)s[i]);")
            self.indent -= 1
            self.emit("}")
            self.emit("buf[i] = '\\0';")
            self.emit("return buf;")
            self.indent -= 1
            self.emit("}")
            self.emit()

        if self.type_ctx.uses_str_strip:
            self.emit("const char *phoenix_str_strip(const char *s) {")
            self.indent += 1
            self.emit("static char buf[256];")
            self.emit("const char *start = s;")
            self.emit("while (*start && isspace((unsigned char)*start)) {")
            self.indent += 1
            self.emit("start++;")
            self.indent -= 1
            self.emit("}")
            self.emit("const char *end = start + strlen(start);")
            self.emit("while (end > start && isspace((unsigned char)*(end - 1))) {")
            self.indent += 1
            self.emit("end--;")
            self.indent -= 1
            self.emit("}")
            self.emit("int len = (int)(end - start);")
            self.emit("if (len > 255) len = 255;")
            self.emit("memcpy(buf, start, (size_t)len);")
            self.emit("buf[len] = '\\0';")
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

        for key_t, val_t in sorted(self.type_ctx.dict_types, key=lambda x: (repr(x[0]), repr(x[1]))):
            self._emit_dict_helpers(key_t, val_t)

        for elem_t in sorted(self.type_ctx.set_types, key=lambda x: repr(x)):
            self._emit_set_helpers(elem_t)

    def _emit_dict_helpers(self, key_t: Type, val_t: Type) -> None:
        key_suffix = self._dict_key_suffix(key_t)
        val_suffix = self._dict_val_suffix(val_t)
        key_c = "int" if isinstance(key_t, IntType) else "const char *"
        val_c = self._dict_c_val(val_t)
        struct_name = c_type_name(DictType(key_t, val_t))
        self.emit(f"typedef struct {{")
        self.indent += 1
        self.emit("int len;")
        self.emit(f"{key_c} *keys;")
        self.emit(f"{val_c} *values;")
        self.indent -= 1
        self.emit(f"}} {struct_name};")
        self.emit()

        func_name = f"phoenix_dict_{key_suffix}_{val_suffix}_get"
        self.emit(f"{val_c} {func_name}({struct_name} *dict, {key_c} key) {{")
        self.indent += 1
        self.emit("for (int i = 0; i < dict->len; i++) {")
        self.indent += 1
        if isinstance(key_t, StringType):
            self.emit("if (strcmp(dict->keys[i], key) == 0) {")
        else:
            self.emit("if (dict->keys[i] == key) {")
        self.indent += 1
        self.emit("return dict->values[i];")
        self.indent -= 1
        self.emit("}")
        self.indent -= 1
        self.emit("}")
        self.emit('fprintf(stderr, "PhoenixError: key not found in dict\\n");')
        self.emit("exit(1);")
        self.indent -= 1
        self.emit("}")
        self.emit()

    def _emit_set_helpers(self, elem_t: Type) -> None:
        elem_suffix = self._set_elem_suffix(elem_t)
        elem_c = "int" if isinstance(elem_t, IntType) else "const char *"
        struct_name = c_type_name(SetType(elem_t))
        self.emit("typedef struct {")
        self.indent += 1
        self.emit("int len;")
        self.emit(f"{elem_c} *data;")
        self.indent -= 1
        self.emit(f"}} {struct_name};")
        self.emit()

        func_name = f"phoenix_set_{elem_suffix}_contains"
        self.emit(f"bool {func_name}({struct_name} *set, {elem_c} value) {{")
        self.indent += 1
        self.emit("for (int i = 0; i < set->len; i++) {")
        self.indent += 1
        if isinstance(elem_t, StringType):
            self.emit("if (strcmp(set->data[i], value) == 0) {")
        else:
            self.emit("if (set->data[i] == value) {")
        self.indent += 1
        self.emit("return true;")
        self.indent -= 1
        self.emit("}")
        self.indent -= 1
        self.emit("}")
        self.emit("return false;")
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

            if isinstance(value, ast.List) and isinstance(t, ListType) and t.length is not None:
                elems = [self.expr(e) for e in value.elts]
                size = t.length if t.length is not None else len(elems)
                init = ", ".join(elems)
                self.emit(f"{c_type} {name}[{size}] = {{{init}}};")
                self.declared.add(name)
                return

            if isinstance(value, ast.List) and isinstance(t, ListType) and t.length is None:
                elems = [self.expr(e) for e in value.elts]
                size = len(elems)
                if is_new:
                    self.emit(f"{c_type} {name};")
                    self.declared.add(name)
                self.emit(f"{name}.len = {size};")
                self.emit(f"{name}.cap = {size};")
                elem_c = self._list_c_elem(t.element_type)
                self.emit(f"{name}.data = ({elem_c} *)malloc(sizeof({elem_c}) * {size});")
                for idx, elem in enumerate(elems):
                    self.emit(f"{name}.data[{idx}] = {elem};")
                return

            if isinstance(value, ast.Dict) and isinstance(t, DictType):
                self.emit_dict_assign(name, value, t, is_new)
                return

            if isinstance(value, ast.Set) and isinstance(t, SetType):
                self.emit_set_assign(name, value, t, is_new)
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

    def emit_dict_assign(self, name: str, value: ast.Dict, t: DictType, is_new: bool) -> None:
        key_t = t.key_type
        val_t = t.value_type
        key_c = "int" if isinstance(key_t, IntType) else "const char *"
        val_c = self._dict_c_val(val_t)
        size = len(value.keys)
        if is_new:
            self.emit(f"{c_type_name(t)} {name};")
            self.declared.add(name)
        self.emit(f"{name}.len = {size};")
        self.emit(f"{name}.keys = ({key_c} *)malloc(sizeof({key_c}) * {size});")
        self.emit(f"{name}.values = ({val_c} *)malloc(sizeof({val_c}) * {size});")

        for idx, (k, v) in enumerate(zip(value.keys, value.values)):
            key_expr = self.expr(k)
            self.emit(f"{name}.keys[{idx}] = {key_expr};")
            if isinstance(val_t, ListType) and val_t.length is None and isinstance(v, ast.List):
                temp_name = f"__phoenix_dict_list{idx}_{name}"
                self._emit_dyn_list_literal(temp_name, val_t.element_type, v.elts)
                self.emit(f"{name}.values[{idx}] = {temp_name};")
            else:
                val_expr = self.expr(v)
                self.emit(f"{name}.values[{idx}] = {val_expr};")

    def emit_set_assign(self, name: str, value: ast.Set, t: SetType, is_new: bool) -> None:
        elem_t = t.element_type
        elem_c = "int" if isinstance(elem_t, IntType) else "const char *"
        size = len(value.elts)
        if is_new:
            self.emit(f"{c_type_name(t)} {name};")
            self.declared.add(name)
        self.emit(f"{name}.len = {size};")
        self.emit(f"{name}.data = ({elem_c} *)malloc(sizeof({elem_c}) * {size});")
        for idx, e in enumerate(value.elts):
            elem_expr = self.expr(e)
            self.emit(f"{name}.data[{idx}] = {elem_expr};")

    def _emit_dyn_list_literal(self, name: str, elem_t: Type, elems: List[ast.AST]) -> None:
        elem_c = self._list_c_elem(elem_t)
        size = len(elems)
        self.emit(f"{c_type_name(ListType(elem_t, length=None))} {name};")
        self.emit(f"{name}.len = {size};")
        self.emit(f"{name}.cap = {size};")
        self.emit(f"{name}.data = ({elem_c} *)malloc(sizeof({elem_c}) * {size});")
        for idx, elem in enumerate(elems):
            self.emit(f"{name}.data[{idx}] = {self.expr(elem)};")

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
            elif isinstance(call.func, ast.Attribute) and call.func.attr in {"append", "pop"}:
                expr = self.expr(call)
                self.emit(f"{expr};")

    def expr(self, node):
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "1" if node.value else "0"
            if isinstance(node.value, str):
                return json.dumps(node.value)
            return str(node.value)

        if isinstance(node, (ast.Dict, ast.Set)):
            raise Exception("Dict/set literals must be assigned to a variable first")

        if isinstance(node, ast.Subscript):
            arr = self.expr(node.value)
            slice_expr = node.slice.value if isinstance(node.slice, ast.Index) else node.slice
            list_type = self._type_of(node.value)
            if isinstance(slice_expr, ast.Slice):
                start = "0" if slice_expr.lower is None else self.expr(slice_expr.lower)
                end = None
                if slice_expr.upper is None:
                    if isinstance(list_type, ListType) and list_type.length is None:
                        end = f"{arr}.len"
                    else:
                        end = "0"
                else:
                    end = self.expr(slice_expr.upper)
                if isinstance(list_type, ListType) and list_type.length is None:
                    suffix = self._list_suffix(list_type.element_type)
                    return f"phoenix_list_{suffix}_slice(&{arr}, {start}, {end})"
            if isinstance(list_type, DictType):
                key_t = list_type.key_type
                val_t = list_type.value_type
                key_suffix = self._dict_key_suffix(key_t)
                val_suffix = self._dict_val_suffix(val_t)
                key_expr = self.expr(slice_expr)
                return f"phoenix_dict_{key_suffix}_{val_suffix}_get(&{arr}, {key_expr})"
            idx = self.expr(slice_expr)
            if isinstance(list_type, ListType) and list_type.length is None:
                return f"{arr}.data[phoenix_bounds_check({idx}, {arr}.len)]"
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
            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
                right_t = self._type_of(node.comparators[0])
                if isinstance(right_t, SetType):
                    elem_suffix = self._set_elem_suffix(right_t.element_type)
                    left = self.expr(node.left)
                    right = self.expr(node.comparators[0])
                    expr = f"phoenix_set_{elem_suffix}_contains(&{right}, {left})"
                    if isinstance(node.ops[0], ast.NotIn):
                        return f"!({expr})"
                    return expr
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
                if isinstance(arg_t, ListType):
                    if isinstance(arg, ast.List):
                        elem_c = c_type_name(arg_t.element_type)
                        elems = ", ".join(self.expr(e) for e in arg.elts)
                        list_expr = f"({elem_c}[]){{{elems}}}"
                        list_len = str(arg_t.length or len(arg.elts))
                    else:
                        list_expr = self.expr(arg)
                        list_len = f"{list_expr}.len" if arg_t.length is None else str(arg_t.length)
                    if isinstance(arg_t.element_type, FloatType):
                        fn = "phoenix_min_double_list" if node.func.id == "min" else "phoenix_max_double_list"
                    else:
                        fn = "phoenix_min_int_list" if node.func.id == "min" else "phoenix_max_int_list"
                    if isinstance(arg, ast.List):
                        return f"{fn}({list_expr}, {list_len})"
                    if arg_t.length is None:
                        return f"{fn}({list_expr}.data, {list_len})"
                    return f"{fn}({list_expr}, {list_len})"

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
                if isinstance(arg_t, ListType) and arg_t.length is None:
                    return f"{self.expr(arg)}.len"
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
                if isinstance(arg_t, ListType) and arg_t.length is None:
                    list_expr = self.expr(arg)
                    if isinstance(arg_t.element_type, FloatType):
                        return f"phoenix_sum_double({list_expr}.data, {list_expr}.len)"
                    return f"phoenix_sum_int({list_expr}.data, {list_expr}.len)"

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
                    and node.func.attr
                    in {
                        "sin",
                        "cos",
                        "tan",
                        "floor",
                        "ceil",
                        "log",
                        "exp",
                        "log10",
                        "asin",
                        "acos",
                        "atan",
                        "fabs",
                        "pow",
                    }
                ):
                    arg = self.expr(node.args[0])
                    if node.func.attr == "pow":
                        right = self.expr(node.args[1])
                        return f"pow({arg}, {right})"
                    return f"{node.func.attr}({arg})"
                if node.func.attr in {"upper", "lower", "strip"}:
                    target = self.expr(node.func.value)
                    if node.func.attr == "upper":
                        return f"phoenix_str_upper({target})"
                    if node.func.attr == "lower":
                        return f"phoenix_str_lower({target})"
                    return f"phoenix_str_strip({target})"
                if node.func.attr in {"append", "pop"}:
                    target = self.expr(node.func.value)
                    recv_t = self._type_of(node.func.value)
                    if isinstance(recv_t, ListType) and recv_t.length is None:
                        suffix = self._list_suffix(recv_t.element_type)
                        if node.func.attr == "append":
                            arg = self.expr(node.args[0])
                            return f"phoenix_list_{suffix}_append(&{target}, {arg})"
                        return f"phoenix_list_{suffix}_pop(&{target})"

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
    if type_ctx.uses_str_upper or type_ctx.uses_str_lower or type_ctx.uses_str_strip:
        headers.update({"<ctype.h>", "<string.h>", "<stdio.h>"})
    if type_ctx.uses_bounds_check:
        headers.update({"<stdio.h>", "<stdlib.h>"})
    if (
        type_ctx.uses_dyn_list_int
        or type_ctx.uses_dyn_list_float
        or type_ctx.uses_dyn_list_bool
        or type_ctx.uses_dyn_list_string
    ):
        headers.update({"<stdlib.h>", "<stdio.h>"})
    if type_ctx.dict_types or type_ctx.set_types:
        headers.update({"<stdlib.h>", "<stdio.h>", "<string.h>", "<stdbool.h>"})

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
