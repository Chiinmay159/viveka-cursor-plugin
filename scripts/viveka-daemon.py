#!/usr/bin/env python3
"""
Viveka Governance Daemon — persistent process for hook evaluations.

Started once on sessionStart, stays alive for the entire Cursor session.
Accepts evaluation requests over a Unix domain socket.
All heavy imports (pydantic, viveka runtime) happen once at startup.

The actual evaluate() call takes ~0.01ms. By keeping this process alive,
we avoid the ~550ms per-call cost of spawning Python + importing pydantic
on every hook invocation.
"""

import json
import os
import re
import signal
import socket
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
sys.path.insert(0, str(RUNTIME_DIR))

def _session_paths(session_hash: str = "default"):
    """Derive per-session socket/pid/ready paths from a cwd hash."""
    tmpdir = Path(tempfile.gettempdir())
    return (
        tmpdir / f"viveka-daemon-{session_hash}.sock",
        tmpdir / f"viveka-daemon-{session_hash}.pid",
        tmpdir / f"viveka-daemon-{session_hash}.ready",
    )

# Module-level defaults — overridden in main() from argv.
SOCKET_PATH, PID_FILE, READY_FILE = _session_paths()

_POSTURE_MODE_OVERRIDE = {
    "exploratory": "permissive",
    "speed":       "permissive",
    "adversarial": "guarded",
}

_INTENT_PATTERNS = [
    (r"\b(fix|bug|error|crash|broken|patch|hotfix)\b",       "fix"),
    (r"\b(recover|rollback|revert|incident|outage)\b",       "recovery"),
    (r"\b(explor|spike|prototype|research|investigat)",       "exploration"),
    (r"\b(refactor|optimiz|improv|clean.?up|perf)",           "improvement"),
    (r"\b(updat|upgrad|depend|migrat|deprecat|maint)",        "maintenance"),
]


def _detect_intent(task: str) -> str:
    lower = task.lower()
    for pattern, intent in _INTENT_PATTERNS:
        if re.search(pattern, lower):
            return intent
    return "feature"


