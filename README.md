# Phoenix

[![PyPI](https://img.shields.io/pypi/v/phoenix-lang-cli)](https://pypi.org/project/phoenix-lang-cli/)

Phoenix is a statically verified, Python-like language that compiles to optimized C.

Write Python-style code. Get native performance.

```
Python (CPython):   ~0.52s
Phoenix → gcc -O3: ~0.01s   ← 50–100× faster on numeric workloads
```

Phoenix is not a faster Python runtime — it eliminates the interpreter entirely.

---

## Install

```bash
pip install phoenix-lang-cli
```

Requires: Python 3.9+, `gcc` (or `clang`) on your PATH.

---

## Quickstart

```bash
# write a .py file that follows Phoenix rules, then:
phoenix myfile.py          # check + compile + run
phoenix check myfile.py    # analysis only (no gcc needed)
phoenix build myfile.py    # force recompile
phoenix --version
```

Phoenix caches binaries in `.phoenix_cache/` keyed by source hash — repeat runs are instant.

---

## Example

### Phoenix code

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

## Why Phoenix instead of NumPy / Cython / PyPy?

| Tool | What it does | Limitation |
|---|---|---|
| NumPy | Fast array math | Requires vectorizable code, Python overhead for loops |
| Cython | Compiles annotated Python to C | Requires type annotations, complex build setup |
| PyPy | JIT-compiled Python | Still Python semantics, unpredictable warmup |
| **Phoenix** | Statically verified subset → native binary | Restricted language; no classes, no stdlib |

Phoenix's advantage: **zero interpreter overhead, provably at compile time.** If the program passes Phoenix's rules, the generated C is as fast as hand-written C.

---

## How it works

Phoenix enforces a **zero-ambiguity** execution model:

> If performance cannot be proven at compile time, the program is rejected.

The pipeline:

1. Parse Python source into AST
2. Verify zero-ambiguity rules (type stability, loop bounds, no dynamic code)
3. Generate deterministic C
4. Compile with `gcc -O3`
5. Execute native binary

---

## Language Rules

Phoenix enforces at compile time:

1. Variables may not change type
2. Lists must contain a single element type
3. No `eval`, `exec`, reflection, or dynamic imports
4. `for` uses `range(n)`, a list, or a dict; `while` requires a counter with a static bound and monotonic step
5. Function return types are consistent
6. Logical ops and comparisons require bool/numeric operands
7. List indexing is bounds-checked (statically when possible, runtime otherwise)

---

## Supported Constructs

- **Types:** `int`, `float`, `bool`, `str`, homogeneous lists, dicts, sets
- **Control flow:** `for` over `range()`, lists, dynamic lists, and dicts; bounded `while`; `if`/`elif`/`else`
- **Functions:** positional parameters with inferred types; type-stable returns
- **Builtins:** `print`, `int`, `abs`, `min`, `max`, `pow`, `len`, `sum`, `str`, `round`, `math.*`
- **Strings:** `+` concat, `.upper()`, `.lower()`, `.strip()`, `.startswith()`, `.endswith()`, `.find()`, `.replace()`
- **Lists:** fixed-length literals, dynamic lists (`append`/`pop`), slicing, iteration
- **Dicts/Sets:** literals, read/write, `del`, `add`/`remove`, key iteration (`for k in d`)
- **Modules:** local `import module`, `import math`

---

## Feature Matrix

| Feature | Static-Proofed | Runtime-Checked |
| --- | --- | --- |
| Type stability | ✅ | — |
| Homogeneous containers | ✅ | — |
| For-loop bounds | ✅ (range/known-length) | — |
| While termination | ✅ (strict counter pattern) | — |
| List indexing | ✅ (literal index + known length) | ✅ (dynamic) |
| Dynamic lists (append/pop/slice/iterate) | — | ✅ |
| Dict/Set lookup | — | ✅ (missing key) |
| Dict key iteration (`for k in d`) | ✅ (type match) | ✅ (iteration) |
| Set membership (`in`/`not in`) | ✅ (type match) | ✅ (lookup) |

---

## Status

Phoenix is a working prototype focused on provability over breadth:

- **Missing:** `from`-imports/aliasing, classes/objects, file I/O, broader stdlib
- **Next:** `from module import x`, classes, richer error recovery, stronger static bounds proofs

Contributions welcome. See the [PyPI page](https://pypi.org/project/phoenix-lang-cli/) to install the latest release.
