#!/usr/bin/env python3
"""
Viveka MCP Server — Decision tools for Cursor agents.

Exposes deterministic governance tools via Model Context Protocol.
No LLM calls. No external dependencies. All local.

Tools:
  viveka_check           — Quick governance check for a proposed action
  viveka_memory_read     — Search .viveka/memory/ for relevant past learnings
  viveka_memory_write    — Write a task memory entry
  viveka_session_state   — Read current session governance state
  viveka_status          — Layer health check (daemon, MCP, session)
  viveka_update_posture  — Update enforcement mode via posture change
  viveka_constraint_check — Validate text against user-declared hard constraints
  viveka_scenarios       — Get applicable adversarial failure scenarios
  viveka_policies        — List available governance PolicyPacks
  viveka_session_trace   — Export governed session trace
"""

import hashlib
import json
import os
import socket
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
sys.path.insert(0, str(RUNTIME_DIR))

def _session_hash() -> str:
    """Derive per-project session hash from cwd, matching viveka-hook.sh."""
    return hashlib.sha1(os.getcwd().encode()).hexdigest()[:12]

_HASH = _session_hash()
SOCKET_PATH = Path(tempfile.gettempdir()) / f"viveka-daemon-{_HASH}.sock"
PID_FILE = Path(tempfile.gettempdir()) / f"viveka-daemon-{_HASH}.pid"
STATE_FILE = Path(tempfile.gettempdir()) / f"viveka-session-state-{_HASH}.json"
OBS_FILE = Path(".viveka") / "observations.jsonl"


def _log_mcp_tool_call(tool_name: str, tool_args: dict, result: dict):
    """Phase 0 observation — append MCP tool usage to observations.jsonl."""
    entry = {
        "session_id": _HASH,
        "timestamp": datetime.now().isoformat(),
        "event": "mcp_tool_call",
        "tool": tool_name,
        "has_error": result.get("isError", False),
    }
    try:
        OBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OBS_FILE, "a") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except OSError:
        pass

