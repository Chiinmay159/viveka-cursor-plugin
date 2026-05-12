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

## Memory Taxonomy
Tag entries with:
- `project`
- `domain`
- `stage-of-failure`
- `severity`
- `supersedes-id` (when replacing a prior rule)

Correction rules may supersede older rules; always keep supersession chain explicit.

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

## Memory Hygiene
- Archive stale rules (project sunset, abandoned domain, contradicted by evidence).
- Record archive reason and date.
- Run periodic catalogue consolidation to merge duplicates and remove drift.

## Framework-Memory Promotion
When the same correction pattern appears across multiple tasks with consistent evidence:
- Promote it to framework-level candidate rule.
- Threshold policy: require repeated evidence across independent tasks before promotion.

Store promoted candidates in:
- `.viveka/framework-memory/`
- Versioned markdown entries with provenance links to source task memories.

## Supervised Promotion Pipeline (Tier 8, Phase A)
Use supervised promotion only; do not auto-modify framework files.

1. Detect repeated pattern across independent tasks.
2. Write candidate to `.viveka/framework-memory/candidates/`.
3. Run contradiction check against existing framework rules.
4. Attach evidence bundle:
   - source task memory links
   - failure mode prevented
   - expected trade-offs
5. Propose merge with rollback plan.
6. Require explicit human approval before framework merge.

Recommended threshold:
- At least 3 independent task confirmations before proposing merge.

## What Not to Catalogue
Routine operations with no insights. Speculative conclusions. Cataloguing for its own sake — every entry must earn its place.
