"""
Micro-Decision Rule Engine — The Deterministic Kernel

Handles 80% of agent decisions without any LLM call.
Runs in milliseconds. Costs nothing.

This is the seed of the runtime governor. During agent execution,
every action passes through this engine. Most are permitted instantly.
Some are warned. Few are blocked. Rarely, one escalates to a
macro-decision (full governance pipeline).

The engine tracks behavioral patterns across decisions in a session:
retry loops, scope creep, token burn, assumption accumulation.

Usage:
    engine = MicroDecisionEngine(
        environment=env_state,
        context=task_context,
        risk_mode=RiskMode.STANDARD,
        macro_strategy=selected_option,  # from govern() output
    )

    # Agent proposes an action
    verdict = engine.evaluate("edit auth/views.py")
    if verdict.permitted:
        # proceed
    elif verdict.blocked:
        print(verdict.reason)
    elif verdict.escalate:
        # run macro governance decision
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum

from viveka.models.core import (
    EnvironmentState,
    Environment,
    Option,
    RiskMode,
    TaskContext,
    Reversibility,
)


class Verdict(str, Enum):
    """Micro-decision outcome."""
    PERMIT = "permit"          # proceed, no issues
    WARN = "warn"              # proceed, but flag for attention
    BLOCK = "block"            # do not proceed
    ESCALATE = "escalate"      # needs macro governance decision


@dataclass
class MicroDecision:
    """Result of a micro-decision evaluation."""
    verdict: Verdict
    action: str
    reason: str = ""
    rule: str = ""             # which rule triggered
    suggestions: list[str] = field(default_factory=list)

    @property
    def permitted(self) -> bool:
        return self.verdict in (Verdict.PERMIT, Verdict.WARN)

    @property
    def blocked(self) -> bool:
        return self.verdict == Verdict.BLOCK

    @property
    def escalate(self) -> bool:
        return self.verdict == Verdict.ESCALATE


@dataclass
class SessionState:
    """
    Tracks behavioral patterns across decisions in a session.
    This is where drift detection and retry loop catching happens.
    """
    decisions: list[MicroDecision] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    files_modified: set[str] = field(default_factory=set)
    tools_used: list[str] = field(default_factory=list)
    retries: dict[str, int] = field(default_factory=dict)  # action_pattern → count
    token_spend: int = 0
    assumptions_declared: list[str] = field(default_factory=list)
    assumptions_undeclared: int = 0
    started_at: float = field(default_factory=time.time)
    warnings_issued: int = 0
    blocks_issued: int = 0

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    @property
    def action_count(self) -> int:
        return len(self.actions_taken)

    def record(self, decision: MicroDecision, action: str):
        """Record a decision in session state."""
        self.decisions.append(decision)
        self.actions_taken.append(action)
        if decision.verdict == Verdict.WARN:
            self.warnings_issued += 1
        elif decision.verdict == Verdict.BLOCK:
            self.blocks_issued += 1

    def reset_stage_counters(self):
        """Reset per-stage counters. Call between stages.

        Keeps: files_modified, tools_used, total action count (session-level).
        Resets: retries, warnings, blocks (stage-level).
        """
        self.retries.clear()
        self.warnings_issued = 0
        self.blocks_issued = 0


class MicroDecisionEngine:
    """
    The deterministic decision kernel.

    No LLM calls. Pure rule evaluation.
    Designed to run on every agent action during execution.
    """

    def __init__(
        self,
        environment: EnvironmentState,
        context: TaskContext,
        risk_mode: RiskMode = RiskMode.STANDARD,
        macro_strategy: Option | None = None,
    ):
        self.env = environment
        self.ctx = context
        self.risk_mode = risk_mode
        self.macro_strategy = macro_strategy
        self.session = SessionState()

        # Risk-mode-dependent limits
        self._limits = _LIMITS[risk_mode]

    def evaluate(self, action: str) -> MicroDecision:
        """
        Evaluate a proposed action against all rules.
        Returns the most severe verdict from all applicable rules.

        Rules are checked in order of severity (block > escalate > warn > permit).
        First block or escalate wins.
        """
        results: list[MicroDecision] = []

        # Run all rule categories
        results.append(self._check_invariants(action))
        results.append(self._check_protected_resources(action))
        results.append(self._check_retry_loops(action))
        results.append(self._check_scope_drift(action))
        results.append(self._check_destructive_actions(action))
        results.append(self._check_token_budget(action))
        results.append(self._check_session_health(action))

        # Find most severe verdict
        severity = {Verdict.BLOCK: 3, Verdict.ESCALATE: 2, Verdict.WARN: 1, Verdict.PERMIT: 0}
        worst = max(results, key=lambda r: severity[r.verdict])

        # Collect all warnings/suggestions even if permitted
        if worst.verdict == Verdict.PERMIT:
            warnings = [r for r in results if r.verdict == Verdict.WARN]
            if warnings:
                worst = warnings[0]
                worst.suggestions = [w.reason for w in warnings[1:]]

        # Record in session
        self.session.record(worst, action)

        return worst

    def record_file_modified(self, filepath: str):
        """Track files modified during execution."""
        self.session.files_modified.add(filepath)

    def record_tool_used(self, tool: str):
        """Track tools used during execution."""
        self.session.tools_used.append(tool)

    def record_tokens(self, count: int):
        """Track token spend."""
        self.session.token_spend += count

    def record_assumption(self, assumption: str, declared: bool = True):
        """Track assumptions made during execution."""
        if declared:
            self.session.assumptions_declared.append(assumption)
        else:
            self.session.assumptions_undeclared += 1

    def get_session_summary(self) -> dict:
        """Return a summary of the session's behavioral patterns."""
        return {
            "total_actions": self.session.action_count,
            "warnings": self.session.warnings_issued,
            "blocks": self.session.blocks_issued,
            "files_modified": len(self.session.files_modified),
            "tools_used": len(set(self.session.tools_used)),
            "retry_patterns": dict(self.session.retries),
            "token_spend": self.session.token_spend,
            "assumptions_declared": len(self.session.assumptions_declared),
            "assumptions_undeclared": self.session.assumptions_undeclared,
            "elapsed_seconds": round(self.session.elapsed_seconds, 1),
        }

    # ──────────────────────────────────────────────
    # Rule implementations
    # ──────────────────────────────────────────────

    def _check_invariants(self, action: str) -> MicroDecision:
        """Hard invariant violations. Always block.
        Delegates to scanner.find_invariant_violations — single source of truth.
        """
        from viveka.layers.scanner import find_invariant_violations

        violations = find_invariant_violations(self.env, action)
        if violations:
            v = violations[0]
            return MicroDecision(
                verdict=Verdict.BLOCK,
                action=action,
                reason=v.message,
                rule=v.rule,
            )
        return MicroDecision(verdict=Verdict.PERMIT, action=action)

    def _check_protected_resources(self, action: str) -> MicroDecision:
        """Sensitive files and secrets.
        Protected branch checks handled by _check_invariants via scanner.
        """
        if (
            not self.env.permissions.can_access_secrets
            and _matches_any(action, [
                "secret", "credential", "api_key", "password",
                ".env", "token", "private_key",
            ])
        ):
            return MicroDecision(
                verdict=Verdict.WARN,
                action=action,
                reason="Action may involve secrets/credentials without permission",
                rule="protected:secrets",
            )

        return MicroDecision(verdict=Verdict.PERMIT, action=action)

    def _check_retry_loops(self, action: str) -> MicroDecision:
        """Detect blind retry patterns — same action repeated without change."""
        # Read operations are inherently safe and idempotent.
        # Reading a file multiple times is normal workflow (write → verify → iterate).
        # Only track retries for mutation/execution operations.
        if _is_read_only_action(action):
            return MicroDecision(verdict=Verdict.PERMIT, action=action)

        # Normalize action for comparison
        pattern = _normalize_action(action)

        if pattern in self.session.retries:
            self.session.retries[pattern] += 1
        else:
            self.session.retries[pattern] = 1

        count = self.session.retries[pattern]
        max_retries = self._limits["max_retries"]

        if count > max_retries:
            return MicroDecision(
                verdict=Verdict.BLOCK,
                action=action,
                reason=(
                    f"Retry loop detected: action repeated {count} times "
                    f"(limit: {max_retries} in {self.risk_mode.value} mode). "
                    f"Blind retries indicate the approach isn't working."
                ),
                rule="behavior:retry_loop",
                suggestions=["Try a different approach", "Escalate to human"],
            )
        elif count > 1 and count > max_retries // 2:
            return MicroDecision(
                verdict=Verdict.WARN,
                action=action,
                reason=f"Action repeated {count} times — approaching retry limit",
                rule="behavior:retry_warning",
            )

        return MicroDecision(verdict=Verdict.PERMIT, action=action)

    def _check_scope_drift(self, action: str) -> MicroDecision:
        """Detect when agent drifts beyond the task scope."""
        max_files = self._limits["max_files_modified"]
        max_tools = self._limits["max_unique_tools"]

        # Too many files modified
        if len(self.session.files_modified) > max_files:
            if _looks_like_file_edit(action):
                return MicroDecision(
                    verdict=Verdict.WARN,
                    action=action,
                    reason=(
                        f"Scope creep: {len(self.session.files_modified)} files modified "
                        f"(limit: {max_files}). Task may be expanding beyond original scope."
                    ),
                    rule="behavior:scope_creep_files",
                )

        # Too many different tools
        unique_tools = len(set(self.session.tools_used))
        if unique_tools > max_tools:
            return MicroDecision(
                verdict=Verdict.WARN,
                action=action,
                reason=(
                    f"High tool diversity: {unique_tools} unique tools used "
                    f"(limit: {max_tools}). Agent may be thrashing."
                ),
                rule="behavior:tool_thrashing",
            )

        # Task keyword drift — if macro strategy exists, check alignment
        if self.macro_strategy and self.session.action_count > 5:
            strategy_words = set(self.macro_strategy.strategy.lower().split())
            action_words = set(action.lower().split())
            # Very loose check — just flag if action seems completely unrelated
            overlap = strategy_words & action_words
            if len(action_words) > 3 and len(overlap) == 0:
                # Don't block, just track. Many legitimate actions won't share words.
                pass

        return MicroDecision(verdict=Verdict.PERMIT, action=action)

    def _check_destructive_actions(self, action: str) -> MicroDecision:
        """Flag or block destructive actions based on risk mode."""
        destructive_patterns = [
            "delete", "drop table", "drop database", "truncate",
            "rm -rf", "rm -r ",
            "force push", "push --force", "push -f ",
            "reset --hard", "clean -fd",
            "destroy", "remove all", "wipe", "purge",
        ]

        if _matches_any(action, destructive_patterns):
            if self.risk_mode in (RiskMode.GUARDED, RiskMode.RESTRICTED):
                return MicroDecision(
                    verdict=Verdict.BLOCK,
                    action=action,
                    reason=(
                        f"Destructive action blocked in {self.risk_mode.value} mode. "
                        f"Requires explicit human approval."
                    ),
                    rule="destructive:blocked",
                )
            elif self.ctx.reversibility in (Reversibility.LOW, Reversibility.IRREVERSIBLE):
                return MicroDecision(
                    verdict=Verdict.ESCALATE,
                    action=action,
                    reason="Destructive action with low reversibility — needs governance",
                    rule="destructive:low_reversibility",
                )
            else:
                return MicroDecision(
                    verdict=Verdict.WARN,
                    action=action,
                    reason="Destructive action detected — verify this is intentional",
                    rule="destructive:warning",
                )

        return MicroDecision(verdict=Verdict.PERMIT, action=action)

    def _check_token_budget(self, action: str) -> MicroDecision:
        """Warn or block as token budget depletes."""
        if not self.env.budget:
            return MicroDecision(verdict=Verdict.PERMIT, action=action)

        fraction = self.env.budget.fraction_used
        if fraction >= 1.0:
            return MicroDecision(
                verdict=Verdict.BLOCK,
                action=action,
                reason="Token budget exhausted",
                rule="budget:exhausted",
            )
        elif fraction >= self.env.budget.warn_at:
            return MicroDecision(
                verdict=Verdict.WARN,
                action=action,
                reason=f"Token budget {fraction:.0%} consumed — consider wrapping up",
                rule="budget:warning",
            )

        return MicroDecision(verdict=Verdict.PERMIT, action=action)

    def _check_session_health(self, action: str) -> MicroDecision:
        """Overall session health checks."""

        # Too many warnings without behavior change
        if self.session.warnings_issued > self._limits["max_warnings"]:
            return MicroDecision(
                verdict=Verdict.ESCALATE,
                action=action,
                reason=(
                    f"Session has accumulated {self.session.warnings_issued} warnings. "
                    f"Agent may not be responding to governance signals."
                ),
                rule="session:warning_accumulation",
            )

        # Too many total actions (runaway agent)
        if self.session.action_count > self._limits["max_actions"]:
            return MicroDecision(
                verdict=Verdict.ESCALATE,
                action=action,
                reason=(
                    f"Session has {self.session.action_count} actions "
                    f"(limit: {self._limits['max_actions']}). "
                    f"Agent may be stuck in an unproductive loop."
                ),
                rule="session:action_limit",
            )

        # Undeclared assumptions accumulating
        if self.session.assumptions_undeclared > self._limits["max_undeclared_assumptions"]:
            return MicroDecision(
                verdict=Verdict.WARN,
                action=action,
                reason=(
                    f"{self.session.assumptions_undeclared} undeclared assumptions detected. "
                    f"Agent should be explicit about what it's assuming."
                ),
                rule="session:undeclared_assumptions",
            )

        return MicroDecision(verdict=Verdict.PERMIT, action=action)


