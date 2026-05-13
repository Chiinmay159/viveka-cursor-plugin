# Viveka

Guardrails for AI agents in Cursor. Intercepts every agent action at the platform hook level and every git operation at the repository level. Evaluates against a stateful rule engine, returns a verdict before execution. No LLM cost. No network calls. Runs locally.

## Verdicts

Every intercepted action receives one of four verdicts:

| Verdict | Effect |
|---------|--------|
| `permit` | Action proceeds silently |
| `warn` | Action proceeds, concern flagged to agent |
| `block` | Action stopped, reason and alternative provided |
| `escalate` | Action paused, human asked to decide |

## Rules

Seven rule categories. Pattern matching and heuristic counters — not semantic analysis, not formal verification. Catches mechanical failures that are cheap to detect and expensive to recover from.

| Rule | Trigger | Default |
|------|---------|---------|
| Protected resources | Write to `.env`, secrets, locked paths | Warn or block |
| Branch safety | Force-push to main/production | Block |
| Destructive commands | `rm -rf`, `drop table`, `reset --hard` | Block in guarded/restricted |
| Retry loops | Same normalized action ≥3 times | Block (reads and test runs exempt) |
| Scope drift | Files modified exceeds policy limit | Warn → block at overshoot |
| Action budget | Total actions exceed session limit | Escalate |
| Warning accumulation | Agent ignoring repeated warnings | Escalate |

Thresholds are configurable per policy pack. The engine does not understand code semantics, verify business logic, or reason about dependencies.

## Architecture

Four independent components. Each works alone. Together they reinforce each other.

```
┌──────────────────────────────────────────────────────────────┐
│  Reasoning Kernel         rules/ skills/ agents/             │
│  System prompt. Shapes agent reasoning.                      │
│  Zero dependencies. Always active.                           │
├──────────────────────────────────────────────────────────────┤
│  Enforcement Daemon       scripts/ hooks/ → runtime/         │
│  Persistent process. Holds session state.                    │
│  Evaluates every action via Cursor hooks.                    │
│  Python 3.10+ required.                                      │
├──────────────────────────────────────────────────────────────┤
│  Git Hooks                githooks/                          │
│  pre-commit: file count vs policy. pre-push: branch safety.  │
│  Pure shell. No daemon dependency. Survives outside Cursor.  │
├──────────────────────────────────────────────────────────────┤
│  MCP Tools                mcp-server/ → runtime/             │
│  10 tools the agent calls voluntarily.                       │
│  Routes through daemon when available.                       │
│  Python 3.10+ required.                                      │
└──────────────────────────────────────────────────────────────┘
```

### Enforcement daemon

The daemon exists because rule evaluation needs session context. Whether an action is permitted depends on what happened earlier in the session: how many files were already modified, how many warnings were issued, how many retries were attempted, which policy pack is active. A stateless hook cannot track this. The daemon holds a `GovernedSession` object warm in memory, so each evaluation has full session history at ~0.01ms evaluation cost after a one-time ~1s startup.

**Lifecycle:**

1. Cursor fires `sessionStart` → hook script spawns daemon, daemon scans git state, computes risk mode, loads policy pack, binds Unix socket keyed by working directory.
2. Every tool call, shell command, and file edit fires a hook → hook script sends event over Unix socket → daemon evaluates against rule engine + session state → returns verdict. Round-trip: ~16ms.
3. Session ends → daemon auto-extracts task learnings from the governance trace (patterns, repeated warnings, scope drift events, correction rules), writes them to `.viveka/memory/`, writes checkpoint to `.viveka/checkpoints/`, cleans up socket and PID file, exits. If user walks away, 5-minute idle timeout handles cleanup.

**Failure handling:** If daemon crashes mid-session, hook script detects dead socket, attempts one respawn from saved session state. If respawn fails, hooks fail-open (actions proceed without evaluation). This is deliberate: blocking a developer's workflow because the safety tool died is worse than temporarily losing enforcement. The reasoning kernel continues to guide agent behavior regardless.

**Isolation:** Each working directory gets its own daemon instance via socket path hashing. Two Cursor windows on different projects never share state, counters, or policy configuration.

