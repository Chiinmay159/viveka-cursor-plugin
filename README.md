# Viveka

The only Cursor plugin that governs both native tools and MCP tools. 16ms per action. 1,078 tokens for simple tasks. Hook+MCP hybrid scoring 43/48 on the ACP governance benchmark.

## What It Does

Viveka evaluates every agent action before it executes. File edits, shell commands, tool calls — all pass through a deterministic decision engine. No LLM cost. No network calls. No API keys.

Every action gets one of four verdicts:

- **Permit** — proceed silently.
- **Warn** — proceed, flag the concern to the agent.
- **Block** — stop the action, explain why, suggest alternatives.
- **Escalate** — pause and ask the human to decide.

## What It Catches

| Problem | How | When |
|---------|-----|------|
| Force-push to main/production | Git branch detection + git pre-push hook | Always blocked (any tool, any IDE) |
| `rm -rf`, `drop table`, `reset --hard` | Destructive command patterns | Blocked in guarded/restricted mode |
| Agent retrying the same failing command | Per-action retry counter | Blocked after 3 attempts (configurable) |
| Scope creep (editing 20 files for a "fix one bug" task) | File-modified counter | Warned at limit, blocked at overshoot |
| Runaway agent loops | Total action counter | Escalated to human at 100 actions |
| Secret exposure (.env, API keys, tokens) | Path/content pattern matching | Warned on access |
| Accumulated ignored warnings | Warning counter | Escalated when agent stops responding to signals |

## What It Ships

| Component | Count | Purpose |
|-----------|-------|---------|
| Reasoning kernel | 1 | Lean system prompt — six-stage pipeline, four postures, decision gates |
| Skills | 12 | On-demand depth: context mapping, architecture, code, research, review, etc. |
| Sub-agents | 4 | Isolated execution: code, research, doc-review, adversarial |
| Hook events | 5 | preToolUse, beforeShellExecution, afterFileEdit, sessionStart, stop |
| Git hooks | 2 | pre-push (branch protection), pre-commit (file count + secret detection) |
| MCP tools | 10 | Action checks, memory, session state, posture, constraints, scenarios, policies, trace |
| Policy packs | 5 | Pre-built governance for hotfixes, refactors, migrations, incidents, cleanup |

## Install

