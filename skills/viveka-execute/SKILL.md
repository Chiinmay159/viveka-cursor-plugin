---
name: viveka-execute
description: Governed execution with delegation, live review, and conflict resolution. Use for compound tasks — multi-file changes, sub-agent delegation, long-running builds, or tasks where drift risk is high. Includes loop-back triggers and execution discipline.
---

# Execute

Plan the roadmap, delegate, build within architecture, review live.

## Transition Protocol
Apply at every stage boundary.

- **Interactive mode:** declare findings, apply decision gate, pause for significant transitions, proceed silently for trivial ones.
- **Autonomous mode:** write findings to audit log, apply policy ("on ambiguity escalate; on irreversible action halt and queue; on trivial proceed"), and continue.

## Posture Protocol (Tier 7)
- Declare posture at task start: `standard`, `exploratory`, `speed`, or `adversarial`.
- Keep invariant controls active in every posture:
  - irreversible-action gate
  - minimum review requirement for irreversible outcomes
  - scope compliance
- Max one posture switch per task unless explicitly escalated with reason.
- On conflict between posture and safety controls, safety controls win and posture falls back to `standard`.

## Execution Roadmap
- List components from Architecture's sequence.
- Assign each: direct implementation, sub-agent, tool invocation, or user action.
- Identify critical path and parallelizable work.
- Set checkpoints for verification before continuing.

## Time and Depth Bounds
- Set max wall-clock budget for the task.
- Set max sub-agent depth.
- Set max recursive loop-back depth.
- On breach: escalate, checkpoint, or halt.

## Delegation Protocol
**Delegate when:** independent domains, parallel exploration useful, research would flood context, specialist review improves reliability.
**Do not delegate when:** task is small, context already loaded, tightly sequential, startup cost exceeds work.

**Discipline:**
- One clear task per sub-agent with architecture slice, success criteria, and scope.
- Sub-agents return structured summaries: done, succeeded, failed, unresolved. Not raw output.
- Route by capability: heavy reasoning → stronger models, lookups → faster ones.
- Each sub-agent inherits the full framework. Recursive — re-enters Context for its own scope.
- For outputs affecting irreversible actions, spot-check summary claims against source artifacts before integrating.

## Inter-Agent Contract Schema
Every delegation must include:
- Scope statement.
- Success criteria.
- Escalation rules.
- Output format.
- Max depth and max cost.
- Return schema: completed, evidence, unresolved, blocked.

## Live Review
Live reviewer is separate from execution thread, scoped to architecture spec, and returns recommendations (not commands). It interrupts on essence-drift or scope-creep.

Reviewer checks:
- Is output conforming to architecture spec?
- Is essence being honored?
- Is complexity growing beyond plan?
- Are Grasping assumptions still valid?

## Conflict Resolution
When sub-agents conflict: stop conflicting work, surface the divergence, resolve against architecture (essence and foundation are tiebreakers). If architecture does not resolve it, the conflict reveals an ambiguity — return to Architecture.

## Loop-Back Triggers
- **→ Architecture:** scope wrong, components misordered, foundation invalid, dependency missed.
- **→ Grasping:** approach failing, value equation changed, better approach apparent.
- **→ Context:** environment different than assumed, new constraints, user need changed.

Stop. Name what changed. Re-enter. Resume only after upstream correction.

## Bounded Loop-Back Protocol
- Max 3 loop-backs per task.
- If the same stage re-enters with the same trigger twice, flag thrash.
- On cap or thrash: stop execution, declare structural break, and escalate.

## Checkpoint and Resume
For long or interrupted tasks, checkpoint:
- Current stage.
- Last completed component.
- Open loop-backs.
- Frozen decisions and success criteria.
- Next safe resume step.

## Execution Discipline
- Only modify what the task requires. Clean diffs.
- No speculative abstractions or hypothetical scaffolding.
- State assumptions explicitly.
- Define success criteria before implementation.
- If plan breaks, stop and re-plan. Do not push through failure.
