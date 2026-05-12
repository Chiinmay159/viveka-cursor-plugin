"""
Task Specifications — declarative definitions for harness runs.

A task spec defines what the agent must build, how to verify output,
and metadata for analysis. No code in task specs — all logic in the runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VerificationConfig:
    mode: str = "changed"
    files: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, d: dict | None) -> VerificationConfig:
        if not d:
            return cls()
        return cls(
            mode=d.get("mode", "changed"),
            files=tuple(d.get("files", [])),
            exclude=tuple(d.get("exclude", [])),
        )


@dataclass(frozen=True)
class IterationConfig:
    enabled: bool = True
    max_iterations: int = 3

    @classmethod
    def from_dict(cls, d: dict | None) -> IterationConfig:
        if not d:
            return cls()
        return cls(
            enabled=d.get("enabled", True),
            max_iterations=d.get("max_iterations", 3),
        )


@dataclass(frozen=True)
class TaskMetadata:
    difficulty: str = "medium"
    category: str = "general"
    tags: tuple[str, ...] = ()
    expected_traps: tuple[str, ...] = ()
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict | None) -> TaskMetadata:
        if not d:
            return cls()
        return cls(
            difficulty=d.get("difficulty", "medium"),
            category=d.get("category", "general"),
            tags=tuple(d.get("tags", [])),
            expected_traps=tuple(d.get("expected_traps", [])),
            notes=d.get("notes", ""),
        )


@dataclass(frozen=True)
class TaskSpec:
    """
    Complete task specification for the harness. Immutable after creation.
    """
    name: str
    task: str
    constraints: tuple[str, ...]
    description: str = ""
    environment: str = "development"
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    iteration: IterationConfig = field(default_factory=IterationConfig)
    metadata: TaskMetadata = field(default_factory=TaskMetadata)

    def __post_init__(self):
        if not self.name:
            raise ValueError("Task spec requires a name")
        if not self.task:
            raise ValueError("Task spec requires a task description")
        if not self.constraints:
            raise ValueError("Task spec requires at least one constraint")

    @classmethod
    def from_yaml(cls, path: str | Path) -> TaskSpec:
        import yaml
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Task spec not found: {path}")
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, d: dict) -> TaskSpec:
        return cls(
            name=d["name"],
            task=d["task"],
            constraints=tuple(d["constraints"]),
            description=d.get("description", ""),
            environment=d.get("environment", "development"),
            verification=VerificationConfig.from_dict(d.get("verification")),
            iteration=IterationConfig.from_dict(d.get("iteration")),
            metadata=TaskMetadata.from_dict(d.get("metadata")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "task": self.task,
            "constraints": list(self.constraints),
            "description": self.description,
            "environment": self.environment,
            "verification": {
                "mode": self.verification.mode,
                "files": list(self.verification.files),
                "exclude": list(self.verification.exclude),
            },
            "iteration": {
                "enabled": self.iteration.enabled,
                "max_iterations": self.iteration.max_iterations,
            },
            "metadata": {
                "difficulty": self.metadata.difficulty,
                "category": self.metadata.category,
                "tags": list(self.metadata.tags),
                "expected_traps": list(self.metadata.expected_traps),
                "notes": self.metadata.notes,
            },
        }
