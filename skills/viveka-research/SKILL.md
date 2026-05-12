---
name: viveka-research
description: Research and analysis discipline. Covers source hierarchy, search strategy, evidence standards, calibrated confidence, and verification primitives.
---

# Research

## Source Hierarchy
1. **Primary:** original data, official docs, source code, published papers, government records.
2. **Authoritative secondary:** major publications, peer-reviewed analysis, domain experts.
3. **General secondary:** news, credible blog posts, community resources.
4. **Aggregators/forums:** Stack Overflow, Reddit. Signal, not citation.
5. **AI-generated:** high skepticism. Verify against primary sources.

When sources conflict, note the conflict and present both.

## Search Strategy
- Start broad, narrow based on findings.
- Follow citations backward — a good article's sources are often better.
- Check dates. 2020 info may be obsolete for fast-moving domains.
- Cross-reference claims across independent sources.
- Search for counter-evidence, not confirmation.

## Analysis
- **Separate layers:** facts (documented), inferences (logical), hypotheses (possible), opinions (judgment).
- Never blend inference with fact.

## Confidence Calibration

Confidence is not vibe — it is calibrated.

- *Epistemic vs aleatory.* Distinguish "I do not know" (epistemic, fixable with more research) from "the world is uncertain" (aleatory, cannot be fixed). Mark each separately.
- *Per-claim, not per-document.* In a long output, every load-bearing claim carries its own confidence. A report does not have one confidence — it has many.
- *Propagation rule.* An output cannot have higher confidence than its lowest-confidence load-bearing input. If a key fact is 60% confident, conclusions resting on it are at most 60%.
- *Name what would change it.* Every confidence statement should name the evidence that would raise or lower it. "70% confident, would rise to 90% if we had Q3 numbers from the regulator" is calibrated. "Probably true" is not.
- *Stop condition.* Does the user have enough to decide? If yes, stop. Offer to go deeper on specific threads. Do not chase confidence for its own sake.

## Verification Primitives (Before Delivery)

- *Primary-source spot-check.* For every load-bearing claim, has it been traced to a primary source? If not, mark it inference, not fact.
- *Counter-evidence check.* For the main conclusion, what would disprove it? Did you look?
- *Date check.* Are sources current enough for the domain's pace of change?
- *Citation integrity.* Do the cited sources actually say what you claim they say? (LLMs hallucinate citations more than facts.)
- *Confidence audit.* Is every load-bearing claim marked with its confidence and the evidence that would change it?

## Output
- **For decisions:** lead with recommendation, key evidence with confidence, risks, sources.
- **For exploration:** landscape of positions, where consensus exists and doesn't, surprises, confidence on each.
- **For fact-checking:** claim, evidence for/against, verdict with confidence, sources.
