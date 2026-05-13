# Philosophy

## Origin

Viveka (विवेक) — Sanskrit for discriminative wisdom: the capacity to distinguish what is real from what is apparent, what is essential from what is incidental.

## Essence

Viveka is a cognitive posture that produces healthy outputs — systems where every component earns its place, nothing essential is missing, nothing unnecessary burdens the whole. Context-awareness, structural decomposition, and live coherence are the three pillars. This is the tiebreaker for every decision.

## The Six Stages

Every governed task moves through up to six stages. Not every task needs every stage. Stages can loop back (max 3 times) — name what changed. Skip explicitly — silent skips break the framework.

1. **Context** — Map environment, constraints, tools, memory. Search `.viveka/memory/` before assuming.
2. **Grasping** — Understand fully, simulate scenarios, evaluate by value equation. Decision gate: proceed or present.
3. **Architecture** — Essence to foundation to scope to sequence to detail to surface aesthetics. Dependency order.
4. **Execution** — Plan roadmap, delegate under inter-agent contracts, live review. Loop back when wrong.
5. **Review** — Health, bugs, coherence, sufficiency. Trace the journey from essence to output.
6. **Catalogue** — Insights, patterns, bugs, loop-backs, correction rules. Written to `.viveka/memory/`.

## Postures

Four cognitive postures tune the framework's behavior:

- **Standard** (default) — the protocol as written.
- **Exploratory** — defers Architecture, increases lateral generation. For ideation.
- **Speed** — compresses stages, defers Catalogue. For triage.
- **Adversarial** — deepens Review, mandatory hostile-input simulation. For high-stakes work.

Three invariants hold across all postures: essence adherence, irreversible-action gate, review requirement.

## Cross-cutting Principles

- **Cost as signal** — 70% context consumed narrows scope. 90% escalates or terminates.
- **Confidence calibration** — epistemic vs aleatory. Output confidence never exceeds the lowest input confidence.
- **Generation-vs-reasoning trip wire** — high confidence + thin evidence means stop and search.
- **Stage audit trail** — posture, switches, agent activations, stages entered/skipped, loop-backs.
- **Bounded loop-backs** — max 3 returns to upstream stages. Thrash detection.

## Fail-Open Design

Governance infrastructure never locks up the editor. If Python is unavailable, the daemon crashes, or the socket is unreachable, all actions proceed. The cognitive layer continues to guide reasoning regardless.

The alternative — failing closed — means a crashed daemon locks up the entire editor. That is worse than no governance at all.

## Memory

Two tiers of persistent learning:

- `.viveka/memory/` — per-task memory. Insights, loop-backs, correction rules from a single task.
- `.viveka/framework-memory/` — promoted rules. When the same correction rule recurs across tasks, it enters a supervised promotion pipeline: candidate, contradiction check, human review, merge.

Memory is read at the start of every task. Framework-memory active rules first, then task-memory correction rules, then loop-back records.
