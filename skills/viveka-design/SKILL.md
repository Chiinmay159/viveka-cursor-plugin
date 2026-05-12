---
name: viveka-design
description: Visual and UX execution discipline. Use when the output has a visual or experiential dimension. Covers aesthetics, accessibility, responsiveness, and verification primitives.
---

# Design

Aesthetics is structural, not decorative. Architecture splits it across two layers: **foundational aesthetics** (Layer 2, Foundation) — typography, scale, palette, spacing tokens, brand grammar — and **surface aesthetics** (Layer 6) — microcopy, motion, finishing. Foundation constrains what surface can do.

## Before Designing
- What is the essence? A dashboard's essence is decision support. A landing page's is conversion.
- Who is the viewer/user? Desktop, mobile, print, projected?
- What design system exists? If none, establish minimum tokens (this is foundational aesthetics, Layer 2): typeface, scale, palette, spacing, radius.
- What constraints? Brand guidelines, accessibility requirements, platform limitations, breakpoints?

## While Designing
- **Hierarchy** through size, weight, and position — not decoration.
- **Whitespace** as structure, not leftover space.
- **Grid alignment.** Inconsistency reads as careless.
- **Limited palette.** 3 colours with purpose > 12 without system.
- **Accessibility:** WCAG AA contrast (4.5:1 body, 3:1 large). No colour-only information. Visible focus states. Resizable text. Alt text for informational images.
- **Responsiveness:** primary viewport first, then adapt. Touch targets 44×44pt minimum. Do not hide critical content behind hover states on mobile.
- **Copywriting is design** (this is surface aesthetics, Layer 6). Button labels, error messages, empty states, tooltips. Be specific: "Save changes" not "Submit." Error messages say what went wrong and what to do.
- **Creativity within constraints.** Constraints enable distinctiveness. Surprise once per piece. Reference patterns (users have expectations) without copying.

## Verification Primitives (After Designing)

Visual outputs have measurable acceptance criteria. Use them.

- *View at actual size on the target device.* Most design failures are scale failures only visible at 1:1.
- *Contrast check.* Run actual numbers against WCAG AA. Do not eyeball.
- *Focus and keyboard pass.* Tab through every interactive element. Visible focus, logical order, no traps.
- *Responsive sweep.* Check at every key breakpoint, not just the primary.
- *Read all text in context and sequence.* Every label, every error, every empty state.
- *Essence elicitation check.* Does this honour the essence? A dashboard that looks beautiful but doesn't support decisions has failed its essence with zero bugs.
- *Adversarial read.* Where will a confused, hurried, or disabled user fail? Trace those paths.

Evidence, not assertion. "Looks good" is not verification — "passes contrast at 4.7:1, focus order matches reading order, breakpoints render cleanly at 320/768/1280" is.
