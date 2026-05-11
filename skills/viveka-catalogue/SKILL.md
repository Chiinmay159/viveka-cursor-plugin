---
name: viveka-catalogue
description: Persistent learning and task memory. Use after any significant task to capture insights, patterns, bugs, loop-backs, and correction rules. Writes to .viveka/memory/ as markdown files that future sessions can find and read.
---

# Catalogue

Capture what this interaction revealed. Persist it for future sessions.

## What to Capture

**Key insights:** What was learned about the domain, user's patterns, or environment?

**Unique patterns:** Unusual combinations that worked. Approaches that seemed right but failed — and why. Constraints that emerged during execution.

**Bugs and causes:** Specific bugs from specific actions. Which stage failed — Context (misread), Grasping (wrong evaluation), Architecture (structural flaw), Execution (implementation), or Review (missed defect)?

**Loop-back records:** Where did execution return to an earlier stage? What triggered it? What was wrong? How resolved? These are the highest-value learnings.

**Correction rules:** After any correction, formulate a specific prevention rule.
- Bad: "Be more careful with auth code."
- Good: "Token refresh must invalidate the old token within the same database transaction as new token creation."

## Task Memory Format

```markdown
# Task Memory: [task name]
Date: [date]
Environment: [platform, tools, tech stack]

## Essence
[One sentence]

## Key Decisions
- [Decision and why]

## Insights
- [What was learned]

## Bugs and Fixes
- [Bug]: [cause] → [fix] → [prevention rule]

## Loop-Backs
- [Stage]: [what wrong] → [trigger] → [resolution]

## Rules Generated
- [Specific prevention rule]
```

## Where to Write
- `.viveka/memory/` in the project root
- Name: `YYYY-MM-DD-task-name.md`

## Reading Previous Catalogues
At the start of new tasks, search `.viveka/memory/` for relevant past files. Read correction rules first — most actionable. Do not load all past catalogues — search by relevance.

## What Not to Catalogue
Routine operations with no insights. Speculative conclusions. Cataloguing for its own sake — every entry must earn its place.