### Option A — Plugin only (zero dependencies)

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/viveka ~/.cursor/plugins/local/viveka
```

Restart Cursor. The reasoning kernel and skills activate immediately.

### Option B — Full governance (Python 3.10+)

```bash
pip install pydantic
```

If Python 3.10+ and pydantic are available, hooks and MCP tools activate automatically on next session start. Verify: Cmd+Shift+P → "MCP: List Tools" → look for `viveka`.

### Git hooks (recommended, any project)

```bash
cd your-project
git config core.hooksPath /path/to/viveka/githooks
```

Or copy individually: `cp /path/to/viveka/githooks/pre-* .git/hooks/`. This adds branch protection and file-count limits that work outside Cursor.

### Claude Code

```bash
cp /path/to/viveka/CLAUDE.md /your/project/CLAUDE.md
```

### Claude Chat

Copy content from `platforms/chat/preferences.md` into Settings → User Preferences.

## Architecture

```
┌─────────────────────────────────────────┐
│  Reasoning Kernel                       │  rules/ skills/ agents/
│  Shapes how the agent thinks            │  Prompt-based, always active
├─────────────────────────────────────────┤
│  Mandatory Enforcement                  │  hooks/ scripts/ githooks/
│  Gates every action — agent can't       │  IDE hooks + git hooks
│  opt out                                │  16ms round-trip
├─────────────────────────────────────────┤
│  Optional Tools (MCP)                   │  mcp-server/ → runtime/
│  Agent calls when it wants guidance     │  10 tools, all local, all free
├─────────────────────────────────────────┤
│  Cursor Platform                        │  Tool execution, context mgmt
└─────────────────────────────────────────┘
```

### Mandatory Enforcement

Two enforcement layers, both automatic. The agent cannot opt out of either.

**IDE hooks (Cursor).** Cursor fires a hook on every tool call, shell command, and file edit. The hook sends the event to a persistent background daemon over a Unix socket. The daemon holds the decision engine warm in memory — one-time startup cost, then ~0.01ms per evaluation.

The daemon computes a risk mode from the environment (branch, dirty state, available tools) and task context (intent, reversibility, urgency). Four modes: permissive, standard, guarded, restricted. Each mode sets limits on retries, file count, and action count.

Each Cursor window gets its own daemon, keyed by working directory. Two projects open in parallel never share state.

IDE hooks fail-open: if the daemon is unreachable, actions proceed. The reasoning kernel continues to guide the agent.

**Git hooks (any tool).** Two git-layer hooks enforce rules regardless of what initiated the operation — Cursor, CLI, VS Code, CI, or manual terminal use:

- `pre-push` — blocks force-pushes to protected branches (main, master, production, release). Same branch set as the IDE enforcement.
- `pre-commit` — checks staged file count against the active policy's limit. Warns at 80%, blocks at the limit. Also scans staged diffs for common secret patterns (API_KEY, SECRET_KEY, PRIVATE_KEY).

Install: `git config core.hooksPath githooks` or copy from `githooks/` into `.git/hooks/`.

### Optional Tools (MCP)

Ten tools the agent can call voluntarily — it is not forced to use them, but they give it access to the same governance engine:

| Tool | What it does |
|------|-------------|
| `viveka_check` | Evaluate a proposed action against the governance engine |
| `viveka_memory_read` | Search past task memories and correction rules |
| `viveka_memory_write` | Persist insights for future sessions |
| `viveka_session_state` | Read current risk mode, posture, and governance context |
| `viveka_status` | Health check across all layers |
| `viveka_update_posture` | Switch cognitive posture mid-session (syncs to daemon) |
| `viveka_constraint_check` | Validate text against hard constraints |
| `viveka_scenarios` | Get adversarial failure scenarios for the current context |
| `viveka_policies` | List available policy packs |
| `viveka_session_trace` | Export the full decision chain for the session |

The MCP server routes through the daemon when available (preserving session history). Falls back to standalone evaluation if the daemon is down.

### Reasoning Kernel

A lean system prompt that shapes agent behavior:

- **Four postures** — Standard, Exploratory (defer structure, widen search), Speed (compress stages), Adversarial (mandatory hostile-input sim).
- **Twelve skills** — loaded on-demand when task complexity warrants depth. Context mapping, architecture, code, research, writing, design, review, diagnosis, and more.
- **Four sub-agents** — auto-deploy for multi-file code changes, structured research, long document review, and adversarial analysis.
- **Decision gates** — every stage transition uses the same permit/warn/block/escalate vocabulary as enforcement.

### Policy Packs

Named governance configurations for specific workflows:

| Pack | Mode | File limit | Retry limit | Key constraint |
|------|------|-----------|-------------|----------------|
| `production-hotfix` | Restricted | 3 | 1 | Human approval required |
| `refactor-safe` | Standard | 15 | 3 | Tests required before deploy |
| `data-migration` | Guarded | 10 | 2 | Backup required, DROP/TRUNCATE blocked |
| `incident-response` | Restricted | 2 | 1 | Human approval required |
| `cleanup` | Standard | 20 | 3 | Check dynamic import references |

Custom packs: drop a YAML file in `~/.viveka/policies/`.

## Session Lifecycle

1. **Start** — daemon spawns, scans git, computes risk mode, loads policy. ~1s.
2. **Work** — every action evaluated in 16ms. Most permitted silently. Warnings, blocks, escalations when warranted.
3. **End** — checkpoint written to `.viveka/checkpoints/` (audit trail). Daemon exits. If Cursor crashes, 5-minute idle timeout handles cleanup.

## Dependencies

- **Kernel only:** Zero. No Python, no packages, no network.
- **Full governance:** Python 3.10+ and `pydantic`. No API keys, no accounts, no network access.

## Links

- [How Viveka Governs](docs/how-viveka-governs.md) — detailed runtime explainer for non-technical readers
- [Philosophy](PHILOSOPHY.md) — the six stages, postures, cross-cutting principles, and design rationale

*MIT License. Built by [Chinmay Bhandari](https://github.com/Chiinmay159)*
