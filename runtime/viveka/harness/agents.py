"""
Agent Adapters — thin wrappers around external agent CLIs.

An adapter is a name + command template with {task}/{feedback} placeholders.
No agent-specific logic. The adapter doesn't know what Claude Code or Codex
does — it only knows how to construct a command string.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class FeedbackInjectionError(Exception):
    pass


def _shell_escape(value: str) -> str:
    escaped = value.replace("'", "'\\''")
    escaped = escaped.replace("\n", "\\n")
    return escaped


@dataclass(frozen=True)
class AgentAdapter:
    name: str
    command_template: str
    description: str = ""

    def build_command(self, task: str, feedback: str = "") -> str:
        if "{task}" not in self.command_template:
            raise ValueError(
                f"Agent '{self.name}' command_template must contain {{task}}"
            )

        cmd = self.command_template
        safe_task = _shell_escape(task)
        safe_feedback = _shell_escape(feedback) if feedback else ""

        if feedback:
            if "{feedback}" in cmd:
                cmd = cmd.replace("{task}", safe_task).replace("{feedback}", safe_feedback)
            else:
                raise FeedbackInjectionError(
                    f"Agent '{self.name}' command_template has no {{feedback}} "
                    f"placeholder and feedback was provided."
                )
        else:
            cmd = cmd.replace("{task}", safe_task).replace("{feedback}", "")

        return cmd

    def execute(
        self,
        task: str,
        feedback: str = "",
        workdir: str | Path = ".",
        timeout: int | None = None,
    ) -> ExecutionResult:
        cmd = self.build_command(task, feedback)
        workdir = Path(workdir)

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, shell=True, cwd=workdir,
                capture_output=True, text=True, timeout=timeout,
            )
            duration = time.monotonic() - start
            return ExecutionResult(
                command=cmd, exit_code=proc.returncode,
                stdout=proc.stdout, stderr=proc.stderr,
                duration_seconds=round(duration, 2),
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            return ExecutionResult(
                command=cmd, exit_code=-1, stdout="",
                stderr=f"Command timed out after {timeout}s",
                duration_seconds=round(duration, 2), timed_out=True,
            )

    @classmethod
    def from_dict(cls, d: dict) -> AgentAdapter:
        return cls(
            name=d["name"],
            command_template=d["command_template"],
            description=d.get("description", ""),
        )


@dataclass
class ExecutionResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "stdout_lines": len(self.stdout.splitlines()),
            "stderr_lines": len(self.stderr.splitlines()),
        }


BUILT_IN_AGENTS: dict[str, AgentAdapter] = {
    "codex": AgentAdapter(
        name="codex",
        command_template="codex exec --full-auto '{task}\\n\\n{feedback}'",
        description="OpenAI Codex CLI agent (full-auto mode)",
    ),
    "claude": AgentAdapter(
        name="claude",
        command_template="claude -p '{task}\\n\\n{feedback}'",
        description="Anthropic Claude Code CLI agent",
    ),
    "echo": AgentAdapter(
        name="echo",
        command_template="echo 'TASK: {task} | FEEDBACK: {feedback}'",
        description="Dummy agent for testing (echoes task and feedback)",
    ),
}


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentAdapter] = {}

    def register(self, adapter: AgentAdapter) -> None:
        self._agents[adapter.name] = adapter

    def get(self, name: str) -> AgentAdapter:
        if name not in self._agents:
            available = ", ".join(sorted(self._agents.keys()))
            raise KeyError(f"Agent '{name}' not registered. Available: {available}")
        return self._agents[name]

    def list(self) -> list[str]:
        return sorted(self._agents.keys())

    def load_from_yaml(self, path: str | Path) -> None:
        import yaml
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        for agent_def in data.get("agents", []):
            self.register(AgentAdapter.from_dict(agent_def))

    @classmethod
    def with_builtins(cls) -> AgentRegistry:
        registry = cls()
        for adapter in BUILT_IN_AGENTS.values():
            registry.register(adapter)
        return registry
