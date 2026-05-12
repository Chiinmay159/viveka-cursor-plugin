"""
Policy Packs — Reusable Governance Configurations

A policy pack captures an organization's or domain's rules for a
specific class of decisions. Instead of specifying --env production
--risk locked --reversibility low --constraint "..." every time,
you define it once and reference by name.

Packs compose: you can layer "production" + "payment-critical" + "after-hours"
and the most restrictive policy wins for each parameter.

Built-in packs:
    - production-hotfix: Locked mode, low reversibility, human escalation
    - refactor-safe: Balanced mode, high reversibility, scope limits
    - cleanup: Explore mode, high reversibility, broad scope
    - data-migration: Cautious mode, low reversibility, backup required
    - incident-response: Locked mode, critical urgency, minimal scope

Custom packs: YAML files in ~/.viveka/policies/
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from viveka.models.core import (
    Environment,
    Intent,
    Reversibility,
    RiskMode,
    Urgency,
)

POLICY_DIR = Path.home() / ".viveka" / "policies"


@dataclass
class PolicyPack:
    """A named set of governance parameters."""
    name: str
    description: str = ""

    # Environment defaults
    environment: Environment | None = None
    risk_mode: RiskMode | None = None
    intent: Intent | None = None
    urgency: Urgency | None = None
    reversibility: Reversibility | None = None

    # Constraints
    constraints: list[str] = field(default_factory=list)

    # Micro-engine overrides
    max_retries: int | None = None
    max_files_modified: int | None = None
    max_actions: int | None = None
    blocked_paths: list[str] = field(default_factory=list)
    blocked_tools: list[str] = field(default_factory=list)

    # Behavioral rules
    require_human_approval: bool = False
    require_backup_before_mutation: bool = False
    require_tests_before_deploy: bool = False

    def merge(self, other: PolicyPack) -> PolicyPack:
        """
        Merge two policies. The stricter value wins for each field.
        'other' takes precedence for non-None values.
        Lists are concatenated.
        """
        return PolicyPack(
            name=f"{self.name}+{other.name}",
            description=f"Merged: {self.description} | {other.description}",
            environment=_stricter_env(self.environment, other.environment),
            risk_mode=_stricter_risk(self.risk_mode, other.risk_mode),
            intent=other.intent or self.intent,
            urgency=_stricter_urgency(self.urgency, other.urgency),
            reversibility=_lower_reversibility(self.reversibility, other.reversibility),
            constraints=self.constraints + other.constraints,
            max_retries=_min_or(self.max_retries, other.max_retries),
            max_files_modified=_min_or(self.max_files_modified, other.max_files_modified),
            max_actions=_min_or(self.max_actions, other.max_actions),
            blocked_paths=list(set(self.blocked_paths + other.blocked_paths)),
            blocked_tools=list(set(self.blocked_tools + other.blocked_tools)),
            require_human_approval=self.require_human_approval or other.require_human_approval,
            require_backup_before_mutation=self.require_backup_before_mutation or other.require_backup_before_mutation,
            require_tests_before_deploy=self.require_tests_before_deploy or other.require_tests_before_deploy,
        )


# ──────────────────────────────────────────────
# Built-in packs
# ──────────────────────────────────────────────

BUILTIN_PACKS: dict[str, PolicyPack] = {
    "production-hotfix": PolicyPack(
        name="production-hotfix",
        description="Maximum safety for production incident fixes",
        environment=Environment.PRODUCTION,
        risk_mode=RiskMode.LOCKED,
        intent=Intent.FIX,
        urgency=Urgency.CRITICAL,
        reversibility=Reversibility.LOW,
        constraints=[
            "Must not break working functionality",
            "Must not increase blast radius",
            "Must be deployable without full release cycle",
            "Must have immediate rollback plan",
        ],
        max_retries=1,
        max_files_modified=3,
        max_actions=20,
        require_human_approval=True,
    ),

    "refactor-safe": PolicyPack(
        name="refactor-safe",
        description="Safe refactoring with scope guardrails",
        environment=Environment.DEVELOPMENT,
        risk_mode=RiskMode.BALANCED,
        intent=Intent.IMPROVEMENT,
        reversibility=Reversibility.HIGH,
        constraints=[
            "Must not change external behavior",
            "Tests must pass before and after",
        ],
        max_files_modified=15,
        require_tests_before_deploy=True,
    ),

    "cleanup": PolicyPack(
        name="cleanup",
        description="Broad-scope cleanup with safety net",
        environment=Environment.DEVELOPMENT,
        risk_mode=RiskMode.BALANCED,
        intent=Intent.MAINTENANCE,
        reversibility=Reversibility.HIGH,
        constraints=[
            "Verify no runtime references before deletion",
            "Check for dynamic imports and reflection usage",
        ],
    ),

    "data-migration": PolicyPack(
        name="data-migration",
        description="Database migration with backup requirements",
        risk_mode=RiskMode.CAUTIOUS,
        reversibility=Reversibility.LOW,
        constraints=[
            "Must create backup before any mutation",
            "Must validate data integrity after migration",
            "Must have rollback script ready",
            "Must not exceed maintenance window",
        ],
        max_retries=1,
        require_backup_before_mutation=True,
        require_human_approval=True,
        blocked_tools=["DROP", "TRUNCATE"],
    ),

    "incident-response": PolicyPack(
        name="incident-response",
        description="Active incident: contain first, fix later",
        environment=Environment.PRODUCTION,
        risk_mode=RiskMode.LOCKED,
        urgency=Urgency.CRITICAL,
        reversibility=Reversibility.LOW,
        constraints=[
            "Containment before root cause analysis",
            "No speculative fixes",
            "Log all actions for post-incident review",
            "Escalate if containment fails on first attempt",
        ],
        max_retries=1,
        max_files_modified=2,
        max_actions=10,
        require_human_approval=True,
    ),
}


def get_policy(name: str) -> PolicyPack | None:
    """Get a policy by name. Checks built-ins first, then user-defined."""
    if name in BUILTIN_PACKS:
        return BUILTIN_PACKS[name]
    return _load_user_policy(name)


def list_policies() -> list[tuple[str, str, str]]:
    """List all available policies. Returns (name, description, source)."""
    policies = []
    for name, pack in BUILTIN_PACKS.items():
        policies.append((name, pack.description, "built-in"))

    if POLICY_DIR.exists():
        for f in sorted(POLICY_DIR.glob("*.yaml")):
            pack = _load_user_policy(f.stem)
            if pack:
                policies.append((f.stem, pack.description, "user"))

    return policies


def merge_policies(names: list[str]) -> PolicyPack | None:
    """Load and merge multiple policies. Stricter wins."""
    packs = []
    for name in names:
        pack = get_policy(name)
        if pack is None:
            return None
        packs.append(pack)

    if not packs:
        return None

    result = packs[0]
    for pack in packs[1:]:
        result = result.merge(pack)
    return result


# ──────────────────────────────────────────────
# User-defined policy loading (YAML)
# ──────────────────────────────────────────────

def _load_user_policy(name: str) -> PolicyPack | None:
    """Load a user-defined policy from ~/.viveka/policies/{name}.yaml"""
    path = POLICY_DIR / f"{name}.yaml"
    if not path.exists():
        return None

    try:
        import yaml
    except ImportError:
        return None

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        return None

    return PolicyPack(
        name=data.get("name", name),
        description=data.get("description", ""),
        environment=Environment(data["environment"]) if "environment" in data else None,
        risk_mode=RiskMode(data["risk_mode"]) if "risk_mode" in data else None,
        intent=Intent(data["intent"]) if "intent" in data else None,
        urgency=Urgency(data["urgency"]) if "urgency" in data else None,
        reversibility=Reversibility(data["reversibility"]) if "reversibility" in data else None,
        constraints=data.get("constraints", []),
        max_retries=data.get("max_retries"),
        max_files_modified=data.get("max_files_modified"),
        max_actions=data.get("max_actions"),
        blocked_paths=data.get("blocked_paths", []),
        blocked_tools=data.get("blocked_tools", []),
        require_human_approval=data.get("require_human_approval", False),
        require_backup_before_mutation=data.get("require_backup_before_mutation", False),
        require_tests_before_deploy=data.get("require_tests_before_deploy", False),
    )


# ──────────────────────────────────────────────
# Merge helpers — stricter wins
# ──────────────────────────────────────────────

_ENV_SEVERITY = {
    Environment.DEVELOPMENT: 0,
    Environment.STAGING: 1,
    Environment.PRODUCTION: 2,
}

_RISK_SEVERITY = {
    RiskMode.EXPLORE: 0,
    RiskMode.BALANCED: 1,
    RiskMode.CAUTIOUS: 2,
    RiskMode.LOCKED: 3,
}

_URGENCY_SEVERITY = {
    Urgency.LOW: 0,
    Urgency.MEDIUM: 1,
    Urgency.HIGH: 2,
    Urgency.CRITICAL: 3,
}

_REVERSIBILITY_SEVERITY = {
    Reversibility.HIGH: 0,
    Reversibility.MEDIUM: 1,
    Reversibility.LOW: 2,
    Reversibility.IRREVERSIBLE: 3,
}


def _stricter_env(a: Environment | None, b: Environment | None) -> Environment | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if _ENV_SEVERITY.get(a, 0) >= _ENV_SEVERITY.get(b, 0) else b


def _stricter_risk(a: RiskMode | None, b: RiskMode | None) -> RiskMode | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if _RISK_SEVERITY.get(a, 0) >= _RISK_SEVERITY.get(b, 0) else b


def _stricter_urgency(a: Urgency | None, b: Urgency | None) -> Urgency | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if _URGENCY_SEVERITY.get(a, 0) >= _URGENCY_SEVERITY.get(b, 0) else b


def _lower_reversibility(a: Reversibility | None, b: Reversibility | None) -> Reversibility | None:
    if a is None:
        return b
    if b is None:
        return a
    return a if _REVERSIBILITY_SEVERITY.get(a, 0) >= _REVERSIBILITY_SEVERITY.get(b, 0) else b


def _min_or(a: int | None, b: int | None) -> int | None:
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)
