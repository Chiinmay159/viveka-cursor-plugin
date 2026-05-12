# Viveka — Changes log

## v3.0.0 (current) — Lazy skill loading + runtime extraction + audit hardening

### Lazy skill loading (CLAUDE.md → kernel)
CLAUDE.md reduced from 19,382 bytes (~4,845 tokens) to 4,791 bytes (~1,198 tokens). The monolithic framework document is replaced by a lean kernel that contains the reasoning posture, transition protocol, and a skill trigger map. Stage-specific content (Context, Grasping, Architecture, Execution, Review, Catalogue) is no longer always-loaded — each lives in its on-demand skill, loaded when the task requires it. Domain skills (code, writing, design, research, decide, diagnose) remain on-demand as before.

Three loading strategies in the trigger map:
- **Need-based:** agent detects it's entering a stage that warrants depth → loads the stage skill.
- **Task-based:** task type detected (code, research, decision) → loads the domain skill.
- **Ask-based:** user invokes `/viveka-<name>` → loads explicitly.

For simple tasks (quick answers, single-file edits), the kernel is sufficient. No skills load.

| Scenario | Before (always-on) | After (on-demand) |
|----------|--------------------|--------------------|
| Simple task | ~6,109 tokens | ~1,078 tokens |
| Code task | ~6,109 tokens | ~2,996 tokens |
| Complex code | ~6,109 tokens | ~6,700 tokens |
| Research | ~6,109 tokens | ~2,915 tokens |

Agent Activation protocol moved from CLAUDE.md to viveka-context skill (where the activation decision is made).

### Runtime extraction
~1,700 lines of model-independent governance code extracted from v0.5.0 into `runtime/viveka/`. 10 MCP tools, 9 daemon events. PolicyPack system wired into daemon.

### Audit hardening (7 bugs fixed, 3 maintenance risks resolved)
- GovernedToolkit redesigned as pure stage-contract gate (was double governance gate)
- Invariant checks consolidated to single source in scanner.py
- max_retries derived from _LIMITS (was duplicate definition)
- PolicyPack blocked_paths/tools applied to engine permissions (was dead code)
- Daemon evaluate() routes through GovernedSession (was bypassing session trace)
- GovernedToolkit records tool calls (was missing from all paths)
- Grammar fix in readiness.py

---

## v2.2.0 — Persistent daemon: 14x hook performance

Hook overhead reduced from 22.8s to 1.7s per session (40 tool calls).

### Architecture change
The old design spawned a new Python process for every hook event (~570ms each: Python startup + pydantic import + environment scan + rule evaluation). The new design:

1. **`viveka-daemon.py`** — long-running Python process started once on `sessionStart`. Imports all heavy dependencies upfront, creates the `MicroDecisionEngine`, listens on a Unix domain socket. The actual rule evaluation takes <0.1ms.
2. **`viveka-hook.sh`** — bash thin client invoked by Cursor for each hook event. Sends the payload to the daemon over the Unix socket via `nc -U`. Bash+nc starts in ~8ms vs ~50ms for Python.
3. **Fail-open preserved** — if the daemon is unreachable (crashed, Python unavailable), the bash client returns `{"continue": true}` immediately.

### Measured performance

| Metric | v2.1.0 | v2.2.0 |
|--------|--------|--------|
| Per-hook latency | ~570ms | ~16ms |
| 40-call session overhead | 22.8s | 1.7s |
| Daemon startup (one-time) | — | ~1s |
| Idle timeout | — | 5 min |

### Fallback chain
`viveka-hook.sh` (bash+nc, 8ms) → `viveka-hook.py` (Python thin client, 50ms) → fail-open (0ms). The Python thin client is retained as a cross-platform fallback for systems without `nc -U`.

---

## v2.1.0 — Jargon unification + posture-enforcement bridge

Five internal consistency fixes that resolve conflicts between the cognitive layer and the deterministic runtime.

### Fix 1: Posture → enforcement mode bridge
Cognitive postures (standard/exploratory/speed/adversarial) now influence the enforcement mode. Adversarial posture nudges toward guarded mode. Exploratory and speed postures nudge toward permissive mode. Standard posture uses the computed mode. Session state tracks both.

### Fix 2: Enforcement modes renamed
Runtime risk modes renamed to eliminate collision with cognitive postures: explore→permissive, balanced→standard, cautious→guarded, locked→restricted. Postures shape reasoning depth; enforcement modes shape action latitude. Different systems, different names.

### Fix 3: Intent detection from task description
Session start now parses the task description for intent signals (fix, improvement, exploration, maintenance, recovery) instead of always defaulting to "feature". Pattern-priority order prevents ambiguous matches.

### Fix 4: Unified decision vocabulary
One vocabulary across all layers — permit/warn/block/escalate. The Transition Protocol in CLAUDE.md, the micro-engine verdicts, the hook responses, and the MCP tool outputs all use the same four terms with the same semantics.

### Fix 5: Cross-referenced memory locations
`viveka_memory_read` now searches both project-local (.viveka/memory/, .viveka/framework-memory/) and user-global (~/.viveka/traces/, ~/.viveka/policies/) locations. `viveka_session_state` returns the enforcement mode, posture, and computed-vs-overridden status.

---

