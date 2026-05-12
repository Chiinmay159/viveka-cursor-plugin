---
name: viveka-decide
description: Decision support without artifact production. Use when the user needs to choose between options. Covers framing, criteria, sensitivity analysis, and recommendation.
---

# Decide

Help the user make a decision well. The output is reasoning plus a recommendation — not an artifact.

## Before Deciding

- **Frame the decision.** What is the actual choice? What is the underlying goal the choice serves? A poorly framed decision cannot be decided well.
- **Reversibility check.** Is this a one-way door (irreversible, decide carefully) or a two-way door (reversible, decide quickly)? Calibrate effort accordingly.
- **Owner check.** Whose decision is this? If it is not the user's to make, surface that before evaluating options.

## Option Generation

- **Avoid the false binary.** If the user presents two options, generate at least one more — even if to reject it. Binary framings hide alternatives.
- **Include the null option.** "Do nothing" or "delay" is always an option. Evaluate it explicitly.
- **Structurally different options.** Two variants of the same approach are one option, not two.

## Criteria

- **Name what matters.** What does a good outcome look like? Cost, speed, reversibility, optionality, risk, fit, strategic alignment — pick the criteria that actually apply.
- **Weight them.** Equal weighting is rarely accurate. Force the user (or yourself) to rank.
- **Hard vs soft.** Some criteria are hard constraints (violating disqualifies an option). Others are soft preferences. Distinguish.

## Evaluation

For each option against each criterion:

- *Score with evidence,* not vibe. Cite the evidence behind each score.
- *Confidence per score.* See viveka-research's calibration. Some scores are well-known; others are guesses. Mark which.
- *Failure modes.* For each option, what is the worst-case outcome and how likely?

## Sensitivity Analysis

The single most useful step. Ask: what would have to change for the recommendation to flip?

- *Weight sensitivity.* If criterion X were weighted higher, would the answer change?
- *Score sensitivity.* If your most uncertain score is wrong, does the answer hold?
- *Robustness.* A recommendation that flips under modest changes is fragile — say so.

## Recommendation

State plainly:

- *The recommendation.* One sentence.
- *Why this over the others.* The two or three decisive factors.
- *Confidence,* with what would change it.
- *Conditions.* Under what conditions the recommendation holds. Under what conditions it does not.
- *Reversal triggers.* What signals, if observed later, should prompt reconsidering.

## Verification Primitives

Decisions cannot be tested before they are made. Use these instead:

- *Pre-mortem.* Imagine the recommendation has failed. What is the most likely cause? If the answer is foreseeable, address it now.
- *Inversion check.* What is the strongest case for the option you did not recommend? If you cannot make that case strongly, you have not understood the trade-off.
- *Stakes check.* Are the stakes proportionate to the analysis depth? Under-analysing a high-stakes decision is the same failure mode as over-analysing a low-stakes one.

## When to Loop Back

- → Grasp if option generation reveals the underlying need was misframed.
- → Context if a criterion you thought was hard turns out to be soft, or vice versa.

## Output

A written recommendation with the structure above. No deliverable beyond the reasoning itself. The user acts on the recommendation; viveka-decide does not act for them.
