---
name: viveka-code
description: Code-specific execution discipline. Use when the output is source code. Covers surgical precision, simplicity, assumption surfacing, correctness, and code review protocols.
---

# Code

## Before Writing
- Define success criteria. What must be true? Write or identify the test first.
- Check existing patterns in the codebase. Follow its conventions.
- Identify the change boundary. What files will and will not be touched.

## While Writing
- **Surgical:** only modify what the task requires. Clean diffs. No unrelated refactors, renames, or reformats outside scope.
- **Simple:** no speculative abstractions, factory patterns, or scaffolding for needs that do not exist today. If 200 lines can be 50 without losing correctness, rewrite.
- **Explicit:** state every choice the user did not specify — language version, framework, architecture pattern, error strategy.
- **Correct:** handle error paths. Consider null/empty/boundary cases. Timing-safe comparisons for security. Validate at boundaries.
- **Clear names:** describe purpose, not implementation. Functions do one thing.

## After Writing
- Run it. Run existing tests. Run new tests.
- Verify success criteria from "Before Writing" are met.
- Verify no files outside change boundary were modified.

## Code Review (when reviewing, not writing)
Delegate categories to separate agents for large codebases:
- **Security:** input validation, injection, secret exposure, timing safety.
- **Correctness:** edge cases, error handling, race conditions.
- **Health:** dead code, unused imports, redundant logic, speculative abstractions.
- **Consistency:** naming, formatting, patterns matching rest of codebase.