## v2.0.0 — Unified product: cognitive + enforcement + tools

The cognitive plugin (v1.3) and the deterministic governance runtime (v0.5.0) are unified into a single Cursor plugin with three integration layers.

### Layer 2: Enforcement via hooks

The v0.5.0 `MicroDecisionEngine` is wired into Cursor hooks. Every tool call (`preToolUse`), shell command (`beforeShellExecution`), and file edit (`afterFileEdit`) passes through the deterministic rule engine. Verdicts: permit, warn, block, escalate. No LLM cost.

Session lifecycle hooks (`sessionStart`, `stop`) initialize and clean up governance state.

Hooks fail-open: if Python is not available, all actions proceed and the cognitive layer (Layer 1) still guides reasoning.

### Layer 3: MCP decision tools

Four tools exposed via MCP server:
- `viveka_check` — deterministic governance check for proposed actions
- `viveka_memory_read` — search .viveka/memory/ and .viveka/framework-memory/
- `viveka_memory_write` — persist task memory entries
- `viveka_session_state` — read current governance context

All local, all zero-cost, no external dependencies.

### Runtime bundled

The deterministic kernel from v0.5.0 is bundled in `runtime/viveka/` — models, micro-decision engine, environment scanner, context assessor. The LLM-dependent governance pipeline (Governor, option generation, stress testing) is not included — that reasoning happens in the agent's own model via the cognitive layer.

### Net effect (v2.0.0 vs v1.3)

| | v1.3 | v2.0.0 |
|---|---|---|
| Cognitive layer | yes | yes |
| Enforcement (hooks) | no | yes — deterministic micro-engine |
| Decision tools (MCP) | no | yes — 4 tools, all local |
| External dependencies | none | none |
| Graceful degradation | n/a | yes — Tier 1 (prompt-only) always works |

---

## v1.3 — Sub-agents + activation policy

The cognitive layer of v1.0–v1.2 becomes operational. Four sub-agents are added, gated by a type-driven activation policy that mirrors the Transition Protocol's decision gate.

### Four agent definitions in `agents/`

**viveka-code-agent** — coding work of meaningful size. Inter-agent contract preamble + viveka-code skill content + verification primitives + structured return schema. Hard rules: no writes outside change boundary; no auto-promotion to framework-memory; no return of raw output.

**viveka-research-agent** — substantial research. Source hierarchy + search strategy + confidence calibration (epistemic vs aleatory, propagation rule) + verification primitives + structured findings schema with per-claim confidence and counter-evidence trace. Hard rules: read-only by tool scoping; counter-evidence mandatory; inferences cannot be presented as facts.

**viveka-doc-review-agent** — long document review. Three-pass reading (skim → focus → critique). Four review levels (Health, Bugs, Coherence, Sufficiency). Verification primitives with audience-read and adversarial-read. Revision mode only when contract authorises. Hard rules: document loads into sub-agent context not parent's; voice preserved unless explicitly authorised.

**viveka-adversarial** — posture-driven adversarial review. Deepened review levels, mandatory threat model, mandatory kill case, hostile-input enumeration, no-residual-trust check. Tightened cost threshold (50% rather than 70%). Hard rules: demands threat model before starting; cannot omit kill case; severity is calibrated not negotiated; cannot modify artifact.

### CLAUDE.md — new AGENT ACTIVATION section

Four-state activation model: no agent (default) / auto-deploy (clear case) / ask first (gray case) / user-requested (always permitted). Session override memory, operating mode interaction, posture interaction, activation transparency, bounded sub-agent depth.

### Net effect (v1.3 vs v1.2)

| | v1.2 | v1.3 |
|---|---|---|
| Skills | 12 | 12 |
| Sub-agents | 0 | 4 (operational) |
| Activation policy | n/a | Four-state, type-driven, with session override |
| Audit trail records activations | n/a | yes |

---

## v1.2 — Tier 7 partial + Tier 8 Phase A

### Tier 7 — Posture diversity

Three declarable postures: exploratory, speed, adversarial. Three invariants that never relax (essence, irreversible-action gate, review). Switching constraint: max one per task without escalation.

### Tier 8 Phase A — Supervised self-modification

Five-stage pipeline: candidate generation → contradiction check → review queue → human approval → merge. No auto-promotion. Active rule versioning with expiry and rollback.

---

## v1.1 — Agentic-first operational completion

Built in dependency-ordered tiers. Each addition reduces a named failure mode.

### Tier 0 — Essence declared
### Tier 1 — Survival mechanics (operating modes, transition protocol, bounded loop-backs, sufficiency threshold, sub-agent verification, live review spec, time-bounded execution, cost-as-signal)
### Tier 2 — Continuity (memory read protocol, tool/connector environment, memory taxonomy, memory hygiene, framework-memory promotion, checkpoint/resume)
### Tier 3 — Quality without humans (verification primitives per output mode, confidence calibration, autonomous acceptance, stage audit trail)
### Tier 4 — Environment (absorbed into Tier 1-3)
### Tier 5 — New skills (viveka-decide, viveka-diagnose)
### Tier 6 — Self-modification (framework-memory candidate→active workflow)

---

## v1.0 — Initial release

Six-stage reasoning posture. Ten skills. Four platform targets. Operationally incomplete — relied on agent goodwill at decision points.
