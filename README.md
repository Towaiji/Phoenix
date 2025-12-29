# Phoenix

Phoenix is a zero-ambiguity performance enforcer for Python.

Phoenix analyzes Python code and refuses to compile it unless the compiler can statically prove it can run fast. Code that is ambiguous, dynamic, or unpredictable is rejected with clear, actionable errors.

Phoenix is not a scripting language.
Phoenix is not a runtime optimizer.
Phoenix is a compiler tool that enforces performance discipline.

---

## Why Phoenix Exists

Python always runs code, even when its performance characteristics are unclear or harmful. This leads to:
- hidden bottlenecks
- unpredictable slowdowns
- rewriting hot paths in C or Rust after the fact

Phoenix flips the contract.

If code runs, it must be fast.
If it cannot be proven fast, it does not run.

---

## Core Philosophy

- Python-like syntax for readability
- No runtime guessing or specialization
- No dynamic fallbacks
- Performance is mandatory, not best-effort
- Ambiguity is a compile-time error

---

## What Phoenix Does

1. Parses restricted Python syntax
2. Performs strict static analysis
3. Either:
   - rejects the code with performance errors, or
   - approves it for compilation
4. Approved code can be transpiled to optimized C and compiled with gcc -O3

---

## What Phoenix Rejects

- Variable type mutation
- Mixed-type containers
- Reflection, eval, exec
- Dynamic imports
- Runtime code generation
- Unbounded or unpredictable loops

---

## Supported Code (v0 Scope)

- Integers and floats
- Arithmetic
- For and while loops
- Functions with deterministic return types
- Homogeneous lists and arrays

---

## Example

Invalid code:
```python
x = 5
x = "hello"
```

Phoenix output:
```
❌ PhoenixError: Variable 'x' changed type (int → str).
Performance cannot be proven.
```

Valid code:
```python
def sum(n: int) -> int:
    s = 0
    for i in range(n):
        s += i
    return s
```

---

## Usage

phoenix check example.py
phoenix build example.py

---

## Status

Phoenix is an experimental engineering project focused on enforcing performance discipline at compile time.
