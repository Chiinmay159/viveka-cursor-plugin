"""
Core data models for Viveka decision governance.

Three layers + adversarial selection:
    Layer 1 (Ruta): Environment invariants — what is real
    Layer 2 (Satya): Task context — what is true here
    Layer 3 (ALU): Decision evaluation — what are options worth
    Selection: Adversarial filtering — what survives perturbation
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────


class Environment(str, Enum):
    """Deployment environment classification."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Urgency(str, Enum):
    """Task urgency levels."""
    LOW = "low"            # exploration, improvement
    MEDIUM = "medium"      # standard work
    HIGH = "high"          # deadline-driven
    CRITICAL = "critical"  # incident response


class Reversibility(str, Enum):
    """How reversible is the action?"""
    HIGH = "high"          # git revert, feature flag, undo available
    MEDIUM = "medium"      # rollback possible but costly
    LOW = "low"            # partial rollback, data loss risk
    IRREVERSIBLE = "irreversible"  # cannot undo (delete, publish, deploy)


class QualityBar(str, Enum):
    """Expected quality standard."""
    PROTOTYPE = "prototype"
    DRAFT = "draft"
    PRODUCTION = "production"
    CRITICAL = "critical"  # safety-critical, financial, etc.


class Intent(str, Enum):
    """What the user is trying to accomplish."""
    FIX = "fix"                    # bug fix, error correction
    IMPROVEMENT = "improvement"    # refactor, optimization
    FEATURE = "feature"            # new functionality
    EXPLORATION = "exploration"    # research, spike, prototype
    MAINTENANCE = "maintenance"    # dependency update, cleanup
    RECOVERY = "recovery"          # incident response, rollback


class RiskMode(str, Enum):
    """Enforcement mode assigned based on invariants + context.

    Named to avoid collision with cognitive postures (Standard, Exploratory,
    Speed, Adversarial). Postures shape reasoning depth; enforcement modes
    shape action latitude.
    """
    PERMISSIVE = "permissive"        # maximum latitude, minimal constraints
    STANDARD = "standard"            # default governance
    GUARDED = "guarded"              # elevated scrutiny
    RESTRICTED = "restricted"        # minimal autonomy, human approval required


class Scenario(str, Enum):
    """Adversarial scenarios for stress-testing options."""
    TOOL_FAILURE = "tool_failure"
    STALE_CONTEXT = "stale_context"
    CONFLICTING_INSTRUCTION = "conflicting_instruction"
    DECEPTIVE_COMPLETION = "deceptive_completion"
    HIDDEN_DEPENDENCY = "hidden_dependency"
    MISSING_DATA = "missing_data"
    TIME_PRESSURE = "time_pressure"
    IRREVERSIBLE_ACTION = "irreversible_action"
    CASCADING_FAILURE = "cascading_failure"
    PERMISSION_ESCALATION = "permission_escalation"


# ──────────────────────────────────────────────
# Layer 1: Environment Invariants (Ruta)
# ──────────────────────────────────────────────


class TokenBudget(BaseModel):
    """Token budget constraints."""
    max_tokens: int = Field(description="Maximum tokens for this task")
    used_tokens: int = Field(default=0, description="Tokens consumed so far")
    warn_at: float = Field(default=0.8, description="Warning threshold (fraction)")

    @property
    def remaining(self) -> int:
        return self.max_tokens - self.used_tokens

    @property
    def fraction_used(self) -> float:
        return self.used_tokens / self.max_tokens if self.max_tokens > 0 else 1.0


class Permissions(BaseModel):
    """What the agent is allowed to do."""
    can_write_files: bool = True
    can_execute_commands: bool = True
    can_access_network: bool = True
    can_modify_git: bool = True
    can_access_secrets: bool = False
    can_deploy: bool = False
    writable_paths: list[str] = Field(default_factory=list)
    blocked_paths: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)


class EnvironmentState(BaseModel):
    """
    Layer 1: Ruta — the immutable realities of the operating environment.

    These are facts, not preferences. Any option that violates an invariant
    is eliminated before evaluation begins.
    """
    environment: Environment = Environment.DEVELOPMENT
    permissions: Permissions = Field(default_factory=Permissions)
    budget: TokenBudget | None = None
    git_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Branch, dirty files, protection rules"
    )
    ci_status: str | None = Field(
        default=None,
        description="Current CI/CD pipeline status"
    )
    available_tools: list[str] = Field(
        default_factory=list,
        description="Tools/APIs currently available"
    )
    rate_limits: dict[str, Any] = Field(
        default_factory=dict,
        description="Current rate limit state for APIs"
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional environment-specific hard constraints"
    )
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def violates(self, action: str) -> list[str]:
        """Return list of invariant violations for a proposed action. Empty = safe."""
        violations = []
        if self.budget and self.budget.remaining <= 0:
            violations.append("token_budget_exhausted")
        if self.environment == Environment.PRODUCTION and not self.permissions.can_deploy:
            if "deploy" in action.lower():
                violations.append("no_deploy_permission_in_production")
        return violations


# ──────────────────────────────────────────────
# Layer 2: Task Context (Satya)
# ──────────────────────────────────────────────


