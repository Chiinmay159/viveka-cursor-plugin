#!/usr/bin/env python3
"""
Viveka MCP Server — Decision tools for Cursor agents.

Exposes deterministic governance tools via Model Context Protocol.
No LLM calls. No external dependencies. All local.

Tools:
  viveka_check        — Quick invariant check for a proposed action
  viveka_memory_read  — Search .viveka/memory/ for relevant past learnings
  viveka_memory_write — Write a task memory entry
  viveka_session_state — Read current session governance state
"""

import json
import os
import sys
import glob as globmod
import re
import tempfile
from datetime import datetime
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
sys.path.insert(0, str(RUNTIME_DIR))

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
]


def handle_viveka_check(args: dict) -> dict:
    """Evaluate an action through the micro-decision engine."""
    action = args.get("action", "")
    if not action:
        return {"content": [{"type": "text", "text": "No action provided."}]}

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
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    except ImportError:
        return {"content": [{"type": "text", "text": "Viveka runtime not available. Action not checked."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Check failed: {e}. Action not blocked."}]}


def handle_viveka_memory_read(args: dict) -> dict:
    """Search all Viveka memory locations for relevant entries.

    Searches both project-local and user-global directories:
      - .viveka/framework-memory/active  (project, promoted rules)
      - .viveka/memory                   (project, task learnings)
      - ~/.viveka/traces                 (global, governance decision records)
      - ~/.viveka/policies               (global, policy packs)
    """
    query = args.get("query", "").lower()
    max_results = args.get("max_results", 5)

    home = Path.home()
    search_dirs = [
        (".viveka/framework-memory/active", "framework-memory"),
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

    # Also search JSON trace files in ~/.viveka/traces
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
    state_file = Path(tempfile.gettempdir()) / "viveka-session-state.json"

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())

            # Compute the effective enforcement mode for display
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


TOOL_HANDLERS = {
    "viveka_check": handle_viveka_check,
    "viveka_memory_read": handle_viveka_memory_read,
    "viveka_memory_write": handle_viveka_memory_write,
    "viveka_session_state": handle_viveka_session_state,
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
                "serverInfo": {"name": "viveka", "version": "2.1.0"},
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
