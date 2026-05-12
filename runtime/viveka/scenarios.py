"""
Scenario Taxonomy & Filtering — Deterministic adversarial scenario system.

Extracted from v0.5.0 adversary.py + governor.py. No LLM calls.

Defines the 10 failure scenarios used in adversarial stress-testing,
plus deterministic scenario filtering that suppresses irrelevant
scenarios based on environment + context.

Usage:
    from viveka.scenarios import (
        SCENARIO_DESCRIPTIONS, DEFAULT_SCENARIOS,
        filter_scenarios_for_context,
    )

    # What failure modes apply to this risk level?
    scenarios = DEFAULT_SCENARIOS[RiskMode.STANDARD]

    # Filter for context — dev + reversible suppresses prod concerns
    active, suppression_log = filter_scenarios_for_context(
        scenarios, env_state, context,
    )
"""

from __future__ import annotations

from viveka.models.core import (
    Environment,
    EnvironmentState,
    Intent,
    Reversibility,
    RiskMode,
    Scenario,
    TaskContext,
)


SCENARIO_DESCRIPTIONS: dict[Scenario, str] = {
    Scenario.TOOL_FAILURE: (
        "A critical tool or API call fails mid-execution. "
        "The agent cannot complete the step it planned."
    ),
    Scenario.STALE_CONTEXT: (
        "The information the strategy relies on is outdated. "
        "A file was modified, a dependency updated, or state changed since planning."
    ),
    Scenario.CONFLICTING_INSTRUCTION: (
        "The user's stated intent and actual need diverge. "
        "The strategy optimizes for what was asked, not what was needed."
    ),
    Scenario.DECEPTIVE_COMPLETION: (
        "The action appears to succeed but hasn't actually solved the problem. "
        "Tests pass but the fix is superficial. The build succeeds but behavior is wrong."
    ),
    Scenario.HIDDEN_DEPENDENCY: (
        "The strategy doesn't account for a dependency that will break. "
        "A downstream system, an import, a shared config, or a lock file is affected."
    ),
    Scenario.MISSING_DATA: (
        "A key piece of information needed for the strategy is unavailable. "
        "A file doesn't exist, an API returns empty, or context is incomplete."
    ),
    Scenario.TIME_PRESSURE: (
        "The token budget or time limit is hit before the strategy completes. "
        "The agent must produce partial results or abandon the approach."
    ),
    Scenario.IRREVERSIBLE_ACTION: (
        "The strategy includes a step that cannot be undone. "
        "Data deletion, external API calls with side effects, or published changes."
    ),
    Scenario.CASCADING_FAILURE: (
        "The strategy's failure triggers failures in dependent systems. "
        "Breaking a shared module, corrupting shared state, or blocking other agents."
    ),
    Scenario.PERMISSION_ESCALATION: (
        "The strategy requires permissions it doesn't have. "
        "It attempts to access restricted files, APIs, or environments."
    ),
}


DEFAULT_SCENARIOS: dict[RiskMode, list[Scenario]] = {
    RiskMode.PERMISSIVE: [
        Scenario.TOOL_FAILURE,
        Scenario.MISSING_DATA,
    ],
    RiskMode.STANDARD: [
        Scenario.TOOL_FAILURE,
        Scenario.STALE_CONTEXT,
        Scenario.DECEPTIVE_COMPLETION,
        Scenario.HIDDEN_DEPENDENCY,
    ],
    RiskMode.GUARDED: [
        Scenario.TOOL_FAILURE,
        Scenario.STALE_CONTEXT,
        Scenario.DECEPTIVE_COMPLETION,
        Scenario.HIDDEN_DEPENDENCY,
        Scenario.CONFLICTING_INSTRUCTION,
        Scenario.CASCADING_FAILURE,
    ],
    RiskMode.RESTRICTED: [
        Scenario.TOOL_FAILURE,
        Scenario.STALE_CONTEXT,
        Scenario.DECEPTIVE_COMPLETION,
        Scenario.HIDDEN_DEPENDENCY,
        Scenario.CONFLICTING_INSTRUCTION,
        Scenario.CASCADING_FAILURE,
        Scenario.IRREVERSIBLE_ACTION,
        Scenario.PERMISSION_ESCALATION,
    ],
}

