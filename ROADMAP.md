# Viveka v4.0 Roadmap

**Status:** Frozen until v3.0 has run in production sessions for 8–12 weeks.
**Trigger:** Resume when session traces show patterns that confirm or contradict the hypotheses below.
**Principle:** Every addition must demonstrate measurable intervention value. No feature earns its place through architectural elegance alone.

---

## Origin

Eight independent cold reviews (3 ChatGPT, 2 Claude, 1 source-level audit) converged on one finding: Viveka v3.0 has a solid 20% core inside 80% framework surface area. v4.0 extracts and strengthens the 20%.

The single metric that matters:

```
valuable_interventions / total_interventions
```

If the ratio is low, the tool annoys developers and dies. If it's high, it earns its place.

---

## What v3.0 proved

These components delivered real value and stay unchanged:

- Stateful session tracking (GovernedSession, accumulated counters)
- 7-rule deterministic engine (protected resources, branch safety, destructive commands, retry loops, scope drift, action budget, warning accumulation)
- Git hooks (pre-commit file count, pre-push branch protection)
- Daemon architecture (Unix socket, per-cwd isolation, crash recovery, fail-open)
- Auto-extracted learnings from governance trace on session end
- Dual-write memory (daemon records what happened, agent records what it learned)
- Four-verdict vocabulary (permit, warn, block, escalate)

## What v3.0 left unproven

These components have no measured impact. v4.0 either proves or removes them:

- 12 lazy-loaded skills (do 12 outperform 3?)
- 4 sub-agents (does adversarial sub-agent produce measurably different outcomes?)
- Posture switching (does switching to adversarial produce statistically better sessions?)
- 10 MCP tools (which ones does the agent actually call?)
- Framework memory promotion pipeline (has any rule ever been promoted?)
- Policy packs beyond 2–3 (are 5 packs needed or do sessions cluster around 2?)
- Governance traces as session output (are traces ever read by a human?)

---

## Phase 0: Observation (Weeks 1–12)

**Do nothing. Collect data.**

Instrument the daemon to log (append-only, structured JSON):

```json
{
  "session_id": "...",
  "timestamp": "...",
  "event": "evaluate",
  "action": "write_file src/auth.py",
  "verdict": "warn",
  "rule": "scope_drift",
  "files_modified": 7,
  "retries": 0,
  "session_action_count": 23
}
```

Log every MCP tool call (which tool, how often, did the agent act on the result).
Log every skill loaded (which skill, for what task type, how many tokens).

After 12 weeks, answer:

- Which rules actually fire? How often?
- Which MCP tools does the agent call? Which ones never?
- Which skills load? Which ones never?
- How many sessions hit posture switches?
- How many times did memory_read return something the agent used?
- What is the current valuable_interventions / total_interventions ratio?

**This data determines everything that follows.**

---

## Phase 1: Prune (Week 13)

Based on Phase 0 data, remove what doesn't earn its keep.

**MCP tools:** Any tool called fewer than 5 times in 12 weeks is a candidate for removal or consolidation. The reviewer's proposed minimum: `risk_check`, `session_status`, `why_blocked`. If data supports it, consolidate 10 tools down to 4–5.

**Skills:** Any skill loaded fewer than 10 times in 12 weeks is a candidate for merging into its nearest neighbor. The reviewer's hypothesis: 3–4 skills cover 90% of loads.

**Sub-agents:** If the adversarial sub-agent fired fewer than 5 times, merge its prompt content into the main kernel and remove the agent definition.

**Policy packs:** If sessions cluster around 2 packs, archive the others.

**Framework memory:** If no rule was ever promoted, simplify to flat task memory only.

**Target:** Reduce surface area to match observed usage. Every surviving component has empirical justification.

---

## Phase 2: Instability Detection (Weeks 14–16)

This is the highest-value new capability identified across all reviews: detecting when an agent is entering an unstable failure trajectory.

### 2a: Oscillating diffs

**What it detects:** Agent rewrites the same file repeatedly with alternating changes. Write A, revert to B, write A again. This is the signature of an agent stuck between two approaches.

**Implementation:** The daemon already tracks files modified. Add a per-file content hash on each `afterFileEdit`. If the hash oscillates (A → B → A or A → B → C → B), flag as oscillation.

**Verdict:** Warn on first oscillation. Escalate on second.

**Lines:** ~40 in GovernedSession.

### 2b: Cascading test failures

**What it detects:** Agent makes changes, runs tests, tests fail, agent makes more changes, more tests fail. Cascading breakage indicates the agent is making things worse, not better.

**Implementation:** Track test command outcomes via `afterShellExecution`. If the agent runs tests and the exit code is non-zero, increment a failure counter. If failures increase monotonically across 3+ test runs, escalate.

**Verdict:** Warn after 2 consecutive test failures. Escalate after 3.

**Lines:** ~30 in MicroDecisionEngine.

### 2c: Revert-edit cycles

**What it detects:** Agent uses `git checkout`, `git restore`, or `git stash` followed by editing the same files. This indicates the agent undid its own work and is trying again — a retry loop at the git level that the current retry detector (which tracks action strings) misses.

