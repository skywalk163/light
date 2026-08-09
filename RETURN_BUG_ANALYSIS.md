# -*- coding: utf-8 -*-
"""
Debug Report: SyntaxError: 'return' outside function

Environment: G:\dumategithub\light (光明/Light programming language)
Date: 2026-07-05

================================================================================
1. BUG REPRODUCTION
================================================================================

Running `light run hello.light` with src backend produces:
    SyntaxError: 'return' outside function

The error line number shifts based on the generated code, but consistently
points to a `return` statement at module level.

Confirmed with minimal reproduction (test_return_bug.py):

    source = '定义甲等于3。\n返回甲。'
    → generates: "甲 = 3" (module level)
                 "return 甲"  (module level ← SyntaxError!)

================================================================================
2. ROOT CAUSE
================================================================================

The parser (`src/parser_stmt.py`) correctly accepts `返回` as a statement
everywhere — including at module level — which is valid Light syntax (a script
may return a value for the REPL or the caller).

The problem is that the Python code generator (`src/code_generator.py`) blindly
translates every `ReturnStmt` AST node into a Python `return` statement,
regardless of whether it is inside a function body or at module level.

In Python, `return` outside a function is a SyntaxError.

┌──────────────────────────────────────────────────────────────────────────────┐
│  Light AST: Module                              Python: invalid                 │
│  ├── VarDecl(甲 = 3)                         甲 = 3                            │
│  └── ReturnStmt(value=甲)   → generator →    return 甲   ← SyntaxError!       │
│                                                ^^^^^^^^^                     │
└──────────────────────────────────────────────────────────────────────────────┘

Affected files:
    • src/code_generator.py            (primary — used by `light run`)
    • src/code_generator_unified.py    (secondary — used by antlr backend)

================================================================================
3. AFFECTED CODE
================================================================================

src/code_generator.py  lines 37–66  (__init__)
    No tracking of whether we're inside a function/paragraph or method.

src/code_generator.py  lines 577–613  (_generate_paragraph)
    Generates `def name(...):` and body, but does NOT set any flag.

src/code_generator.py  lines 615–621  (_generate_return_stmt)
    Unconditionally emits `return`:
        def _generate_return_stmt(self, stmt: ReturnStmt):
            if stmt.value:
                value = self._generate_expr(stmt.value)
                self._add_line(f"return {value}")
            else:
                self._add_line("return")

src/code_generator.py  lines 699–790  (_generate_class_definition)
    Generates methods inside class, but does NOT tell the generator that a
    method body is a function context.

The same pattern exists in `code_generator_unified.py`.

================================================================================
4. WHY THE FIX SHOULD BE IN THE CODE GENERATOR (NOT THE PARSER)
================================================================================

Option A — Parser fix (reject module-level `返回`):
    ❌  Wrong semantics. Light supports module-level return for REPL and scripts.
    ❌  Would break legitimate use-cases (e.g. interactive `返回 42`).

Option B — Semantic analyser fix (reject module-level `返回`):
    ❌  Same issue — module-level return is valid in Light semantics.

Option C — Code generator fix (track function context, emit `return` correctly):
    ✅  Correct approach. Preserves Light semantics.
    ✅  Python `return` inside functions, module-level becomes a no-op or
        expression evaluation.

================================================================================
5. RECOMMENDED FIX
================================================================================

Add a `_in_function` context flag to `PythonCodeGenerator`.

A. In __init__ (around line 63):
    Add:  self._in_function = False

B. In _generate_paragraph (around line 604):
    Add:  self._in_function = True   before body generation
    Add:  self._in_function = False  after body generation

C. In _generate_class_definition / _generate_method (around line 759):
    Add:  self._in_function = True   before method body generation
    Add:  self._in_function = False  after body generation

D. In _generate_return_stmt (around line 615):
    Wrap the generated `return` in a conditional:

        def _generate_return_stmt(self, stmt: ReturnStmt):
            if self._in_function:
                if stmt.value:
                    value = self._generate_expr(stmt.value)
                    self._add_line(f"return {value}")
                else:
                    self._add_line("return")
            else:
                # Module-level return: evaluate the value as an expression
                # (for REPL / script semantics) but do not emit Python `return`
                if stmt.value:
                    value = self._generate_expr(stmt.value)
                    self._add_line(f"_light_result = {value}")

E. Same fix should be applied to `code_generator_unified.py`.

================================================================================
6. FILES TO MODIFY
================================================================================

Priority 1 (main backend used by CLI):
    src/code_generator.py
    — _generate_return_stmt    (add _in_function guard)
    — __init__                 (add _in_function flag)
    — _generate_paragraph      (set flag around body)
    — _generate_class_definition / _generate_method (set flag around body)

Priority 2 (antlr unified backend):
    src/code_generator_unified.py
    — Same pattern as above

================================================================================
7. VERIFICATION
================================================================================

After fix, the reproduction script should produce:

    TEST 1: Module-level return
    → Generated code: "甲 = 3" (line N)
                      "_light_result = 甲"  (line N+1)   ← no SyntaxError
    → exec(): SUCCESS

    TEST 2: Return inside paragraph
    → Generated code: "def 计算(甲, 乙):"
                      "    return (甲 + 乙)"           ← still works
    → exec(): SUCCESS

    TEST 3: Return inside class method
    → Generated code: "class 计算器:"
                      "    def 计算(self, 甲, 乙):"
                      "        return (甲 + 乙)"        ← still works
    → exec(): SUCCESS

================================================================================
8. ADDITIONAL NOTES
================================================================================

• The `_light_result` variable in the module-level case is harmless; it allows
  a REPL or wrapper to capture the implicit "last value" if desired.
• If stricter behaviour is wanted, the module-level return value could also
  be emitted as a bare expression (e.g. just `甲` on its own line) — but that
  risks side effects in Python (tuples without assignment print nothing).
  Using `_light_result = 甲` is the safest compromise.
• Empty `返回。` at module level should become a no-op (nothing emitted).
