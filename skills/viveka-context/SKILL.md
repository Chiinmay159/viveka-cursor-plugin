---
name: viveka-context
description: Deep environment and situation mapping. Use for complex tasks with multiple environments, unclear constraints, unfamiliar codebase, or ambiguous user signals.
---

# Context

Map what is real before anything else.

## Natural Order
- What is my token budget? How much context window remains?
- What tools are loaded? What could be loaded but is not?
- What can I verify through tools vs. generate from training data?

## Time
- Is this task in planning, execution, or review phase?
- Is this the start of a conversation or deep into an ongoing project?
- Are there fatigue signals, deadlines, or urgency?
- Is this a fresh task or a resumption? If resumption, read `.viveka/checkpoints/<task_id>.yaml` first.

## Place
- What environment? Terminal, IDE, web chat, desktop app, mobile?
- What file system access? Version control state?
- What external services are connected?

## Tool and Connector Environment
The tool surface is part of the environment, not a constant. Map it explicitly.

- Which tools and connectors are loaded? Which are still connecting?
- What does each tool let you verify that you otherwise could not?
- Which tools have authentication state? Could it expire mid-task?
- Which tools' output schemas could drift between calls?
- Fallback rules: if tool X fails, what is plan B? If no plan B, surface that now.

Probe before relying. Before writing code that depends on a connector tool's response shape, call that tool once and look at the actual response — not the assumed shape.

## Entities
**Agent:** Known fully. Do not invent or understate capabilities. Identify which model is running. Declare the posture for this task — *standard* (default), *exploratory* (lateral generation, reduced verification), *speed* (compressed stages, deferred Catalogue), or *adversarial* (deepened Review, hostile-input simulation, paranoid sub-agent verification). If undeclared, default to standard. The posture's invariants (essence adherence, irreversible-action gate, review requirement) hold regardless.

**Human:** Known only through evidence. Is the prompt specific or vague? Does syntax suggest expertise or unfamiliarity? Is the request exploratory or directive? Assess through input quality, not claims. In autonomous mode, the human is absent during execution but present at acceptance — model both.

## Task
- What needs to be done? One sentence.
- In which environment, under which constraints, with which tools?
- What does success look like? (These criteria become frozen for Review.)
- *Type signature:* primarily code, research, document review, decision, diagnosis, conversation, or compound. Drives agent activation.
- *Scale signal:* trivial, standard, compound, or long-run. Drives agent activation thresholds.
- *Stakes signal:* low, standard, or high (security/legal/financial/regulatory/customer-facing irreversible). High stakes elevate to Adversarial posture and viveka-adversarial activation.
- *Activation candidate:* given type + scale + stakes + posture + operating mode, name the activation state — no agent / auto-deploy / ask first / user-requested. Apply session override memory (if a prior veto exists for this signature this session, suppress the proposal). See AGENT ACTIVATION in CLAUDE.md.

## Memory Read Protocol

Search `.viveka/memory/` and `.viveka/framework-memory/` before Grasping. Memory is not optional context — past corrections are the most actionable input you have.

- *Search order:* by relevance to current task (project, domain, stage involved).
- *Load order:* correction rules first (most actionable), then loop-back records (highest-value learnings), then insights.
- *Conflict resolution:* between sessions, recency wins for facts; severity wins for rules; framework-memory overrides task-memory.
- *Load budget:* memory should not flood Context. Cap at roughly 10% of available context window. If more is relevant, summarise rather than load whole.

Do not load all past catalogues. Search by relevance.

## Search Protocol
Before concluding: search memory, read codebase structure, check tools, look for existing patterns. Do not assume — look.

## Output
Structured understanding (held internally) that feeds Grasping via the Transition Protocol. If critical information is missing, ask one focused question. If the tool environment is unstable or memory conflicts are unresolved, surface that before proceeding.
