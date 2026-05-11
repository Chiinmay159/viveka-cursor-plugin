---
name: viveka-execute
description: Governed execution with delegation, live review, and conflict resolution. Use for compound tasks — multi-file changes, sub-agent delegation, long-running builds, or tasks where drift risk is high. Includes loop-back triggers and execution discipline.
---

# Execute

Plan the roadmap, delegate, build within architecture, review live.

## Execution Roadmap
- List components from Architecture's sequence.
- Assign each: direct implementation, sub-agent, tool invocation, or user action.
- Identify critical path and parallelizable work.
- Set checkpoints for verification before continuing.

## Delegation Protocol
**Delegate when:** independent domains, parallel exploration useful, research would flood context, specialist review improves reliability.
**Do not delegate when:** task is small, context already loaded, tightly sequential, startup cost exceeds work.

**Discipline:**
- One clear task per sub-agent with architecture slice, success criteria, and scope.
- Sub-agents return structured summaries: done, succeeded, failed, unresolved. Not raw output.
- Route by capability: heavy reasoning → stronger models, lookups → faster ones.
- Each sub-agent inherits the full framework. Recursive — re-enters Context for its own scope.

## Live Review
One agent watches continuously:
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

## Execution Discipline
- Only modify what the task requires. Clean diffs.
- No speculative abstractions or hypothetical scaffolding.
- State assumptions explicitly.
- Define success criteria before implementation.
- If plan breaks, stop and re-plan. Do not push through failure.
