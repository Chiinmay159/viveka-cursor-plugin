---
name: viveka-execute
description: Governed execution with bounded loop-backs, inter-agent contracts, sub-agent verification, live review, time and cost bounds, and resumable state.
---

# Execute

Plan the roadmap, delegate under contract, build within architecture, review live, stay bounded.

## Execution Roadmap
- List components from Architecture's sequence.
- Assign each: direct implementation, sub-agent, tool invocation, or user action.
- Identify critical path and parallelizable work.
- Set checkpoints for verification before continuing.
- Set wall-clock and cost budgets at the roadmap level (see Time-Bounded Execution).

## Delegation Protocol

**Delegate when:** independent domains, parallel exploration useful, research would flood context, specialist review improves reliability.

**Do not delegate when:** task is small, context already loaded, tightly sequential, startup cost exceeds work.

**Inter-agent contract.** Every delegation is a contract. State all of:
- *Scope:* one sentence on what the sub-agent is and is not doing.
- *Architecture slice:* the relevant essence, foundation, and constraints from the parent's Architecture.
- *Success criteria:* what makes the sub-agent's output acceptable.
- *Output format:* structured summary schema (done, succeeded, failed, unresolved, evidence-pointers).
- *Escalation rules:* what to do on ambiguity, on failure, on cost overrun.
- *Bounds:* max recursive depth, max wall-clock, max token budget.

Without all six, do not delegate. Sub-agents return structured summaries, not raw output. Route by capability — heavier reasoning to stronger models, lookups to faster ones. Each sub-agent inherits the full framework and re-enters Context for its own scope.

**Sub-agent verification gate.** A summary is a claim, not a fact. For any sub-agent output that affects irreversible action, spot-check the summary against a sample of the underlying artifact before integrating. The summary is the highest manipulation surface in the framework — gate it.

## Live Review

A live-review agent runs concurrent with execution, scoped to the Architecture spec. It does not produce work; it watches it.

- *Context:* separate from the executing agent's context.
- *Scope:* the Architecture (essence, foundation, scope, sequence) — nothing else.
- *Triggers:* essence-drift, scope-creep, complexity growth beyond plan, foundation compromise for convenience.
- *Output:* recommendations, not commands. The executing agent decides whether to act on them.
- *Escalation:* if the executing agent ignores three consecutive recommendations from the live reviewer, the live reviewer escalates to the user (interactive) or to the log (autonomous).

## Conflict Resolution

When sub-agents conflict: stop the conflicting work, surface the divergence, resolve against architecture (essence and foundation are tiebreakers). If architecture does not resolve it, the conflict reveals an ambiguity — return to Architecture.

## Loop-Back Triggers

- **→ Architecture:** scope wrong, components misordered, foundation invalid, dependency missed.
- **→ Grasping:** approach failing, value equation changed, better approach apparent.
- **→ Context:** environment different than assumed, new constraints, user need changed.

Stop. Name what changed. Re-enter. Resume only after upstream correction.

**Bounded depth.** Hard cap: three loop-backs to upstream stages within one task. If the same stage is re-entered with the same trigger twice, escalate immediately rather than try a third time. On hitting the cap, force a structural break — declare the thrash, halt the run, and present (interactive) or queue (autonomous). Unbounded loop-backs are how the framework fails silently.

## Time-Bounded Execution

Every roadmap declares wall-clock and cost ceilings before execution begins. Three primitives:

- *Max wall-clock:* if the task exceeds it, halt and present current state.
- *Max sub-agent depth:* recursive delegation cannot exceed this depth (default 3). Prevents stack-style runaway.
- *Max token budget:* see Cost as Signal in CLAUDE.md cross-cutting. At 70% consumed, narrow scope. At 90%, terminate and queue.

Kill switches are not failures — they are the framework refusing to spend more than the work is worth.

## Resumability

Long-running tasks may be interrupted. Specify a checkpoint after each completed component:

```
checkpoint:
  task_id: <stable>
  current_stage: <stage name>
  last_completed_component: <name>
  open_loop_backs: [<list>]
  frozen_decisions: [<list>]
  pending_actions: [<list>]
  artifacts: [<paths>]
```

Write to `.viveka/checkpoints/<task_id>.yaml` after each major checkpoint. On resume: read the checkpoint, re-enter Context (the world may have moved), then resume at `current_stage` with `last_completed_component` as the anchor.

## Execution Discipline

- Only modify what the task requires. Clean diffs.
- No speculative abstractions or hypothetical scaffolding.
- State assumptions explicitly.
- Define success criteria before implementation.
- Make the confidence level visible when delivering pattern-matched content the user will act on.
- If you cannot verify through reasoning alone, use a tool.
- If plan breaks, stop and re-plan. Do not push through failure.
