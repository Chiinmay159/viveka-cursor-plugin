#!/usr/bin/env python3
"""
Viveka Hook Adapter — Bridge between Cursor hooks and MicroDecisionEngine.

Cursor sends JSON via stdin. This script evaluates the action through
the deterministic micro-engine and returns a Cursor hook response.

No LLM calls. No network. Runs in milliseconds.

Hook responses:
  {"permission": "allow"}                    — proceed
  {"permission": "ask", "user_message": ...} — ask user
  {"permission": "deny", "agent_message": ...} — block
"""

import json
import os
import sys
import tempfile
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
sys.path.insert(0, str(RUNTIME_DIR))

STATE_FILE = Path(tempfile.gettempdir()) / "viveka-session-state.json"


def get_hook_event():
    """Detect which hook event invoked us via VIVEKA_HOOK_EVENT env var."""
    return os.environ.get("VIVEKA_HOOK_EVENT", "unknown")


def load_micro_engine():
    """Load or initialize the MicroDecisionEngine from session state."""
    from viveka.micro import MicroDecisionEngine
    from viveka.models.core import (
        Environment,
        EnvironmentState,
        RiskMode,
        TaskContext,
        Intent,
        Urgency,
        Reversibility,
    )
    from viveka.layers.scanner import scan_environment
    from viveka.layers.assessor import assess_context, assign_risk_mode

    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            env_state = scan_environment(
                repo_path=state.get("repo_path", "."),
                environment=Environment(state.get("environment", "development")),
            )
            context = assess_context(
                task=state.get("task", "cursor agent session"),
                intent=Intent(state.get("intent", "feature")),
                urgency=Urgency(state.get("urgency", "medium")),
                reversibility=Reversibility(state.get("reversibility", "high")),
            )
            risk_mode = assign_risk_mode(env_state, context)
            return MicroDecisionEngine(
                environment=env_state,
                context=context,
                risk_mode=risk_mode,
            )
        except Exception:
            pass

    env_state = scan_environment(repo_path=".", environment=Environment.DEVELOPMENT)
    context = assess_context(task="cursor agent session", intent=Intent.FEATURE)
    risk_mode = assign_risk_mode(env_state, context)
    return MicroDecisionEngine(
        environment=env_state,
        context=context,
        risk_mode=risk_mode,
    )


def handle_session_start(payload: dict) -> dict:
    """Initialize session state on sessionStart."""
    state = {
        "repo_path": payload.get("cwd", "."),
        "environment": "development",
        "intent": "feature",
        "urgency": "medium",
        "reversibility": "high",
    }
    STATE_FILE.write_text(json.dumps(state))
    return {"continue": True}


def handle_session_end(payload: dict) -> dict:
    """Clean up session state."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    return {"continue": True}


def handle_pre_tool_use(payload: dict) -> dict:
    """Evaluate a tool call through the micro-engine."""
    from viveka.micro import Verdict

    tool_name = payload.get("tool", "")
    tool_input = payload.get("input", {})

    action = build_action_string(tool_name, tool_input)
    if not action:
        return {"continue": True, "permission": "allow"}

    engine = load_micro_engine()
    decision = engine.evaluate(action)

    if decision.verdict == Verdict.PERMIT:
        return {"continue": True, "permission": "allow"}
    elif decision.verdict == Verdict.WARN:
        return {
            "continue": True,
            "permission": "allow",
            "agent_message": f"[viveka] Warning: {decision.reason}",
        }
    elif decision.verdict == Verdict.BLOCK:
        return {
            "continue": True,
            "permission": "deny",
            "agent_message": f"[viveka] Blocked: {decision.reason}. {'; '.join(decision.suggestions)}",
        }
    elif decision.verdict == Verdict.ESCALATE:
        return {
            "continue": True,
            "permission": "ask",
            "user_message": f"Viveka governance: {decision.reason}",
            "agent_message": f"[viveka] Escalated to user: {decision.reason}",
        }

    return {"continue": True, "permission": "allow"}


def handle_before_shell(payload: dict) -> dict:
    """Evaluate a shell command through the micro-engine."""
    from viveka.micro import Verdict

    command = payload.get("command", "")
    if not command:
        return {"continue": True, "permission": "allow"}

    engine = load_micro_engine()
    decision = engine.evaluate(f"run_command {command}")

    if decision.verdict == Verdict.PERMIT:
        return {"continue": True, "permission": "allow"}
    elif decision.verdict == Verdict.WARN:
        return {
            "continue": True,
            "permission": "allow",
            "agent_message": f"[viveka] Warning: {decision.reason}",
        }
    elif decision.verdict == Verdict.BLOCK:
        return {
            "continue": True,
            "permission": "deny",
            "agent_message": f"[viveka] Blocked: {decision.reason}",
        }
    elif decision.verdict == Verdict.ESCALATE:
        return {
            "continue": True,
            "permission": "ask",
            "user_message": f"Viveka governance: {decision.reason}",
        }

    return {"continue": True, "permission": "allow"}


def handle_after_file_edit(payload: dict) -> dict:
    """Post-edit audit — log the edit, no blocking."""
    return {"continue": True}


def build_action_string(tool_name: str, tool_input: dict) -> str:
    """Convert Cursor tool call into a micro-engine action string."""
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


HANDLERS = {
    "sessionStart": handle_session_start,
    "sessionEnd": handle_session_end,
    "stop": handle_session_end,
    "preToolUse": handle_pre_tool_use,
    "beforeShellExecution": handle_before_shell,
    "afterFileEdit": handle_after_file_edit,
}


def main():
    payload = json.load(sys.stdin)
    event = get_hook_event()
    handler = HANDLERS.get(event, lambda p: {"continue": True})
    response = handler(payload)
    json.dump(response, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        json.dump({"continue": True}, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()
