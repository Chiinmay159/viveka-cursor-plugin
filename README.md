# Viveka

A cognitive framework for AI agents. One reasoning posture, twelve skills, four platforms.

**Essence:** Viveka is a cognitive posture that produces healthy outputs through context-awareness, structural decomposition, and live coherence.

Viveka shapes how an agent thinks — not what tools it calls. The system prompt sets the posture. The skills provide depth when a stage needs more than the compressed version.

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

1. **Context** — Map natural order, time, place, entities, task. Search before assuming.
2. **Grasping** — Understand fully, simulate scenarios, evaluate by value equation. Decision gate: proceed or present.
3. **Architecture** — Essence → foundation → scope → sequence → detail → aesthetics. Dependency order.
4. **Execution** — Plan roadmap, apply dual-mode transition protocol, enforce bounded loop-backs, and run live review throughout.
5. **Review** — Health, bugs, coherence, sufficiency threshold, and autonomous acceptance when no human reviewer exists.
6. **Catalogue** — Insights, patterns, bugs, loop-backs, correction rules, and framework-memory promotion.

## Agentic-First Controls

- Dual-mode transitions at every stage boundary (interactive vs autonomous behavior).
- Time/cost bounds (loop-back cap, sub-agent depth cap, context budget signals at 70% and 90%).
- Stage audit trail for autonomous runs.
- Sub-agent verification gate for irreversible actions.
- Generation-vs-reasoning trip wire to force evidence search when confidence outpaces evidence.

## Tier 7: Posture Diversity

Viveka supports controlled posture selection per task:
- `standard` (default)
- `exploratory`
- `speed`
- `adversarial`

Safety invariants remain active in every posture:
- irreversible-action gate
- minimum review requirement for irreversible outcomes
- scope compliance

Switching policy:
- declare posture at task start
- max one switch per task unless escalated
- fall back to `standard` on conflict

## Tier 8: Self-Modification (Phase A)

Self-modification is currently supervised:
- no autonomous framework rewrites
- repeated correction patterns become promotion candidates
- candidates are stored in `.viveka/framework-memory/candidates/`
- contradiction check + rollback plan required
- human approval required before merge into framework

## Skills

| Skill | Triggers on |
|-------|------------|
| viveka-context | Complex environment mapping, unfamiliar codebase |
| viveka-grasp | Multiple viable approaches, significant stakes |
| viveka-architect | Compound outputs needing structural design |
| viveka-execute | Multi-agent delegation, long builds, drift risk |
| viveka-review | Significant deliverables needing examination |
| viveka-catalogue | Post-task learning capture |
| viveka-code | Source code output |
| viveka-writing | Prose output |
| viveka-research | Information finding and synthesis |
| viveka-design | Visual/UX output |
| viveka-decide | Decision support without implementation |
| viveka-diagnose | Debugging and root-cause analysis |

## Origin

Rooted in a universal pattern: hold what is universally true and what is locally true simultaneously. Right action emerges from their intersection without violating either.
