"""Shared fixtures for MicroDecisionEngine test suite."""

from __future__ import annotations

import pytest

from viveka.models.core import (
    Environment,
    EnvironmentState,
    Option,
    Permissions,
    Reversibility,
    RiskMode,
    TaskContext,
    TokenBudget,
)
from viveka.micro import MicroDecisionEngine, SessionState


# ── Factory helpers ──────────────────────────────────────


def _make_env(
    *,
    environment: Environment = Environment.DEVELOPMENT,
    budget: TokenBudget | None = None,
    can_access_secrets: bool = False,
    can_deploy: bool = False,
    can_modify_git: bool = True,
    blocked_paths: list[str] | None = None,
    blocked_tools: list[str] | None = None,
    git_branch: str = "feature/test",
    is_protected_branch: bool = False,
) -> EnvironmentState:
    return EnvironmentState(
        environment=environment,
        permissions=Permissions(
            can_access_secrets=can_access_secrets,
            can_deploy=can_deploy,
            can_modify_git=can_modify_git,
            blocked_paths=blocked_paths or [],
            blocked_tools=blocked_tools or [],
        ),
        budget=budget,
        git_state={
            "available": True,
            "branch": git_branch,
            "is_protected_branch": is_protected_branch,
            "dirty_files": [],
            "is_dirty": False,
        },
    )


def _make_ctx(
    *,
    task: str = "implement feature",
    reversibility: Reversibility = Reversibility.HIGH,
) -> TaskContext:
    return TaskContext(task=task, reversibility=reversibility)


def _make_engine(
    *,
    risk_mode: RiskMode = RiskMode.STANDARD,
    env: EnvironmentState | None = None,
    ctx: TaskContext | None = None,
    macro_strategy: Option | None = None,
) -> MicroDecisionEngine:
    return MicroDecisionEngine(
        environment=env or _make_env(),
        context=ctx or _make_ctx(),
        risk_mode=risk_mode,
        macro_strategy=macro_strategy,
    )


# ── Pytest fixtures ──────────────────────────────────────


@pytest.fixture
def make_env():
    return _make_env


@pytest.fixture
def make_ctx():
    return _make_ctx


@pytest.fixture
def make_engine():
    return _make_engine


@pytest.fixture
def standard_engine():
    """Engine in STANDARD risk mode with default env/context."""
    return _make_engine(risk_mode=RiskMode.STANDARD)


@pytest.fixture
def permissive_engine():
    return _make_engine(risk_mode=RiskMode.PERMISSIVE)


@pytest.fixture
def guarded_engine():
    return _make_engine(risk_mode=RiskMode.GUARDED)


@pytest.fixture
def restricted_engine():
    return _make_engine(risk_mode=RiskMode.RESTRICTED)


@pytest.fixture
def production_env():
    """Production environment with deploy disabled."""
    return _make_env(
        environment=Environment.PRODUCTION,
        can_deploy=False,
        git_branch="main",
        is_protected_branch=True,
    )


@pytest.fixture
def budget_env_near_limit():
    """Environment with budget 90% consumed."""
    return _make_env(budget=TokenBudget(max_tokens=1000, used_tokens=900))


@pytest.fixture
def budget_env_exhausted():
    """Environment with budget fully consumed."""
    return _make_env(budget=TokenBudget(max_tokens=1000, used_tokens=1000))
