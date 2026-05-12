# Viveka

Cognitive governance for AI agents. One reasoning posture, deterministic enforcement, decision tools.

**Essence:** Viveka is a cognitive posture that produces healthy outputs through context-awareness, structural decomposition, and live coherence.

## Three Layers, One Install

Viveka ships as a single Cursor plugin with three integration layers:

**Layer 1 — Cognitive Posture** (rules, skills, agents). Shapes how the agent reasons. Six-stage pipeline, four postures, four sub-agents, twelve skills. Works immediately on install. No dependencies.

**Layer 2 — Enforcement** (hooks). A deterministic micro-decision engine evaluates every tool call, shell command, and file edit. Permits, warns, blocks, or escalates to the user. No LLM cost. Runs in milliseconds. Requires Python 3.10+.

**Layer 3 — Decision Tools** (MCP server). Exposes `viveka_check`, `viveka_memory_read`, `viveka_memory_write`, and `viveka_session_state` as tools the agent can call. Memory persists across sessions. Requires Python 3.10+.

```
┌─────────────────────────────────────────┐
│  Layer 1: Cognitive Posture             │  rules/ skills/ agents/
│  "How should I think about this?"       │  Prompt-based, always active
├─────────────────────────────────────────┤
│  Layer 2: Enforcement                   │  hooks/ → runtime/
│  "Is this action permitted?"            │  Deterministic, hook-enforced
├─────────────────────────────────────────┤
│  Layer 3: Decision Tools                │  mcp-server/ → runtime/
│  "What does governance say?"            │  Agent-callable, local only
├─────────────────────────────────────────┤
│  Cursor Platform                        │  Tool execution, context mgmt
└─────────────────────────────────────────┘
```

## Install

### Tier 1 — Plugin only (zero dependencies)

Install from Cursor Marketplace, or:

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/viveka ~/.cursor/plugins/local/viveka
```

Restart Cursor. Layer 1 (cognitive posture) is immediately active. Layers 2 and 3 require Python.

### Tier 2 — Full governance (Python 3.10+)

The plugin includes the runtime. If Python 3.10+ is available, hooks and MCP tools activate automatically. No pip install needed — the runtime is bundled.

Verify it works: open a Cursor session and check for `viveka` in the MCP tools list (Cmd+Shift+P → "MCP: List Tools").

### Claude Code

Copy the system prompt to your project:
```bash
cp /path/to/viveka/CLAUDE.md /your/project/CLAUDE.md
```

### Claude Chat

Copy content from `platforms/chat/preferences.md` into Settings → User Preferences.

## Architecture

### The Six Stages

1. **Context** — Map environment, constraints, tools, memory. Search `.viveka/memory/` before assuming.
2. **Grasping** — Understand fully, simulate scenarios, evaluate by value equation. Decision gate: proceed or present.
3. **Architecture** — Essence → foundation → scope → sequence → detail → surface aesthetics. Dependency order.
4. **Execution** — Plan roadmap, delegate under inter-agent contracts, live review. Loop back when wrong (max 3).
5. **Review** — Health, bugs, coherence, sufficiency. Trace the journey from essence to output.
6. **Catalogue** — Insights, patterns, bugs, loop-backs, correction rules. Written to `.viveka/memory/`.

### Postures

- **Standard** (default) — the protocol as written.
- **Exploratory** — defers Architecture, increases lateral generation. For ideation.
- **Speed** — compresses stages, defers Catalogue. For triage.
- **Adversarial** — deepens Review, mandatory hostile-input simulation. For high-stakes work.

Three invariants hold across all postures: essence adherence, irreversible-action gate, review requirement.

### Sub-agents

Four sub-agents activate when task type and scale warrant isolation:

- **viveka-code-agent** — coding work of meaningful size (multi-file, >50 lines, test execution).
- **viveka-research-agent** — substantial research with read-only tools.
- **viveka-doc-review-agent** — long document review (>3000 words) in isolated context.
- **viveka-adversarial** — posture-driven. Deepened review, mandatory kill-case analysis.

Activation is type-driven: no-agent (default) / auto-deploy / ask-first / user-requested.

### Enforcement (Hooks)

The micro-decision engine runs as Cursor hooks on these events:

- `preToolUse` — evaluates every tool call before execution
- `beforeShellExecution` — gates shell commands (blocks destructive ops)
- `afterFileEdit` — post-edit audit
- `sessionStart` — initializes governance context
- `stop` — cleanup

The engine is deterministic: regex rules, pattern matching, state tracking. No LLM calls. Actions receive one of four verdicts: **permit** (proceed), **warn** (proceed with flag), **block** (stop, explain why), **escalate** (ask the user).

Hooks fail-open: if Python is unavailable, all actions proceed. The cognitive layer still guides reasoning.

### Decision Tools (MCP)

Four MCP tools available when the server is running:

| Tool | What it does | Cost |
|------|-------------|------|
| `viveka_check` | Governance check for a proposed action | Zero (deterministic) |
| `viveka_memory_read` | Search past task memories and framework rules | Zero (file I/O) |
| `viveka_memory_write` | Persist task memory for future sessions | Zero (file I/O) |
| `viveka_session_state` | Read current risk mode and governance context | Zero (file read) |

### Memory

Two tiers:

- `.viveka/memory/` — per-task memory. Insights, loop-backs, correction rules from a single task.
- `.viveka/framework-memory/` — promoted rules. When the same correction rule recurs across tasks, it enters a supervised promotion pipeline: candidate → contradiction check → human review → merge.

Memory is read at the start of every task (via `viveka_memory_read` or manual search). Framework-memory active rules first, then task-memory correction rules, then loop-back records.

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
| viveka-decide | Decision support without artifact production |
| viveka-diagnose | Debugging, root-cause analysis |

## Cross-cutting

- **Cost as signal** — 70% context consumed → narrow scope. 90% → escalate or terminate.
- **Confidence calibration** — epistemic vs aleatory. Propagation rule: output confidence <= lowest input confidence.
- **Generation-vs-reasoning trip wire** — high confidence + thin evidence → stop and search.
- **Stage audit trail** — posture, switches, agent activations, stages entered/skipped, loop-backs.
- **Bounded loop-backs** — max 3 returns to upstream stages. Thrash detection.

## No External Dependencies

Viveka requires no API keys, no accounts, no network access. The enforcement layer is deterministic Python. The decision tools are local file I/O. The cognitive reasoning runs in whatever model Cursor provides.

## Origin

Viveka (विवेक) — Sanskrit for discriminative wisdom: the capacity to distinguish what is real from what is apparent, what is essential from what is incidental.

*MIT License. Built by [Chinmay Bhandari](https://github.com/Chiinmay159)*
