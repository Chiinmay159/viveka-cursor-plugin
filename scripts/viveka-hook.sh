#!/usr/bin/env bash
# Viveka Hook Client — fast bash adapter that talks to the governance daemon.
#
# Cursor invokes this for every hook event. It reads JSON from stdin,
# wraps it into a daemon request, and sends it over a Unix domain socket.
#
# On sessionStart: spawns the Python daemon if not already running.
# On stop/sessionEnd: tells the daemon to shut down.
# All other events: send to daemon. If daemon is dead, attempt ONE respawn
# from saved session state before falling open.
#
# Typical latency: ~8ms per call (vs ~570ms with the old process-per-call approach).
# Falls open (allows everything) if daemon is unreachable after respawn attempt.
#
# Known limitation: all Cursor windows share one daemon per user. If two windows
# run different projects, the last sessionStart wins. This requires Cursor to
# expose a per-session identifier to fix properly.

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
    local init_payload="$1"
    rm -f "$SOCKET_PATH" "$PID_FILE" "$READY_FILE" 2>/dev/null
    python3 "$DAEMON_SCRIPT" "$init_payload" &>/dev/null &
    disown
    local deadline=$((SECONDS + 5))
    while [ $SECONDS -lt $deadline ]; do
        [ -f "$READY_FILE" ] && [ -e "$SOCKET_PATH" ] && return 0
        sleep 0.05
    done
    return 1
}

respawn_daemon() {
    [ -f "$STATE_FILE" ] || return 1
    local saved_payload
    saved_payload="$(cat "$STATE_FILE")"
    spawn_daemon "$saved_payload"
}

ensure_daemon() {
    daemon_alive && return 0
    respawn_daemon
}

build_request() {
    printf '{"event":"%s","payload":%s}' "$EVENT" "$payload"
}

case "$EVENT" in
    sessionStart)
        echo "$payload" > "$STATE_FILE" 2>/dev/null || true

        if daemon_alive; then
            send_to_daemon "$(build_request)"
        elif spawn_daemon "$payload"; then
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
        if ensure_daemon; then
            send_to_daemon "$(build_request)"
        else
            echo "$FAIL_OPEN"
        fi
        ;;
esac
