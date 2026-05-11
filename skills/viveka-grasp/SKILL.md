---
name: viveka-grasp
description: Scenario evaluation and decision gate. Use when the task has multiple viable approaches, significant stakes, or when choosing between meaningfully different strategies. Evaluates by value equation and determines whether to proceed, present, or ask.
---

# Grasp

Understand the full situation before evaluating paths. Comprehension precedes deliberation.

## Comprehension First
Before evaluating options, confirm you understand:
- What is the actual problem — not the stated task, the underlying need?
- What has been tried before? (Search codebase, memory, history.)
- Which constraints are hard (violating fails the task) vs. soft (preferences)?
- What is the user's actual priority — speed, correctness, elegance, cost?

## Scenario Simulation
Generate 2-4 structurally different approaches. For each, evaluate:
- **Functionality:** Does it solve the problem completely or partially?
- **Demonstrated potential:** Does it create leverage for known adjacent needs? (Not hypothetical.)
- **Scale:** Point fix or systemic improvement?
- **Energy/time cost:** Tokens, tool calls, sub-agents, user review time.
- **Vulnerabilities:** Failure modes, blast radius.
- **Irreversibility:** Can it be undone? At what cost?

## Value Equation
(functionality + demonstrated potential + scale) − (energy + time + vulnerabilities + irreversibility)

When options score similarly, prefer: more reversible, faster to validate, simpler.

## Search Protocol
Search web, codebases, memory, skills for precedents and patterns. Do not evaluate from training data alone when live information is available.

## Decision Gate
**Proceed** when: clear task, reversible action, proportionate cost, obvious interpretation.
**Present approach** when: significant effort, direction could be wrong, irreversible, multiple valid paths.
**Ask** when: critical information missing, contradictions, undefined scope.
**Surface simpler path** when: a simpler approach solves 80%+ at 20% cost.

When multiple interpretations exist, state them and ask. Do not silently pick one.
