"""
Layer 2: Satya — Task Context Assessment

Primarily deterministic. Combines environment invariants with
task context to assign a risk mode that governs the decision pipeline.
"""

from __future__ import annotations

from viveka.models.core import (
    Environment,
    EnvironmentState,
    Intent,
    QualityBar,
    Reversibility,
    RiskMode,
    TaskContext,
    Urgency,
)


def assess_context(
    task: str,
    intent: Intent = Intent.FEATURE,
    urgency: Urgency = Urgency.MEDIUM,
    reversibility: Reversibility = Reversibility.HIGH,
    quality_bar: QualityBar = QualityBar.PRODUCTION,
    **kwargs,
) -> TaskContext:
    """
    Construct task context from explicit parameters.

    No guessing. If a value isn't provided, it gets a safe default.
    Assumptions are declared, never silent.
    """
    assumptions = kwargs.pop("assumptions", [])
    if not kwargs.get("stated_intent"):
        assumptions.append("User intent inferred from task description")

    return TaskContext(
        task=task,
        intent=intent,
        urgency=urgency,
        reversibility=reversibility,
        quality_bar=quality_bar,
        assumptions=assumptions,
        **kwargs,
    )


def assign_risk_mode(
    environment: EnvironmentState,
    context: TaskContext,
) -> RiskMode:
    """
    Assign governance risk mode from invariants + context.

    This is the bridge between Layer 1 and Layer 2.
    Deterministic: same inputs always produce same mode.

    Risk mode determines how much autonomy the agent gets
    and how rigorous the evaluation pipeline is.
    """
    risk_score = 0.0

    # Environment factors
    if environment.environment == Environment.PRODUCTION:
        risk_score += 0.4
    elif environment.environment == Environment.STAGING:
        risk_score += 0.2

    if environment.git_state.get("is_protected_branch", False):
        risk_score += 0.2

    if environment.budget and environment.budget.fraction_used > 0.8:
        risk_score += 0.1

    # Context factors
    reversibility_weights = {
        Reversibility.HIGH: 0.0,
        Reversibility.MEDIUM: 0.1,
        Reversibility.LOW: 0.25,
        Reversibility.IRREVERSIBLE: 0.4,
    }
    risk_score += reversibility_weights.get(context.reversibility, 0.1)

    quality_weights = {
        QualityBar.PROTOTYPE: 0.0,
        QualityBar.DRAFT: 0.05,
        QualityBar.PRODUCTION: 0.2,
        QualityBar.CRITICAL: 0.3,
    }
    risk_score += quality_weights.get(context.quality_bar, 0.1)

    # Intent modifiers
    if context.intent == Intent.EXPLORATION:
        risk_score -= 0.15  # exploration should be freer
    elif context.intent == Intent.RECOVERY:
        risk_score += 0.1  # recovery needs caution

    # Urgency: high urgency slightly reduces governance overhead
    # (you need to act, but with awareness)
    if context.urgency == Urgency.CRITICAL:
        risk_score -= 0.05

    # Clamp
    risk_score = max(0.0, min(1.0, risk_score))

    # Map to enforcement mode
    if risk_score < 0.2:
        return RiskMode.PERMISSIVE
    elif risk_score < 0.45:
        return RiskMode.STANDARD
    elif risk_score < 0.7:
        return RiskMode.GUARDED
    else:
        return RiskMode.RESTRICTED


def get_governance_params(risk_mode: RiskMode) -> dict:
    """
    Return governance parameters for a given risk mode.

    These control how the evaluation and adversarial layers behave.
    max_retries is derived from micro._LIMITS — single source of truth.
    """
    from viveka.micro import _LIMITS

    _MACRO_PARAMS = {
        RiskMode.PERMISSIVE: {
            "max_options": 5,
            "min_options": 2,
            "adversarial_scenarios": 2,
            "survival_threshold": 0.4,
            "require_human_approval": False,
            "allow_assumptions": True,
        },
        RiskMode.STANDARD: {
            "max_options": 5,
            "min_options": 3,
            "adversarial_scenarios": 4,
            "survival_threshold": 0.6,
            "require_human_approval": False,
            "allow_assumptions": True,
        },
        RiskMode.GUARDED: {
            "max_options": 5,
            "min_options": 3,
            "adversarial_scenarios": 6,
            "survival_threshold": 0.7,
            "require_human_approval": False,
            "allow_assumptions": False,
        },
        RiskMode.RESTRICTED: {
            "max_options": 3,
            "min_options": 2,
            "adversarial_scenarios": 8,
            "survival_threshold": 0.8,
            "require_human_approval": True,
            "allow_assumptions": False,
        },
    }

    params = dict(_MACRO_PARAMS[risk_mode])
    params["max_retries"] = _LIMITS[risk_mode]["max_retries"]
    return params