class Daemon:
    """Holds the warm engine and handles requests."""

    def __init__(self):
        self.engine = None
        self.Verdict = None
        self.RiskMode = None
        self.posture = "standard"
        self.cwd = "."
        self.task = ""
        self.policy_name = ""
        self.session = None

    def initialize(self, payload: dict):
        """One-time heavy init: import, scan, build engine, apply policy."""
        from viveka.micro import MicroDecisionEngine, Verdict, _LIMITS
        from viveka.models.core import (
            Environment, RiskMode, Intent, Urgency, Reversibility,
        )
        from viveka.layers.scanner import scan_environment
        from viveka.layers.assessor import assess_context, assign_risk_mode
        from viveka.policies import get_policy

        self.Verdict = Verdict
        self.RiskMode = RiskMode

        self.task = payload.get("task", payload.get("description", "cursor agent session"))
        self.cwd = payload.get("cwd", ".")
        intent_str = _detect_intent(self.task)
        self.posture = payload.get("posture", "standard")
        self.policy_name = payload.get("policy", "")

        env_state = scan_environment(
            repo_path=self.cwd,
            environment=Environment.DEVELOPMENT,
        )
        context = assess_context(
            task=self.task,
            intent=Intent(intent_str),
            urgency=Urgency.MEDIUM,
            reversibility=Reversibility.HIGH,
        )
        computed_mode = assign_risk_mode(env_state, context)

        override = _POSTURE_MODE_OVERRIDE.get(self.posture)
        risk_mode = RiskMode(override) if override else computed_mode

        # Apply PolicyPack if specified in payload or .viveka/policy.yaml
        policy = None
        if self.policy_name:
            policy = get_policy(self.policy_name)
        else:
            policy_file = Path(self.cwd) / ".viveka" / "policy.yaml"
            if policy_file.exists():
                try:
                    import yaml
                    with open(policy_file) as f:
                        policy_data = yaml.safe_load(f)
                    policy_name = policy_data.get("policy", "")
                    if policy_name:
                        policy = get_policy(policy_name)
                        self.policy_name = policy_name
                except Exception:
                    pass

        if policy:
            if policy.risk_mode:
                risk_mode = policy.risk_mode

        self.engine = MicroDecisionEngine(
            environment=env_state,
            context=context,
            risk_mode=risk_mode,
        )

        # Apply PolicyPack overrides
        if policy:
            limits = dict(_LIMITS[risk_mode])
            if policy.max_retries is not None:
                limits["max_retries"] = policy.max_retries
            if policy.max_files_modified is not None:
                limits["max_files_modified"] = policy.max_files_modified
            if policy.max_actions is not None:
                limits["max_actions"] = policy.max_actions
            self.engine._limits = limits

            if policy.blocked_paths:
                self.engine.env.permissions.blocked_paths = list(
                    set(self.engine.env.permissions.blocked_paths + policy.blocked_paths)
                )
            if policy.blocked_tools:
                self.engine.env.permissions.blocked_tools = list(
                    set(self.engine.env.permissions.blocked_tools + policy.blocked_tools)
                )

        # Initialize GovernedSession for session-level tracking
        try:
            from viveka.session import GovernedSession
            self.session = GovernedSession(
                micro=self.engine,
                task=self.task,
                known_constraints=policy.constraints if policy else [],
            )
        except Exception:
            self.session = None

    def update_posture(self, new_posture: str) -> dict:
        """Update the enforcement mode based on a new cognitive posture."""
        if not self.engine or not self.RiskMode:
            return {"updated": False, "reason": "engine not initialized"}

        from viveka.micro import _LIMITS

        self.posture = new_posture
        override = _POSTURE_MODE_OVERRIDE.get(new_posture)
        if override:
            new_mode = self.RiskMode(override)
        else:
            new_mode = self.engine.risk_mode

        old_mode = self.engine.risk_mode
        self.engine.risk_mode = new_mode
        self.engine._limits = _LIMITS[new_mode]

        return {
            "updated": True,
            "posture": new_posture,
            "enforcement_mode": new_mode.value,
            "previous_mode": old_mode.value,
        }

    def get_status(self) -> dict:
        """Return daemon health and session summary."""
        result = {
            "alive": True,
            "pid": os.getpid(),
            "posture": self.posture,
            "cwd": self.cwd,
            "task": self.task,
            "policy": self.policy_name,
        }
        if self.engine:
            result["enforcement_mode"] = self.engine.risk_mode.value
            result["session_summary"] = self.engine.get_session_summary()
        else:
            result["enforcement_mode"] = "unknown"
            result["session_summary"] = {}
        if self.session:
            result["governed_session"] = self.session.get_summary()
        return result

    def check_constraints(self, text: str, constraints: list[str]) -> dict:
        """Deterministic constraint validation."""
        try:
            from viveka.constraints import validate_against_constraints
            violations = validate_against_constraints(text, constraints)
            return {
                "valid": len(violations) == 0,
                "violations": violations,
                "checked_constraints": len(constraints),
            }
        except ImportError:
            return {"valid": True, "violations": [], "error": "constraints module not available"}

    def get_scenarios(self, risk_mode_str: str = "") -> dict:
        """Return applicable adversarial scenarios for current/given risk mode."""
        try:
            from viveka.scenarios import get_applicable_scenarios, SCENARIO_DESCRIPTIONS
            from viveka.models.core import RiskMode
            mode = RiskMode(risk_mode_str) if risk_mode_str else (
                self.engine.risk_mode if self.engine else RiskMode.STANDARD
            )
            scenarios, suppression_log = get_applicable_scenarios(mode)
            return {
                "risk_mode": mode.value,
                "scenarios": [
                    {"id": s.value, "description": SCENARIO_DESCRIPTIONS.get(s, "")}
                    for s in scenarios
                ],
                "suppression_log": suppression_log,
            }
        except ImportError:
            return {"scenarios": [], "error": "scenarios module not available"}

    def _distill_learnings(self, summary: dict) -> list[str]:
        """Extract correction rules from the governance trace.

        Deterministic — no LLM calls. Reads the session's own behavioral
        record and produces actionable learnings. This closes the trust
        boundary: the daemon observed these events directly, the agent
        cannot omit or rewrite them.
        """
        learnings = []

        # Retry patterns that hit the limit → failed approaches
        for pattern, count in summary.get("retry_patterns", {}).items():
            max_retries = self._limits.get("max_retries", 3) if hasattr(self, '_limits') else 3
            if count >= max_retries:
                learnings.append(
                    f"Approach failed: '{pattern}' was retried {count} times "
                    f"and hit the retry limit. Avoid this pattern next session."
                )

        # Blocks that fired → hard constraints the agent hit
        if self.session:
            blocked_actions = [
                a for a in self.session.actions
                if a.verdict.value == "block"
            ]
            # Deduplicate by rule
            seen_rules = set()
            for action in blocked_actions:
                if action.rule not in seen_rules:
                    seen_rules.add(action.rule)
                    learnings.append(
                        f"Action blocked by {action.rule}: {action.reason}. "
                        f"Action was: '{action.action}'."
                    )

        # Scope creep signal
        files_modified = summary.get("files_modified", 0)
        max_files = self.engine._limits.get("max_files_modified", 15) if self.engine else 15
        if files_modified > max_files * 0.8:
            learnings.append(
                f"Scope creep: {files_modified} files modified "
                f"(limit: {max_files}). Break large changes into "
                f"smaller, focused commits next time."
            )

        # Warning accumulation signal
        warnings = summary.get("warnings", 0)
        if warnings >= 5:
            learnings.append(
                f"Session accumulated {warnings} governance warnings. "
                f"Review the checkpoint trace to identify recurring issues."
            )

        # Escalation signal
        if self.session and self.session.escalation_count > 0:
            learnings.append(
                f"{self.session.escalation_count} action(s) escalated to "
                f"human during this session. Consider tightening the "
                f"approach or switching posture for similar tasks."
            )

        return learnings

    def _write_auto_memory(self, learnings: list[str], now: datetime):
        """Write daemon-distilled learnings to .viveka/memory/.

        These entries are tagged 'generated: daemon' to distinguish them
        from agent-written memories. They cannot be omitted or rewritten
        by the agent — the daemon observed the events directly.
        """
        memory_dir = Path(self.cwd) / ".viveka" / "memory"
        try:
            memory_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return

        slug = f"session-{now.strftime('%H%M%S')}"
        filename = f"{now.strftime('%Y-%m-%d')}-{slug}.md"

        lines = [
            f"# Session learnings — {now.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"**Task:** {self.task}",
            f"**Posture:** {self.posture}",
            f"**Enforcement mode:** {self.engine.risk_mode.value}",
            f"**Source:** daemon (auto-distilled from governance trace)",
            "",
            "## Correction rules",
            "",
        ]
        for i, learning in enumerate(learnings, 1):
            lines.append(f"{i}. {learning}")

        lines.append("")

        try:
            (memory_dir / filename).write_text("\n".join(lines))
        except OSError:
            pass

    def write_session_checkpoint(self):
        """Write a session trace to .viveka/checkpoints/ on shutdown."""
        if not self.engine:
            return
        summary = self.engine.get_session_summary()
        if summary["total_actions"] < 3:
            return

        checkpoint_dir = Path(self.cwd) / ".viveka" / "checkpoints"
        try:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return

        now = datetime.now()
        filename = f"{now.strftime('%Y-%m-%d')}-session-{now.strftime('%H%M%S')}.json"
        checkpoint = {
            "type": "session-checkpoint",
            "generated": "auto",
            "timestamp": now.isoformat(),
            "posture": self.posture,
            "policy": self.policy_name,
            "enforcement_mode": self.engine.risk_mode.value,
            "task": self.task,
            "cwd": self.cwd,
            "summary": summary,
            "files_modified": sorted(self.engine.session.files_modified),
        }
        if self.session:
            checkpoint["session_trace"] = self.session.get_trace()
        try:
            (checkpoint_dir / filename).write_text(json.dumps(checkpoint, indent=2))
        except OSError:
            pass

        # Auto-distill learnings from the trace — closes the trust boundary.
        # The agent can still write its own memories via viveka_memory_write,
        # but these daemon-generated entries exist regardless.
        learnings = self._distill_learnings(summary)
        if learnings:
            self._write_auto_memory(learnings, now)

    def evaluate(self, action: str) -> dict:
        """Evaluate an action. Returns Cursor hook response."""
        if not self.engine:
            return {"continue": True, "permission": "allow"}

        if self.session:
            result = self.session.propose(action)
            V = self.Verdict
            if result.verdict == V.PERMIT:
                return {"continue": True, "permission": "allow"}
            elif result.verdict == V.WARN:
                return {
                    "continue": True,
                    "permission": "allow",
                    "agent_message": f"[viveka] Warning: {result.reason}",
                }
            elif result.verdict == V.BLOCK:
                return {
                    "continue": True,
                    "permission": "deny",
                    "agent_message": f"[viveka] Blocked: {result.reason}. {'; '.join(result.suggestions)}",
                }
            elif result.verdict == V.ESCALATE:
                return {
                    "continue": True,
                    "permission": "ask",
                    "user_message": f"Viveka governance: {result.reason}",
                    "agent_message": f"[viveka] Escalated to user: {result.reason}",
                }
            return {"continue": True, "permission": "allow"}

        decision = self.engine.evaluate(action)
        V = self.Verdict

        if decision.verdict == V.PERMIT:
            return {"continue": True, "permission": "allow"}
        elif decision.verdict == V.WARN:
            return {
                "continue": True,
                "permission": "allow",
                "agent_message": f"[viveka] Warning: {decision.reason}",
            }
        elif decision.verdict == V.BLOCK:
            return {
                "continue": True,
                "permission": "deny",
                "agent_message": f"[viveka] Blocked: {decision.reason}. {'; '.join(decision.suggestions)}",
            }
        elif decision.verdict == V.ESCALATE:
            return {
                "continue": True,
                "permission": "ask",
                "user_message": f"Viveka governance: {decision.reason}",
                "agent_message": f"[viveka] Escalated to user: {decision.reason}",
            }
        return {"continue": True, "permission": "allow"}

    def handle_request(self, request: dict) -> dict:
        event = request.get("event", "")
        payload = request.get("payload", {})

        if event == "sessionStart":
            self.initialize(payload)
            return {"continue": True}

        if event in ("stop", "sessionEnd"):
            self.write_session_checkpoint()
            return {"continue": True, "_shutdown": True}

        if event == "status":
            return {"continue": True, **self.get_status()}

        if event == "postureUpdate":
            new_posture = payload.get("posture", "standard")
            result = self.update_posture(new_posture)
            return {"continue": True, **result}

        if event == "constraintCheck":
            text = payload.get("text", "")
            constraints = payload.get("constraints", [])
            result = self.check_constraints(text, constraints)
            return {"continue": True, **result}

        if event == "scenarios":
            risk_mode = payload.get("risk_mode", "")
            result = self.get_scenarios(risk_mode)
            return {"continue": True, **result}

        if event == "sessionTrace":
            if self.session:
                return {"continue": True, "trace": self.session.get_trace()}
            return {"continue": True, "trace": None}

        if event == "preToolUse":
            tool_name = payload.get("tool", "")
            tool_input = payload.get("input", {})
            action = _build_action_string(tool_name, tool_input)
            if not action:
                return {"continue": True, "permission": "allow"}
            return self.evaluate(action)

        if event == "beforeShellExecution":
            command = payload.get("command", "")
            if not command:
                return {"continue": True, "permission": "allow"}
            return self.evaluate(f"run_command {command}")

        if event == "afterFileEdit":
            filepath = payload.get("path", "")
            if filepath and self.engine:
                self.engine.record_file_modified(filepath)
            return {"continue": True}

        return {"continue": True}