SCENARIO_SUPPRESSION_RULES: list[dict] = [
    {
        "condition": lambda env, ctx: (
            env.environment == Environment.DEVELOPMENT
            and ctx.reversibility in (Reversibility.HIGH, Reversibility.MEDIUM)
        ),
        "suppress": [
            Scenario.IRREVERSIBLE_ACTION,
            Scenario.CASCADING_FAILURE,
            Scenario.PERMISSION_ESCALATION,
        ],
        "reason": (
            "Development environment with reversible actions — "
            "deployment, cascading production failures, and permission escalation "
            "scenarios are out of scope"
        ),
    },
    {
        "condition": lambda env, ctx: ctx.intent == Intent.EXPLORATION,
        "suppress": [
            Scenario.CASCADING_FAILURE,
            Scenario.IRREVERSIBLE_ACTION,
            Scenario.PERMISSION_ESCALATION,
            Scenario.STALE_CONTEXT,
        ],
        "reason": (
            "Exploration intent — production stability scenarios "
            "are not applicable to spikes/prototypes"
        ),
    },
]


def filter_scenarios_for_context(
    scenarios: list[Scenario],
    env_state: EnvironmentState,
    context: TaskContext,
) -> tuple[list[Scenario], list[dict]]:
    """
    Filter adversarial scenarios based on environment + context.
    Returns: (active_scenarios, suppression_log)
    Deterministic — no LLM involvement.
    """
    suppressed: set[Scenario] = set()
    suppression_log: list[dict] = []

    for rule in SCENARIO_SUPPRESSION_RULES:
        if rule["condition"](env_state, context):
            newly_suppressed = [s for s in rule["suppress"] if s in scenarios]
            if newly_suppressed:
                suppressed.update(newly_suppressed)
                suppression_log.append({
                    "suppressed": [s.value for s in newly_suppressed],
                    "reason": rule["reason"],
                })

    active = [s for s in scenarios if s not in suppressed]

    if not active:
        active = [Scenario.TOOL_FAILURE]
        suppression_log.append({
            "suppressed": [],
            "reason": "Safety floor: retained TOOL_FAILURE as minimum scenario",
        })

    return active, suppression_log


def get_applicable_scenarios(
    risk_mode: RiskMode,
    env_state: EnvironmentState | None = None,
    context: TaskContext | None = None,
) -> tuple[list[Scenario], list[dict]]:
    """
    Convenience: get scenarios for a risk mode, optionally filtered by context.
    Returns: (scenarios, suppression_log)
    """
    raw = DEFAULT_SCENARIOS.get(risk_mode, DEFAULT_SCENARIOS[RiskMode.STANDARD])
    if env_state and context:
        return filter_scenarios_for_context(raw, env_state, context)
    return raw, []


def scenario_to_constraint(scenario: Scenario) -> str:
    """Convert a scenario to the constraint any viable approach must satisfy."""
    _MAP = {
        Scenario.TOOL_FAILURE: (
            "Must have fallback mechanisms when tools or APIs fail mid-execution"
        ),
        Scenario.STALE_CONTEXT: (
            "Must not depend on assumptions about current system state without verification"
        ),
        Scenario.CONFLICTING_INSTRUCTION: (
            "Must address the actual need, not just the stated request"
        ),
        Scenario.DECEPTIVE_COMPLETION: (
            "Must validate that the solution genuinely solves the problem, "
            "not just produces passing signals"
        ),
        Scenario.HIDDEN_DEPENDENCY: (
            "Must account for dependencies not visible through static analysis "
            "or standard code inspection"
        ),
        Scenario.MISSING_DATA: (
            "Must handle incomplete information gracefully rather than "
            "assuming availability"
        ),
        Scenario.TIME_PRESSURE: (
            "Must produce usable partial results if interrupted before completion"
        ),
        Scenario.IRREVERSIBLE_ACTION: (
            "Must not include steps that cannot be undone without explicit safeguards"
        ),
        Scenario.CASCADING_FAILURE: (
            "Must isolate changes to prevent failure from propagating to dependent systems"
        ),
        Scenario.PERMISSION_ESCALATION: (
            "Must operate within available permissions without requiring elevated access"
        ),
    }
    return _MAP.get(scenario, f"Must handle {scenario.value} scenarios")
