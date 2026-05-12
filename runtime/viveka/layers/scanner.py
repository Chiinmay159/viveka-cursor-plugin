"""
Layer 1: Ruta — Environment Invariant Scanner

Deterministic. No LLM calls. Scans the operating environment
and returns hard constraints that prune the option space.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from viveka.models.core import (
    Environment,
    EnvironmentState,
    Permissions,
    TokenBudget,
)


def scan_environment(
    repo_path: str = ".",
    environment: Environment = Environment.DEVELOPMENT,
    budget: TokenBudget | None = None,
    permissions: Permissions | None = None,
    additional_constraints: dict | None = None,
) -> EnvironmentState:
    """
    Scan the operating environment and return invariant state.

    All detection is deterministic — no LLM calls.
    Falls back gracefully if tools aren't available.
    """
    git_state = _scan_git(repo_path)
    available_tools = _detect_available_tools()

    return EnvironmentState(
        environment=environment,
        permissions=permissions or Permissions(),
        budget=budget,
        git_state=git_state,
        available_tools=available_tools,
        constraints=additional_constraints or {},
    )


def _scan_git(repo_path: str) -> dict:
    """Detect git state: branch, dirty files, remotes."""
    state: dict = {"available": False}
    try:
        # Check if git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return state

        state["available"] = True

        # Current branch
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        state["branch"] = branch.stdout.strip()

        # Dirty files
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        dirty_files = [
            line.strip() for line in status.stdout.strip().split("\n") if line.strip()
        ]
        state["dirty_files"] = dirty_files
        state["is_dirty"] = len(dirty_files) > 0

        # Protected branches (convention-based detection)
        state["is_protected_branch"] = state.get("branch", "") in {
            "main", "master", "production", "release",
        }

    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return state


def _detect_available_tools() -> list[str]:
    """Detect which tools are available in the environment."""
    tools = []
    check_commands = {
        "git": ["git", "--version"],
        "python": ["python3", "--version"],
        "node": ["node", "--version"],
        "npm": ["npm", "--version"],
        "docker": ["docker", "--version"],
        "pytest": ["python3", "-m", "pytest", "--version"],
        "ruff": ["ruff", "--version"],
    }

    for tool_name, command in check_commands.items():
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0:
                tools.append(tool_name)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return tools


@dataclass
class InvariantViolation:
    """Structured invariant violation with rule tag for tracing."""
    message: str
    rule: str


def find_invariant_violations(
    environment: EnvironmentState,
    proposed_action: str,
) -> list[InvariantViolation]:
    """
    Single source of truth for environment invariant checks.
    Used by both the scanner (macro pipeline) and the micro engine.
    """
    violations = []
    action_lower = proposed_action.lower()

    if environment.budget and environment.budget.remaining <= 0:
        violations.append(InvariantViolation(
            "Token budget exhausted", "invariant:budget",
        ))

    if environment.environment == Environment.PRODUCTION:
        if not environment.permissions.can_deploy and any(
            p in action_lower for p in ["deploy", "push to prod", "release"]
        ):
            violations.append(InvariantViolation(
                "Deploy action not permitted in production",
                "invariant:deploy_permission",
            ))
        if not environment.permissions.can_modify_git and "git push" in action_lower:
            violations.append(InvariantViolation(
                "Git push not permitted in production",
                "invariant:deploy_permission",
            ))

    if environment.git_state.get("is_protected_branch", False):
        for keyword in [
            "force push", "push --force", "push -f ",
            "reset --hard", "clean -fd",
        ]:
            if keyword in action_lower:
                violations.append(InvariantViolation(
                    f"Destructive action '{keyword}' on protected branch",
                    "invariant:protected_branch",
                ))

    for blocked in environment.permissions.blocked_paths:
        if blocked in proposed_action:
            violations.append(InvariantViolation(
                f"Action references blocked path: {blocked}",
                "invariant:blocked_path",
            ))

    for blocked_tool in environment.permissions.blocked_tools:
        if blocked_tool.lower() in action_lower:
            violations.append(InvariantViolation(
                f"Blocked tool referenced: {blocked_tool}",
                "invariant:blocked_tool",
            ))

    return violations


def check_invariant_violations(
    environment: EnvironmentState,
    proposed_action: str,
) -> list[str]:
    """
    Check a proposed action against environment invariants.
    Returns list of violation descriptions. Empty = action is permitted.
    """
    return [v.message for v in find_invariant_violations(environment, proposed_action)]