def _build_action_string(tool_name: str, tool_input: dict) -> str:
    name = tool_name.lower()
    if "write" in name or "edit" in name or "create" in name:
        path = tool_input.get("path", tool_input.get("filePath", "unknown"))
        return f"write_file {path}"
    elif "read" in name:
        path = tool_input.get("path", tool_input.get("filePath", "unknown"))
        return f"read_file {path}"
    elif "shell" in name or "terminal" in name or "command" in name:
        cmd = tool_input.get("command", "unknown")
        return f"run_command {cmd}"
    elif "search" in name or "grep" in name or "glob" in name:
        query = tool_input.get("pattern", tool_input.get("query", ""))
        return f"search_code {query}"
    return ""


def cleanup():
    for f in (SOCKET_PATH, PID_FILE, READY_FILE):
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass


def main():
    global SOCKET_PATH, PID_FILE, READY_FILE

    # Accept session hash from hook (argv[2]) for per-project isolation.
    session_hash = sys.argv[2] if len(sys.argv) > 2 else "default"
    SOCKET_PATH, PID_FILE, READY_FILE = _session_paths(session_hash)

    cleanup()

    daemon = Daemon()

    if len(sys.argv) > 1:
        try:
            init_payload = json.loads(sys.argv[1])
            daemon.initialize(init_payload)
        except Exception:
            pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(SOCKET_PATH))
    sock.listen(5)
    sock.settimeout(300)

    PID_FILE.write_text(str(os.getpid()))
    READY_FILE.write_text("1")

    def handle_signal(signum, frame):
        daemon.write_session_checkpoint()
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        while True:
            try:
                conn, _ = sock.accept()
            except socket.timeout:
                daemon.write_session_checkpoint()
                break

            try:
                conn.settimeout(5)
                data = b""
                while b"\n" not in data:
                    chunk = conn.recv(8192)
                    if not chunk:
                        break
                    data += chunk

                if data:
                    request = json.loads(data.decode().strip())
                    response = daemon.handle_request(request)
                    should_shutdown = response.pop("_shutdown", False)
                    conn.sendall(json.dumps(response).encode() + b"\n")
                    conn.close()
                    if should_shutdown:
                        break
                else:
                    conn.close()
            except Exception:
                try:
                    conn.sendall(json.dumps({"continue": True}).encode() + b"\n")
                    conn.close()
                except Exception:
                    pass
    finally:
        sock.close()
        cleanup()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        cleanup()
