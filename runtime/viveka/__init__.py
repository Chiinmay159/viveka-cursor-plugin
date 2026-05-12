"""
Viveka Runtime — Deterministic decision governance kernel.

This is the enforcement layer. No LLM calls. No external dependencies.
The micro-decision engine handles ~80% of agent decisions in milliseconds.
"""

from viveka.models.core import (
    Environment,
    EnvironmentState,
    Intent,
    Permissions,
    Reversibility,
    RiskMode,
    TaskContext,
    TokenBudget,
    Urgency,
)
from viveka.micro import MicroDecisionEngine, MicroDecision, Verdict, SessionState
from viveka.layers.scanner import scan_environment, check_invariant_violations
from viveka.layers.assessor import assess_context, assign_risk_mode

__version__ = "2.0.0"
