"""
Viveka Harness — Agent-agnostic test & comparison framework.

Declarative task specs, CLI agent adapters, structured verification results,
and comparison matrices. The harness wraps ANY agent CLI and measures
constraint satisfaction across iterations.

No LLM dependency — verification can be done by external tools,
test assertions, or LLM-based verifiers injected by the caller.
"""

from viveka.harness.task import TaskSpec, VerificationConfig, IterationConfig
from viveka.harness.agents import AgentAdapter, AgentRegistry, ExecutionResult
from viveka.harness.results import AgentRun, HarnessResult, IterationRecord