# ──────────────────────────────────────────────
# Risk-mode-dependent limits
# ──────────────────────────────────────────────

_LIMITS: dict[RiskMode, dict] = {
    RiskMode.PERMISSIVE: {
        "max_retries": 5,
        "max_files_modified": 30,
        "max_unique_tools": 15,
        "max_warnings": 15,
        "max_actions": 200,
        "max_undeclared_assumptions": 10,
    },
    RiskMode.STANDARD: {
        "max_retries": 3,
        "max_files_modified": 15,
        "max_unique_tools": 10,
        "max_warnings": 8,
        "max_actions": 100,
        "max_undeclared_assumptions": 5,
    },
    RiskMode.GUARDED: {
        "max_retries": 2,
        "max_files_modified": 8,
        "max_unique_tools": 6,
        "max_warnings": 5,
        "max_actions": 50,
        "max_undeclared_assumptions": 2,
    },
    RiskMode.RESTRICTED: {
        "max_retries": 1,
        "max_files_modified": 3,
        "max_unique_tools": 3,
        "max_warnings": 3,
        "max_actions": 20,
        "max_undeclared_assumptions": 0,
    },
}


# ──────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Check if text contains any of the patterns (case-insensitive)."""
    text_lower = text.lower()
    return any(p.lower() in text_lower for p in patterns)


def _normalize_action(action: str) -> str:
    """Normalize an action string for retry detection."""
    # Strip numbers, whitespace variations, specific IDs
    normalized = re.sub(r'\d+', 'N', action.lower().strip())
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def _looks_like_file_edit(action: str) -> bool:
    """Heuristic: does this action look like a file modification?"""
    return _matches_any(action, [
        "edit", "modify", "write", "create file", "update",
        "append", "replace", "insert", "delete line",
    ])


def _is_read_only_action(action: str) -> bool:
    """Detect inherently safe, idempotent operations.

    These should never trigger retry detection because:
    - They have no side effects (reads) or are safe to repeat (tests)
    - Write → read → iterate is normal agent workflow
    - Write → test → fix → test is normal development workflow
    - Blocking these prevents the agent from verifying its own work
    """
    lower = action.lower().strip()
    return _matches_any(lower, [
        # Read operations
        "read_file", "read file", "cat ", "search_code", "search code",
        "grep ", "find ", "ls ", "head ", "tail ", "view ",
        # Test operations (safe to repeat)
        "run_tests", "run tests", "pytest", "python -m pytest",
        "python3 -m pytest", "unittest", "run_command pytest",
        "run_command python -m pytest", "run_command python3 -m pytest",
    ])
