---
name: viveka-code
description: Code-specific execution discipline. Use when the output is source code. Covers surgical precision, simplicity, assumption surfacing, correctness, and verification primitives.
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

## Verification Primitives (After Writing)

Code is the most verifiable output mode. Use every primitive that applies.

- *Run it.* The single most important check. Failing to run is failing to verify.
- *Run existing tests.* Regression catches what review misses.
- *Run new tests.* Verify the success criteria from Before Writing.
- *Diff check.* Confirm no files outside the change boundary were modified.
- *Type check / lint.* Where the language supports it.
- *Adversarial scan.* For changes touching auth, input parsing, or external boundaries — apply Review's "what would a hostile user do?" frame.

Evidence, not assertion. "Tests pass" is not verification — "tests pass with output X" is.

## Code Review (when reviewing, not writing)
Delegate categories to separate agents for large codebases:
- **Security:** input validation, injection, secret exposure, timing safety.
- **Correctness:** edge cases, error handling, race conditions.
- **Health:** dead code, unused imports, redundant logic, speculative abstractions.
- **Consistency:** naming, formatting, patterns matching rest of codebase.

Each sub-reviewer runs under an inter-agent contract (see viveka-execute). Summaries are claims — spot-check against the artifact before integrating.
