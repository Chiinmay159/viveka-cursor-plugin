#!/usr/bin/env bash
# Viveka Hook Client — fast bash adapter that talks to the governance daemon.
#
# Cursor invokes this for every hook event. It reads JSON from stdin,
# wraps it into a daemon request, and sends it over a Unix domain socket.
#
# On sessionStart: spawns the Python daemon if not already running.
# On stop: tells the daemon to shut down.
# All other events: send to daemon, return response.
#
# Typical latency: ~8ms per call (vs ~570ms with the old process-per-call approach).
# Falls open (allows everything) if daemon is unreachable.

set -euo pipefail

TMPDIR="${TMPDIR:-/tmp}"
SOCKET_PATH="${TMPDIR}/viveka-daemon.sock"
PID_FILE="${TMPDIR}/viveka-daemon.pid"
READY_FILE="${TMPDIR}/viveka-daemon.ready"
STATE_FILE="${TMPDIR}/viveka-session-state.json"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DAEMON_SCRIPT="${SCRIPT_DIR}/viveka-daemon.py"

EVENT="${VIVEKA_HOOK_EVENT:-unknown}"

FAIL_OPEN='{"continue":true}'

payload="$(cat)"
[ -z "$payload" ] && payload='{}'

daemon_alive() {
    [ -f "$PID_FILE" ] || return 1
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null)" || return 1
    kill -0 "$pid" 2>/dev/null
}

send_to_daemon() {
    local request="$1"
    printf '%s\n' "$request" | nc -U "$SOCKET_PATH" -w 3 2>/dev/null || echo "$FAIL_OPEN"
}

spawn_daemon() {
    rm -f "$SOCKET_PATH" "$PID_FILE" "$READY_FILE" 2>/dev/null
    python3 "$DAEMON_SCRIPT" "$payload" &>/dev/null &
    disown
    local deadline=$((SECONDS + 5))
    while [ $SECONDS -lt $deadline ]; do
        [ -f "$READY_FILE" ] && [ -e "$SOCKET_PATH" ] && return 0
        sleep 0.05
    done
    return 1
}

build_request() {
    printf '{"event":"%s","payload":%s}' "$EVENT" "$payload"
}

case "$EVENT" in
    sessionStart)
        # Write session state for MCP server (lightweight, no Python needed)
        echo "$payload" > "$STATE_FILE" 2>/dev/null || true

        if daemon_alive; then
            send_to_daemon "$(build_request)"
        elif spawn_daemon; then
            send_to_daemon "$(build_request)"
        else
            echo "$FAIL_OPEN"
        fi
        ;;
    stop|sessionEnd)
        send_to_daemon "$(build_request)"
        rm -f "$STATE_FILE" 2>/dev/null || true
        ;;
    *)
        if [ -e "$SOCKET_PATH" ]; then
            send_to_daemon "$(build_request)"
        else
            echo "$FAIL_OPEN"
        fi
        ;;
esac
