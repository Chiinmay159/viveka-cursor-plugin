---
name: viveka-review
description: Three-level output examination plus sufficiency threshold and autonomous-acceptance protocol. Use before delivering any significant output.
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

## Sufficiency Threshold

Stop reviewing when all three are true:

1. The essence is honoured.
2. No irreversible flaws remain.
3. The marginal cost of further improvement exceeds the marginal value to the user.

Stop even if the output could be healthier. Reversible flaws below the sufficiency threshold are not blockers — note them and ship. Without this threshold, Review sprawls and the framework consumes more value than it adds.

## Verification

Never mark complete without proving it works. Demonstrate correctness through evidence, not assertion. Verification primitives are mode-specific — see the relevant skill (viveka-code, viveka-writing, viveka-design, viveka-research) for what counts as evidence in that mode.

## Autonomous-Acceptance Protocol

When no human will check the output before it is acted on, Review itself becomes the acceptance test. Two extra requirements apply:

- *Frozen success criteria.* Self-review against the explicit success criteria from the task brief — not against a re-derived standard. Re-deriving criteria mid-review is how autonomous agents drift.
- *Queue on failure.* Anything that fails the criteria is queued for human review with explicit reason, current state, and recommended next action. Do not ship a failing output autonomously to "save the user time."

In autonomous mode, the audit trail and the queued failures are the user's interface to the run.

## Decision

- **Passes sufficiency:** deliver, note minor items.
- **Reversible flaws above threshold:** fix what you can, present judgment calls to user (interactive) or apply policy (autonomous).
- **Irreversible failures:** do not deliver. Fix, flag, explain what remains unresolved.
- **Coherence fails:** name the drift. Return to the stage where drift began (subject to the bounded loop-back cap).
