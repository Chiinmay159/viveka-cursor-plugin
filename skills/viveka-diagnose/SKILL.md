---
name: viveka-diagnose
description: Debugging and root-cause analysis. Use when there is an observed problem and the goal is to find its cause. Hypothesis-driven with eliminative testing.
---

# Diagnose

Find the cause of an observed problem. The output is a confirmed root cause plus a recommended fix.

## Before Diagnosing

- **Reproduce.** A bug you cannot reproduce is a bug you cannot reliably fix. If you can reproduce it, do — even if it takes effort.
- **Define the symptom precisely.** "Slow" is not a symptom. "P95 latency on /search > 800ms when payload exceeds 4KB" is.
- **Establish what changed.** Most bugs cluster around recent changes. What changed in code, data, infrastructure, or environment recently?

## Evidence Gathering

Cast wide before narrowing.

- *Symptoms.* What is observed? What is not observed but expected?
- *Logs and traces.* Read them. Do not skim.
- *Recent diffs.* Code changes, config changes, schema changes, dependency updates.
- *Environment.* Where does the problem happen? Where does it not? Differences are clues.
- *History.* Has this happened before? Search `.viveka/memory/` and `.viveka/framework-memory/` for patterns.

Do not theorise before evidence. Premature theory anchors you to wrong hypotheses.

## Hypothesis Generation

Generate multiple structurally different hypotheses. One hypothesis is anchoring; three or four is investigation.

- *Each hypothesis must be testable* — it predicts something observable.
- *Each hypothesis must be falsifiable* — there is a test that would rule it out.
- *Cover the layers* — code, data, config, infrastructure, external dependency, user error. Bugs hide where you do not look.

## Eliminative Testing

Rule out, do not just rule in. Confirming a hypothesis is weaker evidence than ruling out alternatives.

- *Cheapest test first.* Run the test that disqualifies the most hypotheses for the least effort.
- *One variable at a time.* Changing two things and seeing the bug disappear tells you nothing.
- *Document what you ruled out.* The negative results matter — they prevent re-testing later and become Catalogue input.

## Confirmation, Not Correlation

A correlation is not a cause. Before declaring root cause:

- *Mechanism.* Can you explain why the cause produces the symptom?
- *Reproduction control.* Does removing the cause make the symptom disappear, reliably?
- *Re-introduction control.* Does re-introducing the cause make the symptom return?

Without all three, you have a strong correlation, not a root cause. Mark it as such.

## Recommended Fix

State:

- *The cause,* in mechanistic terms.
- *The fix,* surgical to the cause — not to nearby code.
- *Why this fix and not others.* Often there are multiple candidate fixes; name the trade-offs.
- *Verification primitive for the fix.* What test, when run, proves the fix works?
- *Prevention rule.* What rule, added to `.viveka/memory/` or framework-memory, prevents this class of bug?

## Verification Primitives

- *Reproduce after fix.* The original reproduction must no longer reproduce.
- *Regression scan.* Did the fix break anything else?
- *Mechanism-level verification.* If the cause was X, the fix should remove the X-shaped failure mode entirely, not just hide its current symptom.
- *Negative result check.* The hypotheses you ruled out should still test as ruled out.

## When to Loop Back

- → Grasp if evidence reveals the original symptom framing was wrong.
- → Context if the bug is in a layer you did not have visibility into (database, infrastructure, external service).
- Bounded loop-back applies — three hypothesis cycles maximum before escalating.

## Catalogue After Diagnosing

A diagnosed bug is high-value memory. Always Catalogue:

- The symptom, the root cause, the fix.
- The hypotheses you ruled out.
- A correction rule (prevention, not "be careful").

If the same correction rule appears across N task memories, it becomes a candidate for framework-memory promotion. Diagnose is one of the highest-yield Catalogue inputs.
