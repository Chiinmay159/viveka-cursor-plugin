"""
Harness Results — structured scoring, comparison, and reporting.

Immutable records of a harness run. Each AgentRun captures one
(task, agent) pair. HarnessResult aggregates across agents.
All data is JSON-serializable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ConstraintVerdict:
    constraint: str
    verdict: str  # pass / fail / partial / unclear / not_verified
    evidence: str = ""
    location: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "constraint": self.constraint,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "location": self.location,
            "suggestion": self.suggestion,
        }


@dataclass
class VerificationResult:
    task: str
    total_constraints: int
    passed: int = 0
    failed: int = 0
    partial: int = 0
    unclear: int = 0
    verdicts: list[ConstraintVerdict] = field(default_factory=list)
    summary: str = ""

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.partial == 0

    @property
    def pass_rate(self) -> float:
        if self.total_constraints == 0:
            return 1.0
        return self.passed / self.total_constraints

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "failed": self.failed,
            "partial": self.partial,
            "unclear": self.unclear,
            "pass_rate": round(self.pass_rate, 3),
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


@dataclass
class IterationRecord:
    iteration: int
    exit_code: int
    duration_seconds: float
    verification: VerificationResult | None = None
    feedback_injected: bool = False
    halted: bool = False
    halt_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "verification": self.verification.to_dict() if self.verification else None,
            "feedback_injected": self.feedback_injected,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
        }


@dataclass
class AgentRun:
    agent_name: str
    task_name: str
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: str = ""

    governance_decision_id: str = ""
    governance_risk_mode: str = ""
    governance_readiness: str = ""
    governance_strategy: str = ""

    iterations: list[IterationRecord] = field(default_factory=list)
    total_iterations: int = 0

    final_verification: VerificationResult | None = None
    final_pass_rate: float = 0.0
    all_passed: bool = False
    total_duration_seconds: float = 0.0

    files_verified: list[str] = field(default_factory=list)

    def finalize(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.total_iterations = len(self.iterations)
        self.total_duration_seconds = round(
            sum(i.duration_seconds for i in self.iterations), 2
        )
        if self.iterations:
            last = self.iterations[-1]
            self.final_verification = last.verification
            if last.verification:
                self.final_pass_rate = round(last.verification.pass_rate, 3)
                self.all_passed = last.verification.all_passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "task_name": self.task_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "governance": {
                "decision_id": self.governance_decision_id,
                "risk_mode": self.governance_risk_mode,
                "readiness": self.governance_readiness,
                "strategy": self.governance_strategy,
            },
            "total_iterations": self.total_iterations,
            "iterations": [i.to_dict() for i in self.iterations],
            "final_pass_rate": self.final_pass_rate,
            "all_passed": self.all_passed,
            "total_duration_seconds": self.total_duration_seconds,
            "files_verified": self.files_verified,
        }


@dataclass
class HarnessResult:
    task_name: str
    task_description: str
    constraints: list[str]
    agent_runs: list[AgentRun] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: str = ""

    def finalize(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def comparison_matrix(self) -> dict[str, dict[str, str]]:
        matrix: dict[str, dict[str, str]] = {}
        for run in self.agent_runs:
            verdicts: dict[str, str] = {}
            if run.final_verification:
                for v in run.final_verification.verdicts:
                    verdicts[v.constraint] = v.verdict
            for c in self.constraints:
                if c not in verdicts:
                    verdicts[c] = "not_verified"
            matrix[run.agent_name] = verdicts
        return matrix

    def summary_table(self) -> list[dict[str, Any]]:
        rows = []
        for run in self.agent_runs:
            rows.append({
                "agent": run.agent_name,
                "pass_rate": run.final_pass_rate,
                "all_passed": run.all_passed,
                "iterations": run.total_iterations,
                "duration_seconds": run.total_duration_seconds,
                "governance_readiness": run.governance_readiness,
            })
        return sorted(rows, key=lambda r: r["pass_rate"], reverse=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "task_description": self.task_description,
            "constraints": self.constraints,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "agent_runs": [r.to_dict() for r in self.agent_runs],
            "comparison": self.comparison_matrix(),
            "summary": self.summary_table(),
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        return path
