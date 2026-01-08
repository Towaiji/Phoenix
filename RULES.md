Phoenix v0 Rules

1. Variables may not change type.
2. Lists must contain only one type.
3. No eval, exec, reflection, or dynamic imports.
4. `for` must use `range(<int literal>)`; `while` is forbidden.
5. Function return type must be consistent.
6. Logical ops (`and`, `or`, `not`) and comparisons (incl. chained) need bool/numeric operands and return bool.
7. `if` conditions must be bool; every branch assigns the same vars (elif/nested `if` allowed).

Phoenix v1 Rules

1. Keep type stability: variables and returns stay consistent across all control-flow paths.
2. Containers stay homogeneous.
3. No dynamic code loading.
4. Loops need clear termination:
   - for over finite ranges or sequences with known bounds
   - while allowed only if:
     - the condition compares a loop counter to an integer literal
     - the counter is initialized before the loop
     - the counter is updated exactly once per iteration
     - the update is monotonic and moves toward the literal bound
     - no other code mutates the counter
5. Complex logic is allowed only if all types, shapes, and termination can be statically proven at compile time.
6. Transpilation is explicit (optional):
   - phoenix check file.py runs analysis only
   - phoenix build file.py always transpiles to C and compiles
   - phoenix file.py behaves as today (analyze then build/run)
7. Logical ops and comparisons (incl. chained) require bool/numeric operands and yield bool for predictable transpilation.
8. Phoenix prioritizes provability over expressiveness; any feature that blocks static reasoning is intentionally excluded.