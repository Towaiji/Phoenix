# Phoenix

Phoenix is a statically verified, Python-like language that compiles to optimized C.

It enforces a **zero-ambiguity** execution model: if performance cannot be proven at compile time, the program is rejected.

Phoenix is not a faster Python runtime.  
Phoenix eliminates Python entirely.

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
4. Loop bounds must be statically known
5. Array accesses and mutations are statically verified

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

## Architecture Overview

Phoenix pipeline:

1. Parse Python source into AST
2. Statistically verify zero-ambiguity rules
3. Generate deterministic C code
4. Compile with `gcc -O3`
5. Execute native binary

---

## Status

Phoenix currently supports:
- integers
- lists of integers
- static `for` loops
- arithmetic expressions
- array reads and writes

Future work includes:
- functions
- explicit print semantics
- richer expression support
