"""
Stage Contracts & Governed Toolkit — Enforceable execution boundaries.

Extracted from v0.5.0 agent/contracts.py + agent/tools.py. No LLM calls.

StageContract defines per-stage execution boundaries: allowed tools,
file scope, budget, success checks, stop conditions, rollback.
GovernedToolkit is a pure stage-contract gate — it checks stage
constraints only. The caller owns micro evaluation (through
GovernedSession or MicroDecisionEngine directly).

Usage:
    from viveka.contracts import StageContract, ToolName, GovernedToolkit

    stage = StageContract(
        id="stage_1",
        goal="Implement auth module",
        allowed_tools=[ToolName.WRITE_FILE, ToolName.READ_FILE],
        file_scope=["src/auth.py"],
        max_tool_calls=20,
    )

    toolkit = GovernedToolkit()
    stage_verdict = toolkit.check_stage(tool_call, stage)
    if stage_verdict.permitted:
        micro_verdict = session.propose(tool_call.action_string)  # caller's choice
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from viveka.micro import Verdict


class ToolName(str, Enum):
    WRITE_FILE = "write_file"
    READ_FILE = "read_file"
    RUN_COMMAND = "run_command"
    RUN_TESTS = "run_tests"
    SEARCH_CODE = "search_code"
    CALL_LLM = "call_llm"


@dataclass
class ToolCall:
    tool: ToolName
    args: dict[str, Any] = field(default_factory=dict)
    purpose: str = ""

    @property
    def action_string(self) -> str:
        if self.tool == ToolName.WRITE_FILE:
            return f"write_file {self.args.get('path', 'unknown')}"
        elif self.tool == ToolName.READ_FILE:
            return f"read_file {self.args.get('path', 'unknown')}"
        elif self.tool == ToolName.RUN_COMMAND:
            return f"run_command {self.args.get('command', 'unknown')}"
        elif self.tool == ToolName.RUN_TESTS:
            return f"run_tests {self.args.get('path', '')}"
        elif self.tool == ToolName.SEARCH_CODE:
            return f"search_code {self.args.get('query', '')}"
        elif self.tool == ToolName.CALL_LLM:
            return f"call_llm {self.args.get('purpose', 'generate')}"
        return f"{self.tool.value} {self.args}"


class StageStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class StageContract:
    """
    Enforceable agreement for a unit of work.
    The agent loop enforces these — they're not suggestions.
    """
    id: str
    goal: str
    allowed_tools: list[ToolName] = field(default_factory=lambda: list(ToolName))
    file_scope: list[str] = field(default_factory=list)
    budget_tokens: int = 10000
    max_tool_calls: int = 20
    success_checks: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    rollback_action: str = ""
    constraints: list[str] = field(default_factory=list)

    status: StageStatus = StageStatus.PENDING
    tool_calls_made: int = 0
    tokens_used: int = 0
    blocks_in_stage: int = 0
    warnings_in_stage: int = 0
    replan_count: int = 0

    MAX_BLOCKS_BEFORE_REPLAN: int = 3
    MAX_REPLANS: int = 2

    @property
    def budget_exhausted(self) -> bool:
        return self.tokens_used >= self.budget_tokens

    @property
    def tool_limit_reached(self) -> bool:
        return self.tool_calls_made >= self.max_tool_calls

    @property
    def needs_replan(self) -> bool:
        return self.blocks_in_stage >= self.MAX_BLOCKS_BEFORE_REPLAN

    @property
    def can_replan(self) -> bool:
        return self.replan_count < self.MAX_REPLANS

    def record_tool_call(self) -> None:
        self.tool_calls_made += 1

    def record_block(self) -> None:
        self.blocks_in_stage += 1

    def record_warning(self) -> None:
        self.warnings_in_stage += 1

    def record_replan(self) -> None:
        self.replan_count += 1
        self.blocks_in_stage = 0

    def is_tool_allowed(self, tool: ToolName) -> bool:
        return tool in self.allowed_tools

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "allowed_tools": [t.value for t in self.allowed_tools],
            "file_scope": self.file_scope,
            "budget_tokens": self.budget_tokens,
            "max_tool_calls": self.max_tool_calls,
            "success_checks": self.success_checks,
            "stop_conditions": self.stop_conditions,
            "status": self.status.value,
            "tool_calls_made": self.tool_calls_made,
            "blocks_in_stage": self.blocks_in_stage,
            "warnings_in_stage": self.warnings_in_stage,
            "replan_count": self.replan_count,
        }


@dataclass
class StageResult:
    stage_id: str
    status: StageStatus
    files_written: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    test_results: dict[str, Any] = field(default_factory=dict)
    tool_calls: int = 0
    tokens_used: int = 0
    blocks: int = 0
    warnings: int = 0
    replans: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id,
            "status": self.status.value,
            "files_written": self.files_written,
            "tool_calls": self.tool_calls,
            "blocks": self.blocks,
            "warnings": self.warnings,
            "replans": self.replans,
            "error": self.error,
        }


class ReflectorEventType(str, Enum):
    WARN = "warn"
    BLOCK = "block"
    ESCALATION = "escalation"
    TEST_FAILURE = "test_failure"
    RETRY_THRESHOLD = "retry_threshold"
    STAGE_COMPLETE = "stage_complete"
    CONSTRAINT_VIOLATION = "constraint_violation"
    TASK_COMPLETE = "task_complete"
    REPLAN_TRIGGERED = "replan_triggered"


@dataclass
class ReflectorEvent:
    event_type: ReflectorEventType
    stage_id: str
    action: str = ""
    detail: str = ""
    timestamp: float = field(
        default_factory=lambda: datetime.now(timezone.utc).timestamp()
    )

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "stage_id": self.stage_id,
            "action": self.action,
            "detail": self.detail,
            "timestamp": self.timestamp,
        }


@dataclass
class StageVerdict:
    """Result of a stage-contract check. Does NOT include micro engine evaluation."""
    permitted: bool
    reason: str = ""
    rule: str = "stage_contract"


class GovernedToolkit:
    """
    Pure stage-contract gate. Checks tool allowlists, call limits,
    and budget — nothing else. Does NOT call the micro engine.

    The caller owns micro evaluation. This separation means
    GovernedToolkit composes safely with any evaluation path
    (GovernedSession, bare MicroDecisionEngine, or none).

    Usage:
        toolkit = GovernedToolkit()
        stage_verdict = toolkit.check_stage(tool_call, stage)
        if not stage_verdict.permitted:
            # blocked by stage contract
            ...
        else:
            # caller runs micro evaluation through their preferred path
            micro_result = session.propose(tool_call.action_string)
    """

    def __init__(self):
        self.events: list[ReflectorEvent] = []

    def reset_for_stage(self) -> None:
        self.events.clear()

    def check_stage(
        self, tool_call: ToolCall, stage: StageContract,
    ) -> StageVerdict:
        """Check tool call against stage contract only. Caller handles micro evaluation."""
        if not stage.is_tool_allowed(tool_call.tool):
            stage.record_block()
            self._emit(
                ReflectorEventType.BLOCK, stage.id,
                tool_call.action_string,
                f"Tool {tool_call.tool.value} not allowed in stage {stage.id}",
            )
            return StageVerdict(
                permitted=False,
                reason=f"Tool {tool_call.tool.value} not in stage allowed_tools: "
                       f"{[t.value for t in stage.allowed_tools]}",
            )

        if stage.tool_limit_reached:
            stage.record_block()
            self._emit(
                ReflectorEventType.BLOCK, stage.id,
                tool_call.action_string,
                f"Tool call limit reached: {stage.max_tool_calls}",
            )
            return StageVerdict(
                permitted=False,
                reason=f"Stage tool call limit reached ({stage.max_tool_calls})",
            )

        if stage.budget_exhausted:
            stage.record_block()
            self._emit(
                ReflectorEventType.BLOCK, stage.id,
                tool_call.action_string,
                f"Token budget exhausted: {stage.budget_tokens}",
            )
            return StageVerdict(
                permitted=False,
                reason=f"Stage token budget exhausted ({stage.budget_tokens})",
            )

        stage.record_tool_call()
        return StageVerdict(permitted=True)

    def drain_events(self) -> list[ReflectorEvent]:
        events = list(self.events)
        self.events.clear()
        return events

    def _emit(
        self, event_type: ReflectorEventType, stage_id: str,
        action: str, detail: str,
    ) -> None:
        self.events.append(ReflectorEvent(
            event_type=event_type,
            stage_id=stage_id,
            action=action,
            detail=detail,
        ))
