# Viveka

A cognitive framework for AI agents. One reasoning posture, twelve skills, four sub-agents, four platforms.

**Essence:** Viveka is a cognitive posture that produces healthy outputs through context-awareness, structural decomposition, and live coherence.

Viveka shapes how an agent thinks — not what tools it calls. The system prompt sets the posture. The skills provide depth when a stage needs more than the compressed version. The framework runs in two modes — *interactive* (a human can be asked) and *autonomous* (decisions go to a log under pre-set policy) — using the same protocol with different terminals.

## Install

### Claude Code + Cowork (plugin)

```bash
cd /path/to/viveka-os
zip -r viveka.plugin . -x "*.DS_Store" "platforms/*"
```

Then: Claude Desktop → Cowork → Plugins → Upload → select `viveka.plugin`

For Claude Code, also copy the system prompt to your project:
```bash
cp /path/to/viveka-os/CLAUDE.md /your/project/CLAUDE.md
```

### Cursor (native plugin)

Local development install:

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/viveka-os ~/.cursor/plugins/local/viveka
```

Then restart Cursor (or run `Developer: Reload Window`).

For marketplace publication, push this folder to GitHub and submit it at:
`https://cursor.com/marketplace/publish`

### Claude Chat

Copy content from `platforms/chat/preferences.md` into Settings → User Preferences.

## The Six Stages

1. **Context** — Map natural order, time, place, entities, task. Search memory before assuming.
2. **Grasping** — Understand fully, simulate scenarios, evaluate by value equation. Decision gate: proceed or present.
3. **Architecture** — Essence → foundation (incl. foundational aesthetics) → scope → sequence → detail → surface aesthetics. Dependency order.
4. **Execution** — Plan roadmap, delegate under inter-agent contracts, live review throughout. Loop back when wrong (max three).
5. **Review** — Health, bugs, coherence, sufficiency. Trace the journey from essence to output.
6. **Catalogue** — Insights, patterns, bugs, loop-backs, correction rules. Written to `.viveka/memory/`. Promotes to `.viveka/framework-memory/` when a rule recurs across tasks.

## Cross-cutting principles

Cost as in-loop signal. Confidence calibration. Generation-vs-reasoning trip wire. Stage audit trail. Bounded loop-backs (max three).

## Operating modes

**Interactive:** declare findings at significant transitions, ask user for approval, proceed silently for trivial transitions.

**Autonomous:** declare to a log, apply pre-set policy ("on ambiguity, escalate; on irreversible action, halt and queue; on trivial, proceed"), log becomes audit trail.

## Sub-agents

Four sub-agents are available for tasks where isolation is structurally useful. Activation is type-driven, not user-managed:

- **viveka-code-agent** — coding work of meaningful size (multi-file, >50 lines, or test-running).
- **viveka-research-agent** — substantial research with read-only tools (cannot edit or execute).
- **viveka-doc-review-agent** — long document review (>3000 words / >10 pages) in isolated context.
- **viveka-adversarial** — posture-driven activation. Deepened review with mandatory hostile-input simulation, paranoid sub-agent verification, kill-case analysis, tightened cost thresholds.

Activation states: *no agent* (default — basic interaction), *auto-deploy* (clear case meeting type/scale criteria), *ask first* (gray case — Viveka surfaces the proposal), *user-requested* (always permitted, overrides framework judgment). Session override memory suppresses re-asking after a user veto. Posture × activation: Adversarial always spawns viveka-adversarial; Speed suppresses optional activations; Standard and Exploratory follow type-driven rules.

Every activation decision is recorded in the audit trail.

## Postures

Default is *standard* Viveka. Three alternative postures can be declared at task start:

- **Exploratory** — defers Architecture, increases lateral generation in Grasp, reduces verification weight. For ideation.
- **Speed** — compresses every stage, defers Catalogue unless a correction rule is generated. For triage and quick fixes.
- **Adversarial** — deepens Review, mandatory hostile-input simulation, paranoid sub-agent verification, tighter cost thresholds. For security, legal, and high-stakes work.

Three invariants hold across all postures: essence adherence, irreversible-action gate, review requirement. Posture switching is constrained — at most one switch per task without escalation; switching to Adversarial is always permitted, switching away from it requires escalation. Posture is orthogonal to operating mode and is recorded in the audit trail.

## Skills

| Skill | Triggers on |
|-------|------------|
| viveka-context | Complex environment mapping, unfamiliar codebase, tool/connector landscape |
| viveka-grasp | Multiple viable approaches, significant stakes |
| viveka-architect | Compound outputs needing structural design |
| viveka-execute | Multi-agent delegation, long builds, drift risk, resumable work |
| viveka-review | Significant deliverables needing examination |
| viveka-catalogue | Post-task learning capture; framework-memory promotion |
| viveka-code | Source code output |
| viveka-writing | Prose output |
| viveka-research | Information finding and synthesis with confidence calibration |
| viveka-design | Visual/UX output |
| viveka-decide | Decision support without artifact production |
| viveka-diagnose | Debugging, root-cause analysis, hypothesis testing |

## Memory

Viveka writes to two memory locations:

- `.viveka/memory/` — per-task memory. Insights, loop-backs, correction rules from a single task.
- `.viveka/framework-memory/` — promoted rules. When the same correction rule appears across N task memories with consistent evidence, it enters a supervised promotion pipeline (Phase A): candidate generation → contradiction check → human review → merge. Active rules carry version, expiry, and rollback path. Auto-promotion (Phase B) is deferred and not active.

Read at the start of every task. Framework-memory active rules first, then task-memory correction rules, then loop-back records.

## Origin

Rooted in a universal pattern: hold what is universally true and what is locally true simultaneously. Right action emerges from their intersection without violating either.
