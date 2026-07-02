#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib/launchd.sh"

agents=($(resolve_agents "$@")) || exit 1

for agent in "${agents[@]}"; do
    label=$(label_for "$agent")
    plist_dst=$(plist_dst_for "$agent")

    # Stop if running
    if launchctl print "$DOMAIN/$label" &>/dev/null; then
        launchctl bootout "$DOMAIN/$label"
        echo "[$agent] stopped."
    else
        echo "[$agent] not loaded."
    fi

    # Remove installed plist
    if [ -f "$plist_dst" ]; then
        rm "$plist_dst"
        echo "[$agent] plist removed."
    else
        echo "[$agent] plist not installed."
    fi
done
