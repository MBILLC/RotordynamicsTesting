#!/usr/bin/env bash
# Start/stop/check the nightly_regression_cron.py background daemon.
#
# This is a process-supervision shim standing in for what a real init
# system (systemd --user, cron) would normally provide -- neither is
# available in this container. It only tracks the process for THIS pod's
# lifetime: a JupyterHub server restart/cull loses it and `start` must be
# run again.
#
# Usage:
#   ./nightly_cron_ctl.sh start    # nohup the daemon, default 22:00 America/New_York
#   ./nightly_cron_ctl.sh stop
#   ./nightly_cron_ctl.sh status
#   ./nightly_cron_ctl.sh start --hour 23 --tz Europe/Stockholm   # extra args -> the daemon
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PID_FILE="$SCRIPT_DIR/CronLogs/nightly_cron.pid"
DAEMON="$SCRIPT_DIR/nightly_regression_cron.py"

mkdir -p "$SCRIPT_DIR/CronLogs"

is_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

case "${1:-}" in
    start)
        shift || true
        if is_running; then
            echo "Already running (PID $(cat "$PID_FILE"))."
            exit 0
        fi
        # nightly_regression_cron.py writes its own CronLogs/daemon.log; this
        # redirect only catches a startup crash before it gets that far.
        nohup python3 "$DAEMON" "$@" >> "$SCRIPT_DIR/CronLogs/nohup.out" 2>&1 &
        echo $! > "$PID_FILE"
        disown
        echo "Started (PID $(cat "$PID_FILE")). Logs: $SCRIPT_DIR/CronLogs/daemon.log"

        ;;
    stop)
        if ! is_running; then
            echo "Not running."
            rm -f "$PID_FILE"
            exit 0
        fi
        kill "$(cat "$PID_FILE")"
        rm -f "$PID_FILE"
        echo "Stopped."
        ;;
    status)
        if is_running; then
            echo "Running (PID $(cat "$PID_FILE"))."
        else
            echo "Not running."
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|status} [-- daemon args]" >&2
        exit 2
        ;;
esac
