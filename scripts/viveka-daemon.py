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
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
sys.path.insert(0, str(RUNTIME_DIR))

SOCKET_PATH = Path(tempfile.gettempdir()) / "viveka-daemon.sock"
PID_FILE = Path(tempfile.gettempdir()) / "viveka-daemon.pid"
READY_FILE = Path(tempfile.gettempdir()) / "viveka-daemon.ready"

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

    def initialize(self, payload: dict):
        """One-time heavy init: import, scan, build engine."""
        from viveka.micro import MicroDecisionEngine, Verdict
        from viveka.models.core import (
            Environment, RiskMode, Intent, Urgency, Reversibility,
        )
        from viveka.layers.scanner import scan_environment
        from viveka.layers.assessor import assess_context, assign_risk_mode

        self.Verdict = Verdict

        task = payload.get("task", payload.get("description", "cursor agent session"))
        repo_path = payload.get("cwd", ".")
        intent_str = _detect_intent(task)
        posture = payload.get("posture", "standard")

        env_state = scan_environment(
            repo_path=repo_path,
            environment=Environment.DEVELOPMENT,
        )
        context = assess_context(
            task=task,
            intent=Intent(intent_str),
            urgency=Urgency.MEDIUM,
            reversibility=Reversibility.HIGH,
        )
        computed_mode = assign_risk_mode(env_state, context)

        override = _POSTURE_MODE_OVERRIDE.get(posture)
        risk_mode = RiskMode(override) if override else computed_mode

        self.engine = MicroDecisionEngine(
            environment=env_state,
            context=context,
            risk_mode=risk_mode,
        )

    def evaluate(self, action: str) -> dict:
        """Evaluate an action. Returns Cursor hook response."""
        if not self.engine:
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
            return {"continue": True, "_shutdown": True}

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
    cleanup()

    daemon = Daemon()

    # If sessionStart payload was passed as arg, initialize immediately
    if len(sys.argv) > 1:
        try:
            init_payload = json.loads(sys.argv[1])
            daemon.initialize(init_payload)
        except Exception:
            pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(str(SOCKET_PATH))
    sock.listen(5)
    sock.settimeout(300)  # 5-minute idle timeout

    PID_FILE.write_text(str(os.getpid()))
    READY_FILE.write_text("1")

    def handle_signal(signum, frame):
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        while True:
            try:
                conn, _ = sock.accept()
            except socket.timeout:
                break  # idle too long, exit

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
