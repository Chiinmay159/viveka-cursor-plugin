"""
Viveka Runtime — Deterministic decision governance kernel.

This is the enforcement layer. No LLM calls. No external dependencies.
The micro-decision engine handles ~80% of agent decisions in milliseconds.

Modules:
    micro         — MicroDecisionEngine (7 rule categories, 4 verdicts)
    policies      — PolicyPack system (5 built-in governance profiles)
    constraints   — Deterministic constraint validation
    scenarios     — Failure scenario taxonomy + context filtering
    readiness     — Task readiness assessment from failure data
    contracts     — StageContract, GovernedToolkit (pure stage-contract gate)
    session       — GovernedSession (micro→macro bridge, trace export)
    harness/      — Agent-agnostic test & comparison framework
"""

from viveka.models.core import (
    Environment,
    EnvironmentState,
    Intent,
    Permissions,
    Reversibility,
    RiskMode,
    Scenario,
    TaskContext,
    TokenBudget,
    Urgency,
)
from viveka.micro import MicroDecisionEngine, MicroDecision, Verdict, SessionState
from viveka.layers.scanner import scan_environment, check_invariant_violations
from viveka.layers.assessor import assess_context, assign_risk_mode
from viveka.policies import PolicyPack, BUILTIN_PACKS, get_policy, merge_policies

__version__ = "3.0.0"
