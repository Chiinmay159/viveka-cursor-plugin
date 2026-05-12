#!/usr/bin/env python3
"""
Viveka Hook Client — thin adapter between Cursor hooks and the governance daemon.

This script contains ZERO heavy imports (no pydantic, no viveka runtime).
It communicates with viveka-daemon.py over a Unix domain socket.

On sessionStart: spawns the daemon process, waits for it to be ready.
On preToolUse/beforeShellExecution/afterFileEdit: sends to daemon, returns response.
On stop: tells daemon to shut down.

If the daemon is unreachable, fails open (allows everything).
Typical latency: <2ms per call (vs ~550ms with process-per-call).
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
DAEMON_SCRIPT = SCRIPTS_DIR / "viveka-daemon.py"
SOCKET_PATH = Path(tempfile.gettempdir()) / "viveka-daemon.sock"
PID_FILE = Path(tempfile.gettempdir()) / "viveka-daemon.pid"
READY_FILE = Path(tempfile.gettempdir()) / "viveka-daemon.ready"

STATE_FILE = Path(tempfile.gettempdir()) / "viveka-session-state.json"

FAIL_OPEN = {"continue": True}


def _daemon_alive() -> bool:
    """Check if daemon process is actually running."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # signal 0 = existence check
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def _send_to_daemon(event: str, payload: dict) -> dict | None:
    """Send a request to the daemon. Returns response or None on failure."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(4)
        sock.connect(str(SOCKET_PATH))
        request = json.dumps({"event": event, "payload": payload})
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


def _spawn_daemon(payload: dict):
    """Start the daemon process in the background."""
    for f in (SOCKET_PATH, PID_FILE, READY_FILE):
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass

    init_payload = json.dumps(payload)
    subprocess.Popen(
        [sys.executable, str(DAEMON_SCRIPT), init_payload],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        if READY_FILE.exists() and SOCKET_PATH.exists():
            return True
        time.sleep(0.02)
    return False


def _write_session_state(payload: dict):
    """Write session state for the MCP server to read."""
    import re

    _INTENT_PATTERNS = [
        (r"\b(fix|bug|error|crash|broken|patch|hotfix)\b",       "fix"),
        (r"\b(recover|rollback|revert|incident|outage)\b",       "recovery"),
        (r"\b(explor|spike|prototype|research|investigat)",       "exploration"),
        (r"\b(refactor|optimiz|improv|clean.?up|perf)",           "improvement"),
        (r"\b(updat|upgrad|depend|migrat|deprecat|maint)",        "maintenance"),
    ]

    task = payload.get("task", payload.get("description", "cursor agent session"))
    intent = "feature"
    lower = task.lower()
    for pattern, i in _INTENT_PATTERNS:
        if re.search(pattern, lower):
            intent = i
            break

    state = {
        "repo_path": payload.get("cwd", "."),
        "environment": "development",
        "task": task,
        "intent": intent,
        "urgency": "medium",
        "reversibility": "high",
        "posture": payload.get("posture", "standard"),
    }
    STATE_FILE.write_text(json.dumps(state))


def _cleanup_session_state():
    for f in (STATE_FILE,):
        try:
            f.unlink(missing_ok=True)
        except Exception:
            pass


def main():
    payload = json.load(sys.stdin)
    event = os.environ.get("VIVEKA_HOOK_EVENT", "unknown")

    if event == "sessionStart":
        _write_session_state(payload)

        if _daemon_alive():
            response = _send_to_daemon(event, payload)
        else:
            ok = _spawn_daemon(payload)
            response = _send_to_daemon(event, payload) if ok else None

    elif event in ("stop", "sessionEnd"):
        response = _send_to_daemon(event, payload)
        _cleanup_session_state()

    else:
        if _daemon_alive():
            response = _send_to_daemon(event, payload)
        else:
            response = None

    result = response if response else FAIL_OPEN
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        json.dump(FAIL_OPEN, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()
