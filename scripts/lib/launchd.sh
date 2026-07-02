# Shared logic for multinexus launchd scripts

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AGENTS=("mac-claude" "mac-codex" "mac-opencode" "mac-omp")
LAUNCHD_SRC_DIR="$REPO_ROOT/launchd"
LAUNCHD_DST_DIR="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"

label_for() { echo "com.multinexus.$1"; }

plist_src_for() { echo "$LAUNCHD_SRC_DIR/com.multinexus.$1.plist"; }
plist_dst_for() { echo "$LAUNCHD_DST_DIR/com.multinexus.$1.plist"; }

# Resolve agents to act on: arg or all
resolve_agents() {
    if [ $# -eq 0 ]; then
        printf '%s\n' "${AGENTS[@]}"
    elif printf '%s\n' "${AGENTS[@]}" | grep -qx "$1"; then
        echo "$1"
    else
        echo "ERROR: unknown agent '$1'. Expected one of: ${AGENTS[*]}" >&2
        return 1
    fi
}

# Get launchd-managed PID for an agent (empty if not loaded)
launchd_pid() {
    local label
    label=$(label_for "$1")
    launchctl print "$DOMAIN/$label" 2>/dev/null | grep 'pid = ' | head -1 | awk '{print $NF}' || true
}

# Check if a manual (non-launchd) process is running for an agent.
# Matches any process whose argv contains --agent <agent> or --agent=<agent>
# anywhere, so invocations like "python multinexus.py --config agents.toml --agent mac-claude"
# are also detected.
check_manual_process() {
    local agent=$1 lpid
    lpid=$(launchd_pid "$agent")
    local pids
    pids=$(pgrep -f "nexus\.py.*--agent[= ]${agent}\>" 2>/dev/null || true)
    if [ -z "$pids" ]; then
        return
    fi
    for p in $pids; do
        if [ "$p" != "$lpid" ]; then
            ps -p "$p" -o pid,command 2>/dev/null | tail -n +2
        fi
    done
}