class TaskContext(BaseModel):
    """
    Layer 2: Satya — the subjective, local truth of this specific task.

    Context shapes which options are coherent. An exploratory refactor
    and a production hotfix exist in different decision universes.
    """
    task: str = Field(description="What needs to be done")
    intent: Intent = Intent.FEATURE
    urgency: Urgency = Urgency.MEDIUM
    reversibility: Reversibility = Reversibility.HIGH
    quality_bar: QualityBar = QualityBar.PRODUCTION
    stated_intent: str = Field(
        default="",
        description="What the user explicitly asked for"
    )
    inferred_intent: str = Field(
        default="",
        description="What the user likely needs (may differ from stated)"
    )
    session_history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Prior decisions in this session"
    )
    known_constraints: list[str] = Field(
        default_factory=list,
        description="Constraints the user has specified"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made — must be declared, never silent"
    )


# ──────────────────────────────────────────────
# Layer 3: Decision Evaluation (ALU)
# ──────────────────────────────────────────────


class ALUScores(BaseModel):
    """
    Accountability — Liability — Utility scoring matrix,
    extended with Reversibility and Uncertainty.
    """
    utility: float = Field(ge=0.0, le=1.0, description="Expected benefit")
    liability: float = Field(ge=0.0, le=1.0, description="What can go wrong")
    accountability: float = Field(ge=0.0, le=1.0, description="Traceability / explainability")
    reversibility: float = Field(ge=0.0, le=1.0, description="Can we undo this")
    uncertainty: float = Field(ge=0.0, le=1.0, description="Unknowns remaining")

    def weighted_score(self, weights: dict[str, float] | None = None) -> float:
        """
        Compute composite score. Higher is better.
        Liability and uncertainty are inverted (lower raw = better).
        """
        w = weights or {
            "utility": 0.30,
            "liability": 0.25,
            "accountability": 0.15,
            "reversibility": 0.20,
            "uncertainty": 0.10,
        }
        return (
            w.get("utility", 0) * self.utility
            + w.get("liability", 0) * (1.0 - self.liability)
            + w.get("accountability", 0) * self.accountability
            + w.get("reversibility", 0) * self.reversibility
            + w.get("uncertainty", 0) * (1.0 - self.uncertainty)
        )


class Option(BaseModel):
    """A candidate strategy (not output — strategy)."""
    id: str = Field(description="Unique identifier")
    description: str = Field(description="What this option does")
    strategy: str = Field(description="How it accomplishes the task")
    preconditions: list[str] = Field(
        default_factory=list,
        description="What must be true for this to work"
    )
    risks: list[str] = Field(
        default_factory=list,
        description="Known risks"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Declared assumptions"
    )


class ScoredOption(BaseModel):
    """An option with ALU scores attached."""
    option: Option
    scores: ALUScores
    composite_score: float = 0.0
    rank: int = 0

    def compute_composite(self, weights: dict[str, float] | None = None) -> None:
        self.composite_score = self.scores.weighted_score(weights)


# ──────────────────────────────────────────────
# Adversarial Selection
# ──────────────────────────────────────────────


class ScenarioResult(BaseModel):
    """Result of stress-testing an option against a single scenario."""
    scenario: Scenario
    survived: bool
    degradation: float = Field(
        ge=0.0, le=1.0,
        description="How much the option degraded under this scenario (0=none, 1=total failure)"
    )
    failure_mode: str = Field(
        default="",
        description="How the option would fail"
    )
    mitigation: str = Field(
        default="",
        description="Possible mitigation if partially survived"
    )


class StressTestResult(BaseModel):
    """Complete adversarial evaluation of an option."""
    option: ScoredOption | None = None
    scenario_results: list[ScenarioResult] = Field(default_factory=list)
    survived: bool = False
    resilience_score: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Fraction of scenarios survived"
    )
    fragility_profile: list[Scenario] = Field(
        default_factory=list,
        description="Scenarios that caused failure"
    )

    def compute_resilience(self) -> None:
        if not self.scenario_results:
            self.survived = True
            self.resilience_score = 1.0
            return
        survived_count = sum(1 for r in self.scenario_results if r.survived)
        self.resilience_score = survived_count / len(self.scenario_results)
        self.fragility_profile = [
            r.scenario for r in self.scenario_results if not r.survived
        ]
        self.survived = self.resilience_score >= 0.6  # survives majority


# ──────────────────────────────────────────────
# Governance Decision Record
# ──────────────────────────────────────────────


class GovernanceDecision(BaseModel):
    """
    The complete record of a Viveka governance cycle.

    This is the audit trail: what was real, what was true,
    what options existed, how they scored, which survived,
    and what was executed.
    """
    id: str = Field(description="Unique decision ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    risk_mode: RiskMode = RiskMode.STANDARD

    # Inputs
    environment: EnvironmentState
    context: TaskContext

    # Evaluation
    options_generated: list[Option] = Field(default_factory=list)
    options_scored: list[ScoredOption] = Field(default_factory=list)
    stress_test_results: list[StressTestResult] = Field(default_factory=list)
    adjusted_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Composite × resilience scores (non-mutating)"
    )
    stress_tested_ids: list[str] = Field(
        default_factory=list,
        description="Which option IDs were selected for stress testing"
    )
    suppressed_scenarios: list[dict] = Field(
        default_factory=list,
        description="Scenarios suppressed due to context (with reasons)"
    )

    # Output
    selected_option: Option | None = None
    rationale: str = Field(default="", description="Why this option was selected")
    escalated_to_human: bool = False
    escalation_reason: str = ""
    synthesis: Any | None = Field(default=None, description="Synthesis result when no option survived")

    # Post-execution (filled after action completes)
    outcome: str = ""
    outcome_matched_prediction: bool | None = None
