# Phoenix

Phoenix is a statically verified, Python-like language that compiles to optimized C.

It enforces a **zero-ambiguity** execution model: if performance cannot be proven at compile time, the program is rejected.

Phoenix is not a faster Python runtime.  
Phoenix eliminates Python entirely.

---

## Quickstart

```bash
python3 -m phoenix.cli examples/good_big.py   # emits output.c and ./output
./output                                      # run the native binary

# optional CLI:
# python3 -m phoenix.cli check examples/foo.py   # analysis only
# python3 -m phoenix.cli build examples/foo.py   # force transpile + compile
# python3 -m phoenix.cli examples/foo.py         # default: analyze then build/run
```

Phoenix caches binaries in `.phoenix_cache/` keyed by source hash, so repeat builds are instant.

---

## Why Phoenix

Python is easy to write but slow to execute due to:
- dynamic typing
- runtime dispatch
- interpreter overhead

Phoenix takes a different approach:

> Restrict the language so performance can be *proven* before execution.

If the code passes Phoenix’s rules, it is compiled to native machine code via C and `gcc -O3`.

---

## Language Guarantees

Phoenix enforces the following at compile time:

1. Variables may not change type
2. Lists must contain a single element type
3. No `eval`, `exec`, reflection, or dynamic imports
4. `for` uses `range(<int literal/const>)` or lists with known length (non-zero step); `while` requires a counter compared to an int literal and a monotonic literal step
5. Function returns are type-stable
6. Logical ops (`and`, `or`, `not`) and comparisons (incl. chained) need bool/numeric operands and yield bool
7. List indexing is bounds-checked (static when possible, runtime otherwise)

If any rule is violated, compilation fails with a precise error message.

---

## Example

### Valid Phoenix code

```python
values = [1, 4, 9, 16]
total = 0

for i in range(4):
    total = total + values[i]
```

### Generated C

```c
int values[4] = {1, 4, 9, 16};
int total = 0;

for (int i = 0; i < 4; i++) {
    total = total + values[i];
}

printf("%d\n", total);
```

---

## Benchmarks

Summing integers in nested loops.

### Python (CPython 3.x)

```
Time: ~0.52 seconds
```

### Phoenix → C (gcc -O3)

```
Time: ~0.01 seconds
```

Phoenix achieves **50–100× speedups** on numeric workloads by eliminating dynamic overhead entirely.

---

## Language Rules (v0)

1. Variables may not change type.
2. Lists must contain one static element type.
3. No `eval`, `exec`, reflection, or dynamic imports.
4. `for` must be `range(<int literal/const>)` or a list with known length; `while` must use a counter compared to an int literal with a monotonic literal step.
5. Function return type must be consistent.
6. Logical ops (`and`, `or`, `not`) and comparisons (incl. chained) need bool/numeric operands and return bool.
7. `if` conditions must be boolean; assignments must exist in all branches (elif/nested `if` allowed).

If any rule is violated, compilation fails with a precise error message.

---

## Supported Constructs (today)

- Types: `int`, `float`, `bool`, `string`, fixed-length homogeneous list literals.
- Control flow: `for` over `range(<int literal/const>)` or known-length lists, bounded `while`, `if`/`elif`/`else` with nesting, logical `and`/`or`/`not`, comparisons (incl. chained), string concatenation via `+` (string + string/int/float), set membership via `in`.
- Functions: positional parameters with inferred types; returns must be type-stable.
- Builtins: `print`, `int(...)`, `abs`, `min`, `max`, `pow`, `len`, `sum`, `str`, `round`, `math.sqrt`, `math.sin`, `math.cos`, `math.tan`, `math.floor`, `math.ceil`, `math.log`, `math.exp`, `math.log10`, `math.asin`, `math.acos`, `math.atan`, `math.fabs`, `math.pow` (min/max also accept numeric lists; strings support `.upper()`, `.lower()`, `.strip()`).
- Lists: fixed-length literals and dynamic lists (via `append`/`pop`); slicing on dynamic lists with `list[a:b]` (no step).
- Dict/Set: dict and set literals with read-only access; dict keys must be `int`/`string`, set elements must be `int`/`string`.
- Codegen: C arrays for list literals; `printf` for output; `gcc -O3` compilation.

---

## Architecture Overview

Phoenix pipeline:

1. Parse Python source into AST
2. Statistically verify zero-ambiguity rules
3. Generate deterministic C code
4. Compile with `gcc -O3`
5. Execute native binary

---

## Status

Phoenix is a minimal prototype focused on safety over breadth:

- Missing: richer string utilities (beyond concat/len/str/upper/lower/strip), mutable dict/set operations, classes/objects, and broader stdlib coverage.
- Codegen is deliberately simple: flat arrays, no heap allocation, minimal header selection.

Future work: expand the safe subset (loop analyses, richer math/stdlib), improve diagnostics and error recovery, add stronger static checks (array bounds proofs, inter-file modules), support module-level constants, and explore a safer memory model for dynamic data while keeping zero-ambiguity guarantees.
