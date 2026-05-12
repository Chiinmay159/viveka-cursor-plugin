---
name: viveka-decide
description: Decision support without artifact production. Use for high-stakes choices with multiple valid paths, sensitivity analysis, and explicit "what would change this" framing.
---

# Decide

Produce a recommendation with reasons, not implementation.

## Inputs
- Decision question.
- Available options (or option generation request).
- Constraints and non-negotiables.
- Success criteria and risk tolerance.

## Method
1. Define decision objective in one sentence.
2. List options with assumptions.
3. Evaluate each using value equation:
   `(working value + scale potential) - (cost + risk + irreversibility)`.
4. Run sensitivity analysis:
   - Which assumption changes the ranking most?
   - Which uncertainty is decision-critical?
5. Run reversal check:
   - What is reversible now?
   - What becomes irreversible later?
6. State "what would change this recommendation."

## Output Format
- Recommendation.
- Why this option wins.
- Key risks and mitigations.
- Confidence level.
- Triggers for revisiting decision.
