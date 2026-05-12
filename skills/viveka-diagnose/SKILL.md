---
name: viveka-diagnose
description: Debugging and root-cause analysis for failing systems. Use for incident triage, defect isolation, hypothesis testing, and evidence-driven remediation.
---

# Diagnose

Find root cause with evidence, then define the narrowest reliable fix.

## Intake
- Symptom statement.
- Expected behavior vs observed behavior.
- Blast radius and severity.
- Recent changes and timeline.

## Hypothesis Workflow
1. Generate candidate causes ranked by likelihood and impact.
2. Design eliminative tests that distinguish candidates.
3. Run one test at a time and record outcomes.
4. Update posterior ranking after each test.
5. Stop when one cause explains all critical symptoms better than alternatives.

## Guardrails
- Prefer high-signal evidence over intuition.
- Avoid simultaneous multi-change fixes during diagnosis.
- Mark unknowns explicitly instead of filling with guesswork.
- If evidence plateaus, broaden Context and revisit assumptions.

## Output Format
- Root cause statement.
- Evidence chain.
- Fix recommendation.
- Regression risks.
- Verification plan to confirm resolution.
