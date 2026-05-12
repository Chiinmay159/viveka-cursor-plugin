---
name: viveka-architect
description: Six-layer structural decomposition for compound outputs. Use before building anything complex. Layers: essence, foundation, scope, sequence, detail, surface aesthetics.
---

# Architect

Design the structure before building. Applies to code, content, plans, analysis — any compound output.

## The Six Layers
Each constrains the next. Define top-down.

### 1. Essence
What is the soul of this thing? Not what it does — what it is. State in one sentence. If you cannot, return to Grasping.
- An invoice's essence is a promise of payment. A login page's is trust. An API's is a contract.

### 2. Foundation
What must be in place for everything else to work? Data model, invariants, security model, evidence base, core abstractions. For visual outputs, foundational aesthetics belong here — typography, scale, palette, spacing tokens, brand grammar. These are decisions you cannot change later without rebuilding everything above.

### 3. Scope
What is in and what is out? Name both explicitly, including why exclusions are excluded. Undefined scope causes overbuilding.

### 4. Sequence
Components and their ideal order. Map the dependency graph — build in dependency order, not importance order. If a later component replaces an earlier one, do not build the earlier one. Tag transient fixes explicitly with retirement points.

### 5. Detail
Depth per component, proportional to essence. Critical security functions get 50 lines. Utility helpers get 5. Not uniform — proportional.

### 6. Surface Aesthetics
The final layer applied after everything below is sound. Naming, microcopy, error messages, motion, finishing, copywriting. Not decoration — the visible surface that elicits experience. Foundational aesthetics decisions (Layer 2) constrain what Layer 6 can do; surface aesthetics never override foundation.

## Search Protocol
Search for reference implementations, existing patterns, and validate foundation against tech stack.

## Output
The architecture becomes the spec that Execution and Review check against. Concrete enough that a sub-agent knows exactly what to build, a live reviewer can check conformance, and Review can trace coherence.
