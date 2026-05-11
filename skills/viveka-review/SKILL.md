---
name: viveka-review
description: Three-level output examination — health, bugs, and coherence. Use before delivering any significant output. Traces the journey from Context through Architecture to Execution and checks whether the output honors the essence.
---

# Review

Examine the completed output before delivery.

## Level 1 — Health
The output as an organism:
- **Excess:** anything present that does not earn its place? Redundancy, speculative code, padding?
- **Deficiency:** anything essential missing? Error handling, edge cases, documentation?
- **Imbalance:** is depth proportional? A utility function should not be more complex than core logic.
- **Leakage:** does information flow correctly? Secrets, internal state, implementation details exposed?

**Test:** If this output were a person or a machine, will it work healthily?

## Level 2 — Bugs
- Does it run without errors? Do tests pass?
- Edge cases: off-by-one, null references, race conditions, boundary values?
- Error paths handled, not just happy paths?
- Security: injection, timing leaks, exposed secrets?
- **Adversarial scenarios:** what inputs would break this? What would a hostile user do?
- **Kill cases:** what single failure makes this worthless or dangerous?

## Level 3 — Coherence
Trace the journey:
- Does the output honor the **essence** from Architecture?
- Does it respect the **scope**? Anything added that was excluded? Missing that was included?
- Did execution follow the architecture's **sequence**?
- Are foundation decisions intact or compromised for convenience?
- Do sub-agent outputs integrate cleanly?

**A technically correct output that drifted from the essence fails coherence even with zero bugs.**

## Verification
Never mark complete without proving it works. Run tests. Demonstrate correctness through evidence, not assertion.

## Decision
- **Passes:** deliver, note minor items.
- **Reversible flaws:** fix what you can, present judgment calls to user.
- **Irreversible failures:** do not deliver. Fix, flag, explain what remains unresolved.
- **Coherence fails:** name the drift. Return to the stage where drift began.
