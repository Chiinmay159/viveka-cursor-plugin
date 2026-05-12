---
name: viveka-catalogue
description: Persistent learning across sessions. Captures insights, loop-backs, and correction rules. Promotes recurrent rules from per-task memory to framework-memory.
---

# Catalogue

Capture what this interaction revealed. Persist it for future sessions. Promote what recurs.

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
---
id: <YYYY-MM-DD-task-slug>
project: <project name>
domain: <domain tag>
posture: standard | exploratory | speed | adversarial
posture_switches: [{from: standard, to: adversarial, reason: "..."}, ...]
operating_mode: interactive | autonomous
stages_entered: [Context, Grasping, ...]
stages_skipped: [...]
loop_backs: [{from: Execute, to: Architecture, trigger: "..."}, ...]
severity: low | medium | high
supersedes: [<id>, ...]    # optional — task memories this one replaces
---

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
- [Specific prevention rule with id]
```

## Where to Write
- `.viveka/memory/` in the project root.
- Filename: `YYYY-MM-DD-task-slug.md`.

## Memory Taxonomy

Every entry carries the frontmatter above. Tags enable Context's read protocol to load by relevance instead of by recency.

- *project / domain* — for filtering on read.
- *posture / posture_switches* — which posture the task ran under, plus any switches with reason. Filtering on this surfaces patterns specific to a posture (e.g., "speed posture tasks fail Review more often").
- *operating_mode* — interactive or autonomous. Important for promoting rules later — autonomous-mode failures often differ from interactive ones.
- *stages_entered / stages_skipped* — the audit trail (mandatory in autonomous mode).
- *loop_backs* — structured so they can be counted and pattern-matched across tasks.
- *severity* — drives ordering on read; high severity surfaces first.
- *supersedes* — when a new task memory replaces an older one (better understanding, contradicted facts), name the predecessors. Older ones get archived.

## Memory Hygiene

Memory rots without maintenance.

- *Retire:* mark entries archived when the project sunsets, the domain is abandoned, or evidence contradicts the rule. Move to `.viveka/memory/archive/` with a one-line reason. Do not delete — past mistakes have evidentiary value.
- *Consolidate:* periodically (every ~20 task memories, or when conflicts surface), run a consolidation pass. Merge duplicates, resolve conflicts, prune stale rules.
- *Audit:* if the same correction rule appears across N (default 3) task memories with consistent evidence, it is a candidate for framework-memory promotion (see below).

## Framework-Memory Promotion (Phase A — supervised)

Per-task memory is local. Framework-memory is universal. Promotion is how the framework itself learns. Phase A enforces **supervised promotion**: the pipeline detects, the human approves, the framework merges. Auto-promotion (Phase B) is deferred and not active.

**Promotion criteria.** A correction rule is a candidate for promotion only when all four hold:
1. It has appeared in at least N task memories (default N=3; raised to N=5 if it conflicts with an existing active rule).
2. The evidence across those memories is consistent — same root cause, same fix, no contradicting cases.
3. The rule is general — not project- or domain-specific. Project-specific rules stay in task-memory.
4. It does not contradict an active framework-memory rule, OR it does and explicitly proposes which active rule to retire.

**Promotion pipeline (no step past Stage 1 is automatic).**

*Stage 1 — Candidate generation.* The consolidation pass identifies patterns across task memories and writes a candidate file to `.viveka/framework-memory/candidates/<candidate-id>.md` with full provenance.

*Stage 2 — Contradiction check.* Every candidate is checked against active framework-memory rules. If a contradiction exists, the candidate is marked `status: contradicting`, the conflicting active rule is named, and the candidate cannot advance until the human resolves the conflict (decides which rule retires, which is kept). Contradicting candidates never auto-merge under any condition.

*Stage 3 — Review queue.* Non-contradicting candidates and resolved-contradiction candidates enter the review queue at `.viveka/framework-memory/queue/`. The queue is the human's interface to framework evolution.

*Stage 4 — Human approval.* The human reviews each candidate against its evidence, contradiction state, and proposed scope. Approval is explicit and per-rule; no batch approval, no timeouts that auto-approve, no policy that approves on the human's behalf.

*Stage 5 — Merge.* Approved candidates are merged to `.viveka/framework-memory/active/<rule-id>.md` with full provenance, version id, rollback id, and expiry date. The framework loads the new rule on the next Context read.

**Framework-memory format (active rules).**

```markdown
---
id: fm-<slug>
version: <semver: 1.0.0, 1.1.0, ...>
status: candidate | contradicting | queued | active | retired | rolled-back
promoted_from: [<task-memory-id>, ...]
promoted_on: <date>
approved_by: <human id or policy id>
supersedes: [<fm-id@version>, ...]
rolls_back_to: <fm-id@version | null>
expires_on: <date — default promoted_on + 6 months>
revalidation_history: [{date: <>, outcome: revalidated | retired | refined, note: "..."}, ...]
contradiction_resolution: <id of retired rule | null>
---

