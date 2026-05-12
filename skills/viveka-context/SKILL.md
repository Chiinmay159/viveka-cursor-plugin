---
name: viveka-context
description: Deep environment and situation mapping. Use for complex tasks where quick context assessment is insufficient — multiple environments, unclear constraints, unfamiliar codebase, or ambiguous user signals. Maps natural order, time, place, entities, and task.
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

## Place
- What environment? Terminal, IDE, web chat, desktop app, mobile?
- What file system access? Version control state?
- What external services are connected?
- Which tools/connectors are loaded right now?
- What can each tool verify directly?
- If a tool fails or schema drifts, what is fallback behavior?

## Entities
**Agent:** Known fully. Do not invent or understate capabilities.
**Human:** Known only through evidence. Is the prompt specific or vague? Does syntax suggest expertise or unfamiliarity? Is the request exploratory or directive? Assess through input quality, not claims.

## Task
- What needs to be done? One sentence.
- In which environment, under which constraints, with which tools?
- What does success look like?

## Search Protocol
Before concluding: search memory, read codebase structure, check tools, look for existing patterns. Do not assume — look.

## Catalogue Read Protocol
When past memory exists:
- Query by task domain, failure mode, and stage.
- Read order: correction rules first, then loop-back records, then general notes.
- Conflict handling: recency wins for facts, severity wins for safety rules.
- Apply a load budget so memory does not flood current context.

## Output
Structured understanding (held internally) that feeds Grasping. If critical information is missing, ask one focused question.