**Implementation:** Track git restore/checkout/stash commands in the session. If the agent edits a file it previously reverted, flag as revert-edit cycle.

**Verdict:** Warn on first occurrence. Block on second.

**Lines:** ~50 in GovernedSession.

### Phase 2 total: ~120 lines. Three new rules. Each catches a failure mode the current 7 rules miss entirely.

---

## Phase 3: Structural Awareness (Weeks 17–20)

Move the rule engine from "what the action looks like" to "what the action affects."

### 3a: Dependency graph (import scanning)

**What it adds:** On session start, scan project files for import relationships. Build adjacency dict. When the agent modifies a file, look up how many other files depend on it.

**Effect on verdicts:** High-dependent files (10+ importers) get stricter thresholds. Modifying `utils.py` (imported by 20 files) is categorically different from modifying `test_helper.py` (imported by 0).

**Implementation:** Python's `ast` module for `.py` files. Regex for `import`/`require` in JS/TS. One-time scan at session start.

**Lines:** ~150 in new module `runtime/viveka/layers/depgraph.py`.

### 3b: AST-aware file risk scoring

**What it adds:** On `afterFileEdit`, parse the modified file's AST. Score by structural importance: does it define public functions? Does it contain error handling? Did the edit change function signatures?

**Effect on verdicts:** Structural changes (signature modifications, removed error handling) get higher risk scores than additive changes (new functions, new methods).

**Implementation:** Python's built-in `ast` module for `.py` files. Runs on `afterFileEdit` (post-action, doesn't block). ~1ms per file.

**Lines:** ~200 in new module `runtime/viveka/layers/ast_analyzer.py`.

### 3c: Cross-file coherence

**What it adds:** When the agent changes a function signature in file A, check whether callers in files B, C, D (identified by the dependency graph) were also updated in this session.

**Effect on verdicts:** Warn if signature changed but callers not yet modified. The agent sees: "authenticate() signature changed in auth.py. 3 callers not yet updated: user_service.py, api_handler.py, middleware.py."

**Implementation:** Combines dependency graph (3a) + AST analysis (3b). ~100 lines in a new check method.

### Phase 3 total: ~450 lines. Three new capabilities. The rule engine moves from pattern matching to structural awareness. Python-only initially. JS/TS in a future phase if traces show demand.

---

## Phase 4: Memory Feedback Loop (Week 21)

**What it adds:** Memory feeds back into enforcement. If scope drift occurred 3 times on auth module tasks in past sessions, the daemon automatically tightens the file limit for the next auth module task.

**Implementation:** On session start, `_adjust_limits_from_memory()` reads `.viveka/memory/` for the current project. Finds recurring patterns (same rule, same file area, 3+ sessions). Nudges thresholds: if scope drift recurred, reduce file limit by 20%. If retry loops recurred on a specific file type, reduce retry limit by 1.

**Effect:** The rule engine adapts to the project's actual failure patterns. Not a learning pipeline — a threshold adjustment based on observed history.

**Lines:** ~100 in daemon.

---

## Phase summary

| Phase | When | Lines | What changes |
|-------|------|-------|-------------|
| 0: Observe | Weeks 1–12 | ~50 (logging) | Nothing. Collect data. |
| 1: Prune | Week 13 | Negative (removing code) | Surface area shrinks to match usage |
| 2: Instability | Weeks 14–16 | ~120 | Oscillation, cascading failures, revert cycles |
| 3: Structural | Weeks 17–20 | ~450 | Dependency graph, AST scoring, cross-file coherence |
| 4: Feedback | Week 21 | ~100 | Memory adjusts enforcement thresholds |

**Total new code: ~720 lines across 4 build phases.**
**Total removed code: determined by Phase 0 data, likely 500–2,000 lines.**

Net result: the codebase may shrink while capabilities grow. The 20% core gets stronger. The 80% surface gets pruned.

---

## What v4.0 does NOT attempt

- Semantic analysis of code meaning
- Formal verification of agent behavior
- Sandboxed execution environments
- Multi-tenant or enterprise governance
- Model-level intervention in agent reasoning
- General-purpose agent orchestration

These are either unsolved research problems or products for a different market. Viveka stays in its lane: detecting mechanical and structural failures cheaply, deterministically, and locally.

---

## Success criteria

v4.0 is complete when:

1. Every surviving component has empirical usage data justifying its presence
2. Instability detection catches at least one failure mode per 10 sessions that v3.0 missed
3. Structural awareness produces verdicts that reference specific files and callers, not just counters
4. Memory feedback demonstrably changes enforcement behavior based on project history
5. The valuable_interventions / total_interventions ratio exceeds 0.7

If any of these fail, the corresponding phase is reverted. The product is better smaller and proven than larger and theoretical.

---

## The governing principle

From the review that triggered this roadmap:

> "A lightweight system detecting unstable failure trajectories well would be genuinely valuable."

v4.0 is that system. Nothing more.
