#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib/launchd.sh"

agents=($(resolve_agents "$@")) || exit 1

# Pre-flight checks
mkdir -p "$REPO_ROOT/logs"
mkdir -p "$LAUNCHD_DST_DIR"

if [ ! -f "$REPO_ROOT/agents.toml" ]; then
    echo "ERROR: agents.toml not found in $REPO_ROOT" >&2
    exit 1
fi
if [ ! -f "$REPO_ROOT/.env" ]; then
    echo "ERROR: .env not found in $REPO_ROOT" >&2
    exit 1
fi

for agent in "${agents[@]}"; do
    label=$(label_for "$agent")
    plist_src=$(plist_src_for "$agent")
    plist_dst=$(plist_dst_for "$agent")

    if [ ! -f "$plist_src" ]; then
        echo "ERROR: plist not found: $plist_src" >&2
        exit 1
    fi

    # Check for manual process
    manual=$(check_manual_process "$agent")
    if [ -n "$manual" ]; then
        echo "ERROR: manual process already running for $agent:" >&2
        echo "  $manual" >&2
        echo "Stop it first (kill the PID), then retry." >&2
        exit 1
    fi

    # If already loaded, bootout first so launchd picks up plist changes
    if launchctl print "$DOMAIN/$label" &>/dev/null; then
        echo "[$agent] already loaded, reloading updated plist..."
        launchctl bootout "$DOMAIN/$label"
    fi

    # Install plist and bootstrap
    cp "$plist_src" "$plist_dst"
    launchctl bootstrap "$DOMAIN" "$plist_dst"
    echo "[$agent] started."
done
