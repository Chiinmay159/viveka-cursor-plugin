"""
GovernedSession — Micro→Macro bridge with trace export.

Extracted from v0.5.0 session.py. Model-independent parts only.

Wraps the micro engine into a session that tracks actions, builds
escalation context from session state, and exports full traces.
The LLM-dependent escalation path (Governor.govern) is replaced
with a structured escalation record — the caller decides how to
handle it (invoke Governor externally, ask user, etc.).

Usage:
    session = GovernedSession(
        micro=engine,
        task="Refactor auth module",
    )

    result = session.propose("write_file src/auth.py")
    if result.proceed:
        execute(action)
        session.record_completion(action)
    elif result.escalated:
        # Handle escalation — result.escalation_context has structured data
        ...

    trace = session.get_trace()
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from viveka.micro import MicroDecisionEngine, Verdict


class ActionOutcome(str, Enum):
    PROCEED = "proceed"
    BLOCKED = "blocked"
    ESCALATED = "escalated"


@dataclass
class SessionAction:
    sequence: int
    action: str
    verdict: Verdict
    rule: str
    reason: str
    outcome: ActionOutcome
    timestamp: float = field(default_factory=time.time)
    completed: bool = False


@dataclass
class ProposalResult:
    proceed: bool
    blocked: bool = False
    escalated: bool = False
    verdict: Verdict = Verdict.PERMIT
    reason: str = ""
    rule: str = ""
    suggestions: list[str] = field(default_factory=list)
    escalation_context: dict | None = None


class GovernedSession:
    """
    The micro→macro bridge. Wraps micro engine with session tracking
    and structured escalation context.
    """

    def __init__(
        self,
        micro: MicroDecisionEngine,
        task: str = "",
        known_constraints: list[str] | None = None,
    ):
        self.session_id = f"ses_{uuid.uuid4().hex[:12]}"
        self.micro = micro
        self.task = task
        self.known_constraints = known_constraints or []
        self.actions: list[SessionAction] = []
        self.escalation_count: int = 0
        self.started_at: float = time.time()

    def propose(self, action: str) -> ProposalResult:
        """
        Propose an action. Returns immediately — no LLM calls.
        On ESCALATE, builds structured escalation context from session state.
        """
        sequence = len(self.actions) + 1
        micro_result = self.micro.evaluate(action)

        if micro_result.verdict == Verdict.PERMIT:
            self.actions.append(SessionAction(
                sequence=sequence, action=action,
                verdict=Verdict.PERMIT, rule=micro_result.rule,
                reason=micro_result.reason, outcome=ActionOutcome.PROCEED,
            ))
            return ProposalResult(proceed=True, verdict=Verdict.PERMIT)

        if micro_result.verdict == Verdict.WARN:
            self.actions.append(SessionAction(
                sequence=sequence, action=action,
                verdict=Verdict.WARN, rule=micro_result.rule,
                reason=micro_result.reason, outcome=ActionOutcome.PROCEED,
            ))
            return ProposalResult(
                proceed=True, verdict=Verdict.WARN,
                reason=micro_result.reason, rule=micro_result.rule,
                suggestions=micro_result.suggestions,
            )

        if micro_result.verdict == Verdict.BLOCK:
            self.actions.append(SessionAction(
                sequence=sequence, action=action,
                verdict=Verdict.BLOCK, rule=micro_result.rule,
                reason=micro_result.reason, outcome=ActionOutcome.BLOCKED,
            ))
            return ProposalResult(
                proceed=False, blocked=True, verdict=Verdict.BLOCK,
                reason=micro_result.reason, rule=micro_result.rule,
                suggestions=micro_result.suggestions,
            )

        if micro_result.verdict == Verdict.ESCALATE:
            self.escalation_count += 1
            esc_context = self._build_escalation_context(action, micro_result)
            self.actions.append(SessionAction(
                sequence=sequence, action=action,
                verdict=Verdict.ESCALATE, rule=micro_result.rule,
                reason=micro_result.reason, outcome=ActionOutcome.ESCALATED,
            ))
            return ProposalResult(
                proceed=False, escalated=True, verdict=Verdict.ESCALATE,
                reason=micro_result.reason, rule=micro_result.rule,
                suggestions=micro_result.suggestions,
                escalation_context=esc_context,
            )

        return ProposalResult(proceed=False, reason="Unknown verdict")

    def record_completion(self, action: str):
        for record in reversed(self.actions):
            if record.action == action and not record.completed:
                record.completed = True
                break

    def record_file_modified(self, filepath: str):
        self.micro.record_file_modified(filepath)

    def record_tool_used(self, tool: str):
        self.micro.record_tool_used(tool)

    def record_tokens(self, count: int):
        self.micro.record_tokens(count)

    def _build_escalation_context(self, action: str, micro_result) -> dict:
        """
        Convert micro session state into structured escalation data.
        This is the information bridge — micro patterns become context
        for whatever handles the escalation.
        """
        summary = self.micro.get_session_summary()
        constraints = [
            f"ESCALATION TRIGGER: {micro_result.rule} — {micro_result.reason}"
        ]

        if summary["warnings"] > 0:
            constraints.append(
                f"Session has accumulated {summary['warnings']} warnings — "
                f"agent may not be responding to governance signals"
            )

        if summary["retry_patterns"]:
            repeat_actions = {
                k: v for k, v in summary["retry_patterns"].items() if v > 1
            }
            if repeat_actions:
                constraints.append(
                    f"Retry patterns detected: {repeat_actions} — "
                    f"previous approaches may be failing silently"
                )

        if summary["files_modified"] > 5:
            constraints.append(
                f"{summary['files_modified']} files already modified in session — "
                f"scope may be expanding beyond original task"
            )

        return {
            "session_id": self.session_id,
            "action": action,
            "trigger_rule": micro_result.rule,
            "trigger_reason": micro_result.reason,
            "escalation_number": self.escalation_count,
            "session_summary": summary,
            "inferred_constraints": constraints,
            "known_constraints": self.known_constraints,
            "task": self.task,
        }

    def get_trace(self) -> dict:
        """Export the full session trace as a linked chain."""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "risk_mode": self.micro.risk_mode.value,
            "started_at": datetime.fromtimestamp(
                self.started_at, tz=timezone.utc,
            ).isoformat(),
            "elapsed_seconds": round(time.time() - self.started_at, 1),
            "micro_summary": self.micro.get_session_summary(),
            "escalation_count": self.escalation_count,
            "actions": [
                {
                    "sequence": a.sequence,
                    "action": a.action,
                    "verdict": a.verdict.value,
                    "rule": a.rule,
                    "reason": a.reason,
                    "outcome": a.outcome.value,
                    "completed": a.completed,
                    "timestamp": a.timestamp,
                }
                for a in self.actions
            ],
        }

    def get_summary(self) -> dict:
        """Compact session summary for status reporting."""
        return {
            "session_id": self.session_id,
            "task": self.task[:80] if self.task else "",
            "actions": len(self.actions),
            "escalations": self.escalation_count,
            "blocks": sum(1 for a in self.actions if a.verdict == Verdict.BLOCK),
            "warnings": sum(1 for a in self.actions if a.verdict == Verdict.WARN),
            "elapsed": round(time.time() - self.started_at, 1),
        }
