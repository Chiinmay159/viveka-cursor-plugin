# Viveka

A cognitive framework for AI agents. One reasoning posture, ten skills, four platforms.

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
4. **Execution** — Plan roadmap, delegate single-function agents, live review throughout. Loop back when wrong.
5. **Review** — Health, bugs, coherence. Trace the journey from essence to output.
6. **Catalogue** — Insights, patterns, bugs, loop-backs, correction rules. Written to `.viveka/memory/`.

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

## Origin

Rooted in a universal pattern: hold what is universally true and what is locally true simultaneously. Right action emerges from their intersection without violating either.
