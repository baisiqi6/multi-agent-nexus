#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib/launchd.sh"

agents=($(resolve_agents "$@")) || exit 1

for agent in "${agents[@]}"; do
    label=$(label_for "$agent")
    echo "=== $agent ==="

    if launchctl print "$DOMAIN/$label" &>/dev/null; then
        echo "  status: loaded"
        pid=$(launchctl print "$DOMAIN/$label" 2>/dev/null | grep 'pid' | head -1 | awk '{print $NF}' || true)
        if [ -n "$pid" ]; then
            echo "  pid: $pid"
        fi
        last_exit=$(launchctl print "$DOMAIN/$label" 2>/dev/null | grep 'last exit status' | awk -F': ' '{print $2}' || true)
        if [ -n "$last_exit" ]; then
            echo "  last exit: $last_exit"
        fi
    else
        echo "  status: not loaded"
    fi

    echo "  log: $REPO_ROOT/logs/${agent}.log"
    echo "  err: $REPO_ROOT/logs/${agent}.err.log"

    # Check for manual process
    manual=$(check_manual_process "$agent")
    if [ -n "$manual" ]; then
        echo "  WARNING: manual process detected:"
        echo "    $manual"
    fi
    echo ""
done
