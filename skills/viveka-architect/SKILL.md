---
name: viveka-architect
description: Six-layer structural decomposition for compound outputs. Use before building anything complex — code, documents, plans, designs. Decomposes into essence, foundation, scope, sequence, detail, aesthetics. Ensures dependency-correct build order.
---

# Architect

Design the structure before building. Applies to code, content, plans, analysis — any compound output.

## The Six Layers
Each constrains the next. Define top-down.

### 1. Essence
What is the soul of this thing? Not what it does — what it is. State in one sentence. If you cannot, return to Grasping.
- An invoice's essence is a promise of payment. A login page's is trust. An API's is a contract.

### 2. Foundation
What must be in place for everything else to work? Data model, invariants, security model, evidence base, core abstractions. This is what you cannot change later without rebuilding everything above.

### 3. Scope
What is in and what is out? Name both explicitly, including why exclusions are excluded. Undefined scope causes overbuilding.

### 4. Sequence
Components and their ideal order. Map the dependency graph — build in dependency order, not importance order. If a later component replaces an earlier one, do not build the earlier one. Tag transient fixes explicitly with retirement points.

### 5. Detail
Depth per component, proportional to essence. Critical security functions get 50 lines. Utility helpers get 5. Not uniform — proportional.

### 6. Aesthetics
Surfaces that elicit experience. Naming, documentation, error messages, visual grammar, accessibility, responsiveness, copywriting. Not decoration — the final layer of architecture. Can only be done right after everything below is sound.

## Search Protocol
Search for reference implementations, existing patterns, and validate foundation against tech stack.

## Output
The architecture becomes the spec that Execution and Review check against. Concrete enough that a sub-agent knows exactly what to build, a live reviewer can check conformance, and Review can trace coherence.
