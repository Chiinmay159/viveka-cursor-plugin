"""
Layer 1: Ruta — Environment Invariant Scanner

Deterministic. No LLM calls. Scans the operating environment
and returns hard constraints that prune the option space.
"""

from __future__ import annotations

import json
import subprocess
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


def check_invariant_violations(
    environment: EnvironmentState,
    proposed_action: str,
) -> list[str]:
    """
    Check a proposed action against environment invariants.
    Returns list of violation descriptions. Empty = action is permitted.

    This is the hard gate. Violations here are non-negotiable.
    """
    violations = []

    # Budget check
    if environment.budget and environment.budget.remaining <= 0:
        violations.append("Token budget exhausted")

    # Production safety
    if environment.environment == Environment.PRODUCTION:
        if not environment.permissions.can_deploy and "deploy" in proposed_action.lower():
            violations.append("Deploy action not permitted in production")
        if not environment.permissions.can_modify_git and "git push" in proposed_action.lower():
            violations.append("Git push not permitted in production")

    # Protected branch
    if environment.git_state.get("is_protected_branch", False):
        destructive_keywords = ["force push", "reset --hard", "clean -fd"]
        for keyword in destructive_keywords:
            if keyword in proposed_action.lower():
                violations.append(f"Destructive action '{keyword}' on protected branch")

    # Path restrictions
    for blocked in environment.permissions.blocked_paths:
        if blocked in proposed_action:
            violations.append(f"Action references blocked path: {blocked}")

    # Tool restrictions
    for blocked_tool in environment.permissions.blocked_tools:
        if blocked_tool in proposed_action.lower():
            violations.append(f"Blocked tool referenced: {blocked_tool}")

    return violations