# Framework Rule: [name]

## Rule
[One sentence — actionable, not aspirational.]

## Evidence
- [Task memory id]: [what happened, what the rule prevents]

## Scope
[When this rule applies. When it does not.]

## Rollback Path
[Specific instructions for restoring the previous version if this rule causes regression. If first version, state: "No rollback target — disabling rule restores baseline framework behaviour."]
```

**Versioning.** Promoted rules use semver. First promotion is `1.0.0`. Refinements that preserve scope and direction are minor bumps (`1.1.0`). Refinements that change scope or direction are major bumps (`2.0.0`) and require fresh approval as if a new candidate. Rolled-back versions stay in `.viveka/framework-memory/retired/` with rollback record.

**Expiry and revalidation.** Every active rule carries an expiry date (default 6 months from promotion). On expiry, the rule moves to a revalidation queue. Revalidation requires fresh evidence from recent task memories — old evidence does not count toward revalidation. Outcomes: *revalidated* (new expiry +6 months, version preserved), *retired* (moved to retired/), or *refined* (new version, fresh approval cycle).

**Rollback.** Active rules can be rolled back at any time. Three rollback paths:
- *Disable:* rule moves to retired/ with reason. Framework reverts to behaviour without the rule.
- *Restore prior version:* if a previous active version existed, restore it from retired/ at the previous version id.
- *Emergency disable:* in autonomous mode, if a rule causes a string of failures (configurable threshold), it is auto-disabled and queued for human review. This is the only auto-action in Phase A and it is destructive-safe (disabling a rule cannot break correctness — only remove guidance).

Rollbacks themselves are logged and remain visible in the rule's history.

**What Phase A explicitly does not do (deferred to Phase B).**
- No auto-promotion of any rule, regardless of evidence strength.
- No silent merges. Every promotion is human-approved.
- No automatic resolution of contradictions between rules.
- No rule-to-rule inference (deriving new rules from combinations of existing ones).
- No promotion based on single-task evidence under any condition.

Phase B will introduce semi-automatic promotion under strong evidence (default thresholds: N≥10 task memories, no active contradictions, prior versions of the rule successfully revalidated at least once). Phase B is **not yet specified and is not active**. Do not implement Phase B behaviour under Phase A.

Without this Phase A pipeline, framework memory is either a wishlist (no enforcement) or a danger (auto-mutation). Phase A is the safe middle: Viveka can learn from its own history, but only when the human says yes.

## Reading Previous Catalogues
At the start of new tasks, search `.viveka/memory/` and `.viveka/framework-memory/active/` (see viveka-context's Memory Read Protocol). Framework-memory active rules first, then task-memory correction rules, then loop-back records. Do not load all past catalogues — search by relevance.

## What Not to Catalogue
Routine operations with no insights. Speculative conclusions. Cataloguing for its own sake — every entry must earn its place.
