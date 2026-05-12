"""
Readiness Assessment — Deterministic "is this task ready for execution?"

Extracted from v0.5.0 synthesizer.py. No LLM calls.

Given structured failure data (stress test results), produces:
- ReadinessLevel (ready / caution / bounded / not_ready / blocked)
- FailureLessons (constraints extracted from adversarial failures)
- Dominant failure modes
- Viability constraints

This is the "from failure to guidance" engine. All deterministic.

Usage:
    from viveka.readiness import assess_readiness, extract_failure_lessons

    readiness, reason, boundary = assess_readiness(stress_results)
    lessons = extract_failure_lessons(stress_results)
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field

from viveka.models.core import Scenario, StressTestResult
from viveka.scenarios import scenario_to_constraint


class ReadinessLevel(str, Enum):
    READY = "ready"
    READY_WITH_CAUTION = "caution"
    READY_WITH_BOUNDARY = "bounded"
    NOT_READY = "not_ready"
    BLOCKED = "blocked"


@dataclass
class FailureLesson:
    constraint: str
    source_scenarios: list[Scenario] = field(default_factory=list)
    violated_by: list[str] = field(default_factory=list)
    severity: str = "high"


@dataclass
class ReadinessResult:
    level: ReadinessLevel
    reason: str
    boundary_statement: str = ""
    failure_lessons: list[FailureLesson] = field(default_factory=list)
    constraints_for_viability: list[str] = field(default_factory=list)
    dominant_failure_scenarios: list[Scenario] = field(default_factory=list)
    suppressed_scenarios: list[str] = field(default_factory=list)


def extract_failure_lessons(
    stress_results: list[StressTestResult],
) -> list[FailureLesson]:
    """
    Extract constraints from adversarial failures.
    Deterministic — analyzes failure patterns across options.
    """
    scenario_failures: dict[Scenario, list[dict]] = {}

    for result in stress_results:
        if result.option is None:
            continue
        for sr in result.scenario_results:
            if not sr.survived:
                if sr.scenario not in scenario_failures:
                    scenario_failures[sr.scenario] = []
                scenario_failures[sr.scenario].append({
                    "option_id": result.option.option.id,
                    "degradation": sr.degradation,
                    "failure_mode": sr.failure_mode,
                })

    lessons = []

    for scenario, failures in scenario_failures.items():
        if len(failures) >= 2:
            option_ids = [f["option_id"] for f in failures]
            avg_degradation = sum(f["degradation"] for f in failures) / len(failures)
            severity = (
                "critical" if avg_degradation >= 0.8
                else "high" if avg_degradation >= 0.6
                else "medium"
            )
            lessons.append(FailureLesson(
                constraint=scenario_to_constraint(scenario),
                source_scenarios=[scenario],
                violated_by=option_ids,
                severity=severity,
            ))

    severity_order = {"critical": 0, "high": 1, "medium": 2}
    lessons.sort(key=lambda x: severity_order.get(x.severity, 3))
    return lessons


def _find_dominant_failure_scenarios(
    stress_results: list[StressTestResult],
) -> list[Scenario]:
    """Find scenarios that killed the most options with highest degradation."""
    scenario_impact: dict[Scenario, float] = {}

    for result in stress_results:
        for sr in result.scenario_results:
            if not sr.survived:
                if sr.scenario not in scenario_impact:
                    scenario_impact[sr.scenario] = 0.0
                scenario_impact[sr.scenario] += sr.degradation

    sorted_scenarios = sorted(
        scenario_impact.items(),
        key=lambda x: x[1],
        reverse=True,
    )
    return [s[0] for s in sorted_scenarios]


def assess_readiness(
    stress_results: list[StressTestResult],
    survival_threshold: float = 0.6,
    suppression_log: list[dict] | None = None,
) -> ReadinessResult:
    """
    Full readiness assessment from stress test data.
    Deterministic — based on survival data and failure patterns.
    """
    if not stress_results:
        return ReadinessResult(
            level=ReadinessLevel.BLOCKED,
            reason="No options were evaluated",
        )

    survivors = [
        r for r in stress_results
        if r.resilience_score >= survival_threshold
    ]
    has_suppressed = bool(suppression_log)
    failure_lessons = extract_failure_lessons(stress_results)
    constraints = [lesson.constraint for lesson in failure_lessons]
    dominant = _find_dominant_failure_scenarios(stress_results)

    suppressed_reasons = [
        entry.get("reason", "") for entry in (suppression_log or [])
    ]

    if survivors:
        best_resilience = max(r.resilience_score for r in survivors)

        if has_suppressed:
            boundary = (
                f"Achievable within declared scope. "
                f"Suppressed scenarios: {'; '.join(suppressed_reasons)}. "
                f"Guarantees DO NOT extend beyond the declared "
                f"environment/reversibility context."
            )
            return ReadinessResult(
                level=ReadinessLevel.READY_WITH_BOUNDARY,
                reason=(
                    f"Survivor with {best_resilience:.0%} resilience within scoped "
                    f"adversarial testing (some scenarios suppressed for context)"
                ),
                boundary_statement=boundary,
                failure_lessons=failure_lessons,
                constraints_for_viability=constraints,
                dominant_failure_scenarios=dominant,
                suppressed_scenarios=suppressed_reasons,
            )

        level = (
            ReadinessLevel.READY if best_resilience >= 0.8
            else ReadinessLevel.READY_WITH_CAUTION
        )
        return ReadinessResult(
            level=level,
            reason=(
                f"{'Strong survivor' if best_resilience >= 0.8 else 'Best survivor'} "
                f"with {best_resilience:.0%} resilience"
                + ("" if best_resilience >= 0.8 else " — proceed with monitoring")
            ),
            failure_lessons=failure_lessons,
            constraints_for_viability=constraints,
            dominant_failure_scenarios=dominant,
        )

    best_resilience = max(r.resilience_score for r in stress_results)

    if best_resilience == 0.0:
        return ReadinessResult(
            level=ReadinessLevel.BLOCKED,
            reason=(
                "All options failed all adversarial scenarios — "
                "task cannot be safely executed without fundamentally different approach"
            ),
            failure_lessons=failure_lessons,
            constraints_for_viability=constraints,
            dominant_failure_scenarios=dominant,
        )

    failure_names = ", ".join(s.value for s in dominant[:3])
    return ReadinessResult(
        level=ReadinessLevel.NOT_READY,
        reason=(
            f"No option survived adversarial testing. "
            f"Dominant failure modes: {failure_names}. "
            f"Evidence gathering required before execution."
        ),
        failure_lessons=failure_lessons,
        constraints_for_viability=constraints,
        dominant_failure_scenarios=dominant,
    )