TOOL_DEFINITIONS = [
    {
        "name": "viveka_check",
        "description": (
            "Quick governance check for a proposed action. Returns a list of "
            "violations (empty = safe to proceed). No LLM cost. Use before "
            "irreversible actions, destructive shell commands, or writes to "
            "sensitive paths."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "The action to check, e.g. 'write_file src/auth.py' or 'run_command rm -rf dist/'",
                },
            },
            "required": ["action"],
        },
    },
    {
        "name": "viveka_memory_read",
        "description": (
            "Search all Viveka memory locations for relevant past learnings: "
            "project-local .viveka/memory/ and .viveka/framework-memory/active/, "
            "plus user-global ~/.viveka/traces/ and ~/.viveka/policies/. "
            "Returns correction rules, loop-back records, governance traces, "
            "and insights matching the query. Use during Context stage."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms — project name, domain, error pattern, or stage name",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum entries to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "viveka_memory_write",
        "description": (
            "Write a task memory entry to .viveka/memory/. Use during "
            "Catalogue stage to persist insights, correction rules, and "
            "loop-back records for future sessions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "Short task identifier, e.g. 'fix-auth-token-refresh'",
                },
                "content": {
                    "type": "string",
                    "description": "Full markdown content of the task memory entry",
                },
            },
            "required": ["slug", "content"],
        },
    },
    {
        "name": "viveka_session_state",
        "description": (
            "Read the current session governance state — enforcement mode "
            "(permissive/standard/guarded/restricted), cognitive posture "
            "(standard/exploratory/speed/adversarial), detected intent, "
            "and task context. Shows what governance constraints are active."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "viveka_status",
        "description": (
            "Health check across all Viveka layers. Reports whether the "
            "cognitive layer (Layer 1), enforcement daemon (Layer 2), and "
            "MCP tools (Layer 3) are active. Includes daemon PID, current "
            "enforcement mode, and session summary if the daemon is running."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "viveka_update_posture",
        "description": (
            "Update the cognitive posture mid-session. Syncs the change to "
            "the enforcement daemon so the risk mode adjusts immediately. "
            "Valid postures: standard, exploratory, speed, adversarial."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "posture": {
                    "type": "string",
                    "description": "New posture: standard, exploratory, speed, or adversarial",
                    "enum": ["standard", "exploratory", "speed", "adversarial"],
                },
            },
            "required": ["posture"],
        },
    },
    {
        "name": "viveka_constraint_check",
        "description": (
            "Validate text against user-declared hard constraints. "
            "Returns violations (empty = valid). Deterministic keyword matching — "
            "catches obvious constraint violations like using SQLite when "
            "constraint says 'threading primitives only'. No LLM cost."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to validate (strategy description, proposed action, etc.)",
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Hard constraints to check against, e.g. ['no external dependencies', 'threading primitives only']",
                },
            },
            "required": ["text", "constraints"],
        },
    },
    {
        "name": "viveka_scenarios",
        "description": (
            "Get applicable adversarial failure scenarios for the current "
            "enforcement mode. Returns scenario IDs and descriptions from "
            "the 10-scenario taxonomy (tool_failure, stale_context, "
            "deceptive_completion, etc.). Use during Architecture stage "
            "to identify what could go wrong."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "risk_mode": {
                    "type": "string",
                    "description": "Override risk mode (default: current session mode)",
                    "enum": ["permissive", "standard", "guarded", "restricted"],
                },
            },
        },
    },
    {
        "name": "viveka_policies",
        "description": (
            "List available governance PolicyPacks. Returns built-in packs "
            "(production-hotfix, refactor-safe, cleanup, data-migration, "
            "incident-response) and any user-defined packs from "
            "~/.viveka/policies/. Shows name, description, risk mode, "
            "and key constraints for each."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "viveka_session_trace",
        "description": (
            "Export the full governed session trace — every action, verdict, "
            "escalation, and their outcomes as a linked chain. Shows the "
            "complete decision history for the current session."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _send_to_daemon(event: str, payload: dict = None) -> dict | None:
    """Send a request to the daemon over the Unix socket."""
    if not SOCKET_PATH.exists():
        return None
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(str(SOCKET_PATH))
        request = json.dumps({"event": event, "payload": payload or {}})
        sock.sendall(request.encode() + b"\n")
        data = b""
        while b"\n" not in data:
            chunk = sock.recv(8192)
            if not chunk:
                break
            data += chunk
        sock.close()
        if data:
            return json.loads(data.decode().strip())
    except Exception:
        pass
    return None


def _daemon_alive() -> bool:
    """Check if daemon process is running."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        return False


def handle_viveka_check(args: dict) -> dict:
    """Evaluate an action through the micro-decision engine."""
    action = args.get("action", "")
    if not action:
        return {"content": [{"type": "text", "text": "No action provided."}]}

    daemon_resp = _send_to_daemon("preToolUse", {"tool": "check", "input": {"action": action}})
    if daemon_resp and "permission" in daemon_resp:
        verdict_map = {"allow": "permit", "deny": "block", "ask": "escalate"}
        result = {
            "verdict": verdict_map.get(daemon_resp["permission"], "permit"),
            "action": action,
            "reason": daemon_resp.get("agent_message", ""),
            "permitted": daemon_resp["permission"] == "allow",
            "source": "daemon",
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    try:
        from viveka.micro import MicroDecisionEngine
        from viveka.models.core import Environment
        from viveka.layers.scanner import scan_environment
        from viveka.layers.assessor import assess_context, assign_risk_mode

        env_state = scan_environment(repo_path=".", environment=Environment.DEVELOPMENT)
        context = assess_context(task="cursor agent session")
        risk_mode = assign_risk_mode(env_state, context)
        engine = MicroDecisionEngine(
            environment=env_state, context=context, risk_mode=risk_mode,
        )

        decision = engine.evaluate(action)
        result = {
            "verdict": decision.verdict.value,
            "action": decision.action,
            "reason": decision.reason,
            "rule": decision.rule,
            "suggestions": decision.suggestions,
            "permitted": decision.permitted,
            "source": "standalone",
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    except ImportError:
        return {"content": [{"type": "text", "text": "Viveka runtime not available. Action not checked."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Check failed: {e}. Action not blocked."}]}


def handle_viveka_memory_read(args: dict) -> dict:
    """Search all Viveka memory locations for relevant entries."""
    query = args.get("query", "").lower()
    max_results = args.get("max_results", 5)

    home = Path.home()
    plugin_dir = Path(__file__).resolve().parent.parent
    search_dirs = [
        (str(plugin_dir / ".viveka" / "framework-memory" / "active"), "framework-memory"),
        (".viveka/memory",                  "task-memory"),
        (str(home / ".viveka" / "traces"),  "governance-trace"),
        (str(home / ".viveka" / "policies"),"policy"),
    ]

    results = []
    for search_dir, source_label in search_dirs:
        dir_path = Path(search_dir)
        if not dir_path.exists():
            continue
        for entry in sorted(dir_path.glob("*.md"), reverse=True):
            try:
                content = entry.read_text()
                content_lower = content.lower()
                if query and not any(term in content_lower for term in query.split()):
                    continue
                results.append({
                    "file": str(entry),
                    "source": source_label,
                    "content": content[:2000],
                })
                if len(results) >= max_results:
                    break
            except Exception:
                continue
        if len(results) >= max_results:
            break

    traces_dir = home / ".viveka" / "traces"
    if traces_dir.exists() and len(results) < max_results:
        for entry in sorted(traces_dir.glob("*.json"), reverse=True):
            try:
                content = entry.read_text()
                content_lower = content.lower()
                if query and not any(term in content_lower for term in query.split()):
                    continue
                results.append({
                    "file": str(entry),
                    "source": "governance-trace",
                    "content": content[:2000],
                })
                if len(results) >= max_results:
                    break
            except Exception:
                continue

    if not results:
        dirs_searched = [d for d, _ in search_dirs]
        text = f"No memory entries found matching '{query}'. Directories searched: {dirs_searched}"
    else:
        text = json.dumps(results, indent=2)

    return {"content": [{"type": "text", "text": text}]}


def handle_viveka_memory_write(args: dict) -> dict:
    """Write a task memory entry to .viveka/memory/."""
    slug = args.get("slug", "")
    content = args.get("content", "")

    if not slug or not content:
        return {"content": [{"type": "text", "text": "Both slug and content are required."}]}

    memory_dir = Path(".viveka/memory")
    memory_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}-{slug}.md"
    filepath = memory_dir / filename

    filepath.write_text(content)
    return {"content": [{"type": "text", "text": f"Written to {filepath}"}]}


def handle_viveka_session_state(args: dict) -> dict:
    """Read current session governance state with unified labels."""
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())

            posture = state.get("posture", "standard")
            posture_overrides = {
                "exploratory": "permissive",
                "speed": "permissive",
                "adversarial": "guarded",
            }
            try:
                from viveka.models.core import Environment, Intent, Urgency, Reversibility
                from viveka.layers.scanner import scan_environment
                from viveka.layers.assessor import assess_context, assign_risk_mode
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
                computed = assign_risk_mode(env_state, context).value
            except Exception:
                computed = "standard"

            effective = posture_overrides.get(posture, computed)
            state["enforcement_mode"] = effective
            state["enforcement_mode_computed"] = computed
            if posture in posture_overrides:
                state["enforcement_mode_reason"] = f"overridden by {posture} posture"

            return {"content": [{"type": "text", "text": json.dumps(state, indent=2)}]}
        except Exception:
            pass

    return {"content": [{"type": "text", "text": "No active session state. Session may not have started yet."}]}


def handle_viveka_status(args: dict) -> dict:
    """Health check across all Viveka layers."""
    result = {
        "layer1_cognitive": "active",
        "layer2_daemon": "inactive",
        "layer3_mcp": "active",
    }

    if _daemon_alive():
        result["layer2_daemon"] = "active"
        try:
            result["layer2_pid"] = int(PID_FILE.read_text().strip())
        except Exception:
            pass

        daemon_resp = _send_to_daemon("status")
        if daemon_resp:
            result["enforcement_mode"] = daemon_resp.get("enforcement_mode", "unknown")
            result["posture"] = daemon_resp.get("posture", "unknown")
            result["session_summary"] = daemon_resp.get("session_summary", {})
    elif PID_FILE.exists():
        result["layer2_daemon"] = "dead (stale PID file)"

    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            result.setdefault("posture", state.get("posture", "standard"))
            result["intent"] = state.get("intent", "feature")
            result["cwd"] = state.get("cwd", state.get("repo_path", "."))
        except Exception:
            pass

    text = json.dumps(result, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def handle_viveka_update_posture(args: dict) -> dict:
    """Update posture and sync to daemon."""
    posture = args.get("posture", "")
    if posture not in ("standard", "exploratory", "speed", "adversarial"):
        return {"content": [{"type": "text", "text": f"Invalid posture: {posture}. Must be standard, exploratory, speed, or adversarial."}]}

    results = []

    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            state["posture"] = posture
            STATE_FILE.write_text(json.dumps(state))
            results.append("State file updated")
        except Exception as e:
            results.append(f"State file update failed: {e}")

    daemon_resp = _send_to_daemon("postureUpdate", {"posture": posture})
    if daemon_resp and daemon_resp.get("updated"):
        results.append(
            f"Daemon updated: {daemon_resp.get('previous_mode')} → {daemon_resp.get('enforcement_mode')}"
        )
    elif daemon_resp:
        results.append(f"Daemon update failed: {daemon_resp.get('reason', 'unknown')}")
    else:
        results.append("Daemon unreachable — posture saved to state file only")

    text = json.dumps({
        "posture": posture,
        "actions": results,
    }, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def handle_viveka_constraint_check(args: dict) -> dict:
    """Deterministic constraint validation."""
    text = args.get("text", "")
    constraints = args.get("constraints", [])
    if not text or not constraints:
        return {"content": [{"type": "text", "text": "Both text and constraints are required."}]}

    daemon_resp = _send_to_daemon("constraintCheck", {
        "text": text, "constraints": constraints,
    })
    if daemon_resp and "violations" in daemon_resp:
        return {"content": [{"type": "text", "text": json.dumps(daemon_resp, indent=2)}]}

    try:
        from viveka.constraints import validate_against_constraints
        violations = validate_against_constraints(text, constraints)
        result = {
            "valid": len(violations) == 0,
            "violations": violations,
            "checked_constraints": len(constraints),
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except ImportError:
        return {"content": [{"type": "text", "text": "Constraint validation module not available."}]}


def handle_viveka_scenarios(args: dict) -> dict:
    """Return applicable adversarial scenarios."""
    risk_mode_str = args.get("risk_mode", "")

    daemon_resp = _send_to_daemon("scenarios", {"risk_mode": risk_mode_str})
    if daemon_resp and "scenarios" in daemon_resp:
        return {"content": [{"type": "text", "text": json.dumps(daemon_resp, indent=2)}]}

    try:
        from viveka.scenarios import get_applicable_scenarios, SCENARIO_DESCRIPTIONS
        from viveka.models.core import RiskMode
        mode = RiskMode(risk_mode_str) if risk_mode_str else RiskMode.STANDARD
        scenarios, suppression_log = get_applicable_scenarios(mode)
        result = {
            "risk_mode": mode.value,
            "scenarios": [
                {"id": s.value, "description": SCENARIO_DESCRIPTIONS.get(s, "")}
                for s in scenarios
            ],
            "suppression_log": suppression_log,
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except ImportError:
        return {"content": [{"type": "text", "text": "Scenarios module not available."}]}


def handle_viveka_policies(args: dict) -> dict:
    """List available PolicyPacks."""
    try:
        from viveka.policies import list_policies, get_policy
        policies = list_policies()
        result = []
        for name, description, source in policies:
            entry = {"name": name, "description": description, "source": source}
            pack = get_policy(name)
            if pack:
                if pack.risk_mode:
                    entry["risk_mode"] = pack.risk_mode.value
                if pack.constraints:
                    entry["constraints"] = pack.constraints
                if pack.max_files_modified is not None:
                    entry["max_files_modified"] = pack.max_files_modified
                if pack.require_human_approval:
                    entry["require_human_approval"] = True
            result.append(entry)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
    except ImportError:
        return {"content": [{"type": "text", "text": "Policies module not available."}]}


def handle_viveka_session_trace(args: dict) -> dict:
    """Export governed session trace."""
    daemon_resp = _send_to_daemon("sessionTrace")
    if daemon_resp and daemon_resp.get("trace"):
        return {"content": [{"type": "text", "text": json.dumps(daemon_resp["trace"], indent=2)}]}

    return {"content": [{"type": "text", "text": "No active governed session. Daemon may not be running."}]}


TOOL_HANDLERS = {
    "viveka_check": handle_viveka_check,
    "viveka_memory_read": handle_viveka_memory_read,
    "viveka_memory_write": handle_viveka_memory_write,
    "viveka_session_state": handle_viveka_session_state,
    "viveka_status": handle_viveka_status,
    "viveka_update_posture": handle_viveka_update_posture,
    "viveka_constraint_check": handle_viveka_constraint_check,
    "viveka_scenarios": handle_viveka_scenarios,
    "viveka_policies": handle_viveka_policies,
    "viveka_session_trace": handle_viveka_session_trace,
}


def handle_request(request: dict) -> dict:
    """Handle a JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "viveka", "version": "3.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOL_DEFINITIONS},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)
        if handler:
            try:
                result = handler(tool_args)
            except Exception as e:
                result = {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
        else:
            result = {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}], "isError": True}

        # Phase 0 observation — log every MCP tool call
        _log_mcp_tool_call(tool_name, tool_args, result)

        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main():
    """MCP stdio transport — read JSON-RPC from stdin, write to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
        except Exception:
            pass


if __name__ == "__main__":
    main()
