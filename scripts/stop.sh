#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib/launchd.sh"

agents=($(resolve_agents "$@")) || exit 1

for agent in "${agents[@]}"; do
    label=$(label_for "$agent")
    if launchctl print "$DOMAIN/$label" &>/dev/null; then
        launchctl bootout "$DOMAIN/$label"
        echo "[$agent] stopped."
    else
        echo "[$agent] not loaded (already stopped)."
    fi
done
