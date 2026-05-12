# Viveka — Changes log

## v2.0.0 (current) — Unified product: cognitive + enforcement + tools

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