**What the daemon tracks per session:**

- Files modified (list and count)
- Actions evaluated (with sequence numbers)
- Warnings issued (count and content)
- Retries per normalized action
- Risk mode (computed from environment + task context)
- Active policy pack constraints
- Full governance trace (every action, verdict, rule, reason)
- Auto-extracted learnings on session end (distilled from trace to `.viveka/memory/`)

### Git hooks

Enforcement that survives outside Cursor. Two git hooks extend the rule engine to the repository level, catching actions regardless of which tool or agent initiated them:

**`pre-commit`** — checks staged file count against the active policy pack's file limit. If a commit touches more files than the policy allows, the commit is rejected with the limit and current count. Prevents scope drift from reaching the repository even if the Cursor daemon is down.

**`pre-push`** — checks the target branch against branch protection rules. Force-pushes to protected branches (main, master, production, release/*) are rejected. Normal pushes to protected branches require confirmation. Catches the force-push case that every reviewer flags as the obvious mechanical failure.

Both hooks read policy from `.viveka/policy.yaml` if present, otherwise apply defaults. They run without the daemon — pure shell scripts, no Python dependency, no socket communication.

**Install:**

```bash
cp githooks/pre-commit .git/hooks/pre-commit
cp githooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-commit .git/hooks/pre-push
```

Or symlink for automatic updates:

```bash
ln -sf ../../githooks/pre-commit .git/hooks/pre-commit
ln -sf ../../githooks/pre-push .git/hooks/pre-push
```

### Reasoning kernel

A 50-line system prompt plus 12 on-demand skills and 4 sub-agent definitions. Shapes how the agent approaches tasks through:

- **Six-stage flow** — Context → Grasping → Architecture → Execution → Review → Catalogue. Decision gates between stages use the same permit/warn/block/escalate vocabulary as the daemon.
- **Four postures** — Standard (default), Exploratory (defer structure, widen search), Speed (compress stages, defer Catalogue), Adversarial (mandatory hostile-input simulation, deepened Review).
- **On-demand skills** — 12 skill files loaded by Cursor when task type matches. Simple tasks load no skills (~1,100 tokens overhead). Complex multi-file code tasks load 2–3 skills (~3,000–6,700 tokens).
- **Sub-agents** — 4 definitions for isolated delegation: code (multi-file changes), research (read-only), doc-review (long documents), adversarial (kill-case analysis).

The kernel is a structured system prompt, not executable infrastructure. Its value is behavioral: agents with the kernel show better scope discipline, more consistent self-correction, and fewer runaway modification patterns than agents without it. This is observable in session traces but not provable from code inspection.

### MCP tools

Ten tools the agent can call through Cursor's MCP interface. The MCP server routes through the daemon when available (preserving session history), falls back to standalone evaluation, falls back to graceful error.

| Tool | Input | Output |
|------|-------|--------|
| `viveka_check` | Proposed action string | Verdict + reason + suggestions |
| `viveka_memory_read` | Query string, scope filter | Matching memory entries sorted by relevance |
| `viveka_memory_write` | Key, value, optional tags | Persisted JSON in `.viveka/memory/` |
| `viveka_session_state` | None | Risk mode, posture, enforcement mode, task context |
| `viveka_status` | None | Health of kernel, daemon, MCP across all components |
| `viveka_update_posture` | New posture name | Posture updated, synced to daemon enforcement mode |
| `viveka_constraint_check` | Text to validate, list of constraints | Violations found (keyword-based, no LLM) |
| `viveka_scenarios` | None | Failure scenarios filtered by current risk mode |
| `viveka_policies` | None | Available policy packs with descriptions |
| `viveka_session_trace` | None | Full action chain: sequence, action, verdict, rule, reason |

## Policy packs

Named rule configurations. Select on session start or switch mid-session via `viveka_update_posture`.

| Pack | Risk mode | File limit | Retry limit | Key constraint |
|------|-----------|-----------|-------------|----------------|
| `production-hotfix` | Restricted | 3 | 1 | Human approval required |
| `refactor-safe` | Standard | 15 | 3 | Tests required before deploy |
| `data-migration` | Guarded | 10 | 2 | Backup required, DROP/TRUNCATE blocked |
| `incident-response` | Restricted | 2 | 1 | Human approval required |
| `cleanup` | Standard | 20 | 3 | Check dynamic import references |

Custom packs: drop a YAML file in `~/.viveka/policies/`.

## Memory

Two tiers of cross-session persistence:

**Task memory** (`.viveka/memory/`) — per-task JSON files. On session end, the daemon auto-extracts learnings from the governance trace: recurring patterns, scope drift events, repeated warnings, and correction rules. The agent can also write insights directly via `viveka_memory_write`. This dual-write design closes a trust boundary: the daemon records what actually happened regardless of whether the agent chooses to self-report. Future sessions search this via `viveka_memory_read`.

**Framework memory** (`.viveka/framework-memory/`) — promoted correction rules. This is a human-supervised workflow, not an automated pipeline: the agent proposes correction candidates when a pattern recurs across tasks. The human reviews, approves, or rejects. Approved rules are merged with version tracking and expiry dates. The specification is in `skills/viveka-catalogue/SKILL.md`.

## Degradation

| State | What works |
|-------|-----------|
| Python absent | Kernel + git hooks (reasoning shaping, branch/scope protection, no daemon) |
| Pydantic absent | Kernel + git hooks |
| Daemon crashes | Respawn attempted once. If fails, fail-open with kernel + git hooks active |
| MCP unavailable | Daemon still enforces via Cursor hooks. Kernel + git hooks active |
| Everything present | All four components reinforcing each other |

## Install

### Kernel only (zero dependencies)

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/viveka-cursor-plugin ~/.cursor/plugins/local/viveka
```

Restart Cursor. Reasoning kernel and skills activate immediately. No enforcement, no MCP tools, no Python required.

### Full install (Python 3.10+)

```bash
pip install pydantic
```

Hooks and MCP tools activate automatically on next session start. Verify: `Cmd+Shift+P` → `MCP: List Tools` → look for `viveka_check`.

### Claude Code

```bash
cp /path/to/viveka-cursor-plugin/CLAUDE.md /your/project/CLAUDE.md
```

Reasoning kernel only. Claude Code has its own hook system.

### Claude Chat

Copy content from `platforms/chat/preferences.md` into Settings → User Preferences. Reasoning kernel only.

## What it is not

- **Semantic analysis.** Does not understand code meaning or verify business logic.
- **Formal verification.** Rules are pattern matching and counters, not proofs.
- **Sandboxing.** Actions execute in the normal Cursor environment.
- **Multi-tenant governance.** Governs one developer in one IDE.
- **Enterprise compliance.** No immutable audit logs, no cryptographic signatures, no regulatory certification.

## Inventory

```
viveka-cursor-plugin/
├── rules/viveka-framework.mdc        50 lines     reasoning kernel
├── skills/                           12 files     on-demand skills
├── agents/                            4 files     sub-agent definitions
├── scripts/viveka-daemon.py         485 lines     enforcement daemon
├── scripts/viveka-hook.sh            84 lines     bash hook client
├── hooks/hooks.json                               5 Cursor events
├── githooks/pre-commit                            file count vs policy
├── githooks/pre-push                              branch protection
├── mcp-server/server.py             674 lines     10 MCP tools
├── runtime/viveka/                ~1,800 lines     rule engine, models, session,
│                                                   constraints, scenarios, contracts,
│                                                   policies, traces, readiness
├── CLAUDE.md                         50 lines     kernel for Claude Code
├── PHILOSOPHY.md                                  design rationale
└── CHANGES.md                                     version history
```

Runtime: ~3,500 lines Python. Kernel + skills + agents: ~1,200 lines markdown.

## Origin

Viveka (विवेक) — Sanskrit for the capacity to distinguish what is real from what is apparent. Design rationale in [PHILOSOPHY.md](PHILOSOPHY.md).

MIT License. Built by [Chinmay Bhandari](https://github.com/Chiinmay159).
