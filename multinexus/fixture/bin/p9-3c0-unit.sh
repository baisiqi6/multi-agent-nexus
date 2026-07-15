#!/usr/bin/env bash
# P9-3C0 Package 2 transient-unit lifecycle helper.
#
# Operator-only: render, preflight, start, status, stop, cleanup. No catalog
# sync, job/lease creation, or production activation in Package 2.

set -uo pipefail

# ---------------------------------------------------------------------------
# Replaceable functions for testing; production entrypoint uses real commands.
# ---------------------------------------------------------------------------

_p9c0_real_date_ms() {
    # epoch milliseconds from Python for monotonic integer math.
    "${P9C0_PYTHON:-python3}" -c "import time; print(int(time.monotonic()*1000))"
}

_p9c0_real_systemctl() {
    systemctl "$@"
}

_p9c0_real_run_systemd_run() {
    systemd-run "$@"
}

_p9c0_real_flock() {
    # Prefer the system flock(1) when available; otherwise use Python fcntl.
    if command -v flock >/dev/null 2>&1; then
        flock "$@"
    else
        python3 -c '
import fcntl, sys
op = sys.argv[1]
fd = int(sys.argv[2])
if op == "-x" or op == "--exclusive":
    fcntl.flock(fd, fcntl.LOCK_EX)
elif op == "-u" or op == "--unlock":
    fcntl.flock(fd, fcntl.LOCK_UN)
' "$@"
    fi
}

_p9c0_real_sleep() {
    sleep "$1"
}

_p9c0_real_read_cgroup_procs() {
    local path="$1"
    cat "$path"
}

_p9c0_validate_recorded_cgroup() {
    # Fail closed if the recorded cgroup value could escape /sys/fs/cgroup.
    # systemd ControlGroup values are absolute, normalized, single-segment paths.
    local cgroup="$1"
    python3 - "$cgroup" <<'PYEOF'
import os, sys
cgroup = sys.argv[1]
if not cgroup:
    print("cgroup validation: empty", file=sys.stderr)
    sys.exit(1)
if not cgroup.startswith('/'):
    print("cgroup validation: missing leading slash", file=sys.stderr)
    sys.exit(1)
if cgroup.startswith('//') or cgroup.endswith('/'):
    print("cgroup validation: malformed leading/trailing slash", file=sys.stderr)
    sys.exit(1)
parts = cgroup.split('/')
if any(p in ('', '.', '..') for p in parts[1:]):
    print("cgroup validation: contains empty, ., or .. segment", file=sys.stderr)
    sys.exit(1)
if any(ch in cgroup for ch in '\n\r\t\x00 '):
    print("cgroup validation: contains whitespace or control characters", file=sys.stderr)
    sys.exit(1)
if os.path.normpath(cgroup) != cgroup:
    print("cgroup validation: not normalized", file=sys.stderr)
    sys.exit(1)
PYEOF
}

_p9c0_real_cgroup_procs_path() {
    # cgroup values from systemd already start with /system.slice/...; prepend
    # the real cgroup mount point without adding a second leading slash.
    local cgroup="$1"
    [[ -n $cgroup ]] || return 0
    _p9c0_validate_recorded_cgroup "$cgroup" || return 1
    printf '/sys/fs/cgroup%s/cgroup.procs\n' "$cgroup"
}

_p9c0_date_ms() { _p9c0_real_date_ms; }
_p9c0_systemctl() { _p9c0_real_systemctl "$@"; }
_p9c0_run_systemd_run() { _p9c0_real_run_systemd_run "$@"; }
_p9c0_flock() { _p9c0_real_flock "$@"; }
_p9c0_sleep() { _p9c0_real_sleep "$@"; }
_p9c0_cgroup_procs_path() { _p9c0_real_cgroup_procs_path "$@"; }
_p9c0_read_cgroup_procs() { _p9c0_real_read_cgroup_procs "$1"; }

# ---------------------------------------------------------------------------
# Static constants
# ---------------------------------------------------------------------------

P9C0_AGENT_ALLOWLIST=("p9-3c-fixture-e1" "p9-3c-fixture-e2")
P9C0_PROD_DB="/var/lib/coordinate/coord.sqlite3"
P9C0_PROD_WRAPPER="/usr/local/bin/coord-local"
P9C0_RUN_ID_RE='^[a-z0-9]+(-[a-z0-9]+)*$'
P9C0_MAX_UNITS=2

# ---------------------------------------------------------------------------
# Production path resolution helpers
# ---------------------------------------------------------------------------

_p9c0_is_resolved_production_wrapper() {
    local wrapper="$1"
    local resolved prod_resolved
    resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$wrapper") || return 1
    prod_resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$P9C0_PROD_WRAPPER") || return 1
    [[ $resolved == "$prod_resolved" ]]
}

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

_p9c0_die() {
    printf 'p9-3c0-unit: %s\n' "$1" >&2
    exit "${2:-1}"
}

_p9c0_usage() {
    _p9c0_die "usage: $0 render|preflight|start|status|stop|cleanup [flags]" 2
}

# ---------------------------------------------------------------------------
# Path/identity validation
# ---------------------------------------------------------------------------

_p9c0_is_absolute_path() {
    [[ $1 == /* ]]
}

_p9c0_is_under_root() {
    local path="$1" root="$2"
    [[ -d $root ]] || return 1
    # Use Python realpath for consistent physical normalization on all platforms.
    # Exit status answers the containment question; stdout is unused.
    python3 -c "
import os, sys
root = os.path.realpath(sys.argv[1])
path = os.path.realpath(sys.argv[2])
if path == root or path.startswith(root + os.sep):
    sys.exit(0)
sys.exit(1)
" "$root" "$path"
}

_p9c0_validate_run_id() {
    local run_id="$1"
    [[ -n $run_id ]] || _p9c0_die "run-id required"
    [[ ${#run_id} -le 64 ]] || _p9c0_die "run-id too long"
    [[ $run_id =~ $P9C0_RUN_ID_RE ]] || _p9c0_die "invalid run-id"
}

_p9c0_validate_agent_id() {
    local agent_id="$1"
    local a
    for a in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        [[ $a == "$agent_id" ]] && return 0
    done
    _p9c0_die "invalid agent-id: $agent_id"
}

_p9c0_unit_name() {
    local agent_id="$1" run_id="$2"
    printf '%s-%s.service\n' "$agent_id" "$run_id"
}

# ---------------------------------------------------------------------------
# Ledger layout
# ---------------------------------------------------------------------------

_p9c0_state_dir() {
    printf '%s/%s\n' "$P9C0_STATE_ROOT" "$P9C0_RUN_ID"
}

_p9c0_lock_file() {
    printf '%s/lock\n' "$(_p9c0_state_dir)"
}

_p9c0_ledger_file() {
    printf '%s/ledger\n' "$(_p9c0_state_dir)"
}

_p9c0_config_file() {
    printf '%s/agents.rendered.toml\n' "$(_p9c0_state_dir)"
}

_p9c0_values_file() {
    printf '%s/values.rendered\n' "$(_p9c0_state_dir)"
}

_p9c0_ledger_append() {
    local line="$1"
    local ledger
    ledger=$(_p9c0_ledger_file)
    mkdir -p "$(dirname "$ledger")"
    chmod 700 "$(dirname "$ledger")"
    printf '%s\n' "$line" >> "$ledger"
    chmod 600 "$ledger"
}

# ---------------------------------------------------------------------------
# Render subcommand
# ---------------------------------------------------------------------------

_p9c0_cmd_render() {
    local state_root="" run_id="" fixture_bin="" wrapper="" coord_db="" work_dir="" python="" repo_root=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --state-root) state_root="$2"; shift 2 ;;
            --run-id) run_id="$2"; shift 2 ;;
            --fixture-bin) fixture_bin="$2"; shift 2 ;;
            --wrapper) wrapper="$2"; shift 2 ;;
            --coord-db) coord_db="$2"; shift 2 ;;
            --work-dir) work_dir="$2"; shift 2 ;;
            --python) python="$2"; shift 2 ;;
            --repo-root) repo_root="$2"; shift 2 ;;
            *) _p9c0_die "render: unknown flag $1" ;;
        esac
    done

    [[ -n $state_root ]] || _p9c0_die "render: --state-root required"
    [[ -n $run_id ]] || _p9c0_die "render: --run-id required"
    [[ -n $fixture_bin ]] || _p9c0_die "render: --fixture-bin required"
    [[ -n $wrapper ]] || _p9c0_die "render: --wrapper required"
    [[ -n $coord_db ]] || _p9c0_die "render: --coord-db required"
    [[ -n $work_dir ]] || _p9c0_die "render: --work-dir required"
    [[ -n $python ]] || _p9c0_die "render: --python required"
    [[ -n $repo_root ]] || _p9c0_die "render: --repo-root required"

    _p9c0_validate_run_id "$run_id"

    _p9c0_is_absolute_path "$state_root" || _p9c0_die "state-root must be absolute"
    _p9c0_is_absolute_path "$fixture_bin" || _p9c0_die "fixture-bin must be absolute"
    _p9c0_is_absolute_path "$wrapper" || _p9c0_die "wrapper must be absolute"
    _p9c0_is_absolute_path "$coord_db" || _p9c0_die "coord-db must be absolute"
    _p9c0_is_absolute_path "$work_dir" || _p9c0_die "work-dir must be absolute"
    _p9c0_is_absolute_path "$python" || _p9c0_die "python must be absolute"
    _p9c0_is_absolute_path "$repo_root" || _p9c0_die "repo-root must be absolute"

    # Production DB/wrapper rejection (no bypass)
    [[ $coord_db == "$P9C0_PROD_DB" ]] && _p9c0_die "render: refusing production coord-db"
    [[ $wrapper == "$P9C0_PROD_WRAPPER" ]] && _p9c0_die "render: refusing production wrapper"
    _p9c0_is_resolved_production_wrapper "$wrapper" && _p9c0_die "render: refusing production wrapper (resolved)"

    # Paths must resolve under the isolated state root.
    _p9c0_is_under_root "$coord_db" "$state_root" || _p9c0_die "render: coord-db must be under state-root"
    _p9c0_is_under_root "$work_dir" "$state_root" || _p9c0_die "render: work-dir must be under state-root"

    local template
    template="$repo_root/multinexus/fixture/config/agents.fixture.toml"
    [[ -f $template ]] || _p9c0_die "render: missing fixture template $template"

    # All mutating writes happen under the per-run exclusive lock.
    _p9c0_with_lock "$state_root" "$run_id" _p9c0_render_locked "$state_root" "$run_id" "$fixture_bin" "$wrapper" "$coord_db" "$work_dir" "$python" "$repo_root" "$template"
}

_p9c0_render_locked() {
    local state_root="$1" run_id="$2" fixture_bin="$3" wrapper="$4" coord_db="$5" work_dir="$6" python="$7" repo_root="$8" template="$9"
    P9C0_STATE_ROOT="$state_root"
    P9C0_RUN_ID="$run_id"

    local state_dir
    state_dir="$state_root/$run_id"
    mkdir -p "$state_dir"
    chmod 700 "$state_dir"

    # Record all reviewed values so later commands compare against them.
    cat > "$state_dir/values.rendered" <<EOF
state_root=$state_root
run_id=$run_id
fixture_bin=$fixture_bin
wrapper=$wrapper
coord_db=$coord_db
work_dir=$work_dir
python=$python
repo_root=$repo_root
EOF
    chmod 600 "$state_dir/values.rendered"

    local rendered
    rendered="$state_dir/agents.rendered.toml"

    # Replace each placeholder exactly once; detect leftovers.
    local tmp
    tmp=$(mktemp "$state_dir/.agents.rendered.XXXXXX.toml")
    cp "$template" "$tmp"

    local e1_db="$state_dir/context-e1.sqlite3"
    local e2_db="$state_dir/context-e2.sqlite3"

    _p9c0_replace_once "$tmp" "__P9C0_COORDINATOR_CLI__" "$wrapper"
    _p9c0_replace_once "$tmp" "__P9C0_COORDINATOR_DB__" "$coord_db"
    _p9c0_replace_once "$tmp" "__P9C0_WORK_DIR__" "$work_dir"
    _p9c0_replace_once "$tmp" "__P9C0_E1_CONTEXT_DB__" "$e1_db"
    _p9c0_replace_once "$tmp" "__P9C0_E2_CONTEXT_DB__" "$e2_db"
    _p9c0_replace_once "$tmp" "__P9C0_E1_CLAUDE_BIN__" "$fixture_bin"
    _p9c0_replace_once "$tmp" "__P9C0_E2_CLAUDE_BIN__" "$fixture_bin"

    if grep -qE '__P9C0_[A-Z_]+__' "$tmp"; then
        rm -f "$tmp"
        _p9c0_die "render: leftover placeholders in rendered config"
    fi

    mv "$tmp" "$rendered"
    chmod 600 "$rendered"

    # Load both agents with require_token=False and assert no real-claude fallback.
    local e1_bin e2_bin repo_root_for_python
    repo_root_for_python=$(cd "$repo_root" && pwd)
    e1_bin=$($python - "$rendered" "$repo_root_for_python" "p9-3c-fixture-e1" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from multinexus.config import _load_toml_agent
print(_load_toml_agent(Path(sys.argv[1]), sys.argv[3], require_token=False).claude_bin)
PYEOF
) || _p9c0_die "render: failed to load e1 config"
    e2_bin=$($python - "$rendered" "$repo_root_for_python" "p9-3c-fixture-e2" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
from multinexus.config import _load_toml_agent
print(_load_toml_agent(Path(sys.argv[1]), sys.argv[3], require_token=False).claude_bin)
PYEOF
) || _p9c0_die "render: failed to load e2 config"

    [[ $e1_bin == "$fixture_bin" ]] || _p9c0_die "render: e1 claude_bin mismatch (fallback?): $e1_bin"
    [[ $e2_bin == "$fixture_bin" ]] || _p9c0_die "render: e2 claude_bin mismatch (fallback?): $e2_bin"

    # Record render evidence.
    _p9c0_ledger_append "render run=$run_id fixture_bin=$fixture_bin wrapper=$wrapper coord_db=$coord_db work_dir=$work_dir"

    # Tighten explicit state-root to 0700 now that all mutating work succeeded.
    chmod 700 "$state_root"

    printf 'rendered %s\n' "$rendered"
}

_p9c0_replace_once() {
    local file="$1" marker="$2" value="$3"
    local count
    count=$(grep -oF "$marker" "$file" | wc -l)
    [[ $count -eq 1 ]] || _p9c0_die "render: marker $marker appears $count times (expected 1)"
    sed -i.bak "s|${marker//|/\\|}|${value//|/\\|}|g" "$file"
    rm -f "$file.bak"
}

# ---------------------------------------------------------------------------
# Preflight subcommand
# ---------------------------------------------------------------------------

_p9c0_cmd_preflight() {
    local state_root="" run_id="" agent_id=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --state-root) state_root="$2"; shift 2 ;;
            --run-id) run_id="$2"; shift 2 ;;
            --agent-id) agent_id="$2"; shift 2 ;;
            *) _p9c0_die "preflight: unknown flag $1" ;;
        esac
    done

    [[ -n $state_root ]] || _p9c0_die "preflight: --state-root required"
    [[ -n $run_id ]] || _p9c0_die "preflight: --run-id required"
    [[ -n $agent_id ]] || _p9c0_die "preflight: --agent-id required"
    _p9c0_validate_run_id "$run_id"
    _p9c0_validate_agent_id "$agent_id"

    _p9c0_load_values "$state_root" "$run_id"

    # Linux/systemd availability.
    command -v systemctl >/dev/null || _p9c0_die "preflight: systemctl not found"
    command -v systemd-run >/dev/null || _p9c0_die "preflight: systemd-run not found"

    # Canonical authority must not contain fixture ids.
    local canonical
    canonical="$P9C0_REPO_ROOT/config/agent-registry.toml"
    [[ -f $canonical ]] || _p9c0_die "preflight: missing canonical authority"
    if grep -qE '^id = "p9-3c-fixture-e[12]"' "$canonical"; then
        _p9c0_die "preflight: fixture ids present in canonical authority"
    fi

    # Rendered config exists and resolves expected values.
    local rendered
    rendered="$P9C0_STATE_ROOT/$run_id/agents.rendered.toml"
    [[ -f $rendered ]] || _p9c0_die "preflight: rendered config missing"

    # Exact fixture bin matches.
    local actual_fixture_bin
    actual_fixture_bin=$(grep -m1 '^fixture_bin=' "$P9C0_STATE_ROOT/$run_id/values.rendered" | cut -d= -f2-)
    [[ $actual_fixture_bin == "$P9C0_FIXTURE_BIN" ]] || _p9c0_die "preflight: fixture_bin mismatch"

    # Control envelope is quiet 75.
    [[ -x $P9C0_FIXTURE_BIN ]] || _p9c0_die "preflight: fixture_bin not executable"

    # Isolated wrapper health/list evidence (read-only).
    local wrapper_out
    wrapper_out=$("$P9C0_WRAPPER" --version 2>&1) || _p9c0_die "preflight: wrapper health check failed"
    [[ -n $wrapper_out ]] || _p9c0_die "preflight: wrapper health output empty"

    # No active/running fixture unit may already occupy the exact namespace.
    local unit
    unit=$(_p9c0_unit_name "$agent_id" "$run_id")
    if _p9c0_systemctl list-units --type=service --state=running,activating --no-legend "$unit" 2>/dev/null | grep -q "$unit"; then
        _p9c0_die "preflight: unit $unit already active"
    fi

    # No more than two units per run.
    local ledger
    ledger="$P9C0_STATE_ROOT/$run_id/ledger"
    local unit_count=0
    if [[ -f $ledger ]]; then
        unit_count=$(grep -cE "^unit " "$ledger" 2>/dev/null || true)
    fi
    [[ $unit_count -lt $P9C0_MAX_UNITS ]] || _p9c0_die "preflight: run already has $P9C0_MAX_UNITS units"

    printf 'preflight ok for %s\n' "$unit"
}

# ---------------------------------------------------------------------------
# Start subcommand
# ---------------------------------------------------------------------------

_p9c0_cmd_start() {
    local state_root="" run_id="" agent_id="" mode="" user="" group=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --state-root) state_root="$2"; shift 2 ;;
            --run-id) run_id="$2"; shift 2 ;;
            --agent-id) agent_id="$2"; shift 2 ;;
            --mode) mode="$2"; shift 2 ;;
            --user) user="$2"; shift 2 ;;
            --group) group="$2"; shift 2 ;;
            *) _p9c0_die "start: unknown flag $1" ;;
        esac
    done

    [[ -n $state_root ]] || _p9c0_die "start: --state-root required"
    [[ -n $run_id ]] || _p9c0_die "start: --run-id required"
    [[ -n $agent_id ]] || _p9c0_die "start: --agent-id required"
    [[ -n $mode ]] || _p9c0_die "start: --mode required"
    [[ -n $user ]] || _p9c0_die "start: --user required"
    [[ -n $group ]] || _p9c0_die "start: --group required"
    _p9c0_validate_run_id "$run_id"
    _p9c0_validate_agent_id "$agent_id"
    [[ $mode == complete || $mode == hold ]] || _p9c0_die "start: mode must be complete or hold"

    _p9c0_load_values "$state_root" "$run_id"

    local unit
    unit=$(_p9c0_unit_name "$agent_id" "$run_id")

    _p9c0_with_lock "$state_root" "$run_id" _p9c0_start_locked "$agent_id" "$run_id" "$unit" "$mode" "$user" "$group"
}

_p9c0_start_locked() {
    local agent_id="$1" run_id="$2" unit="$3" mode="$4" user="$5" group="$6"

    local state_dir
    state_dir="$P9C0_STATE_ROOT/$run_id"

    # Verify preflight gates still hold under lock.
    if _p9c0_systemctl list-units --type=service --state=running,activating --no-legend "$unit" 2>/dev/null | grep -q "$unit"; then
        _p9c0_die "start: unit $unit already active"
    fi

    local ledger
    ledger="$state_dir/ledger"
    local unit_count=0
    if [[ -f $ledger ]]; then
        unit_count=$(grep -cE "^unit " "$ledger" 2>/dev/null || true)
    fi
    [[ $unit_count -lt $P9C0_MAX_UNITS ]] || _p9c0_die "start: run already has $P9C0_MAX_UNITS units"

    local rendered
    rendered="$state_dir/agents.rendered.toml"
    [[ -f $rendered ]] || _p9c0_die "start: rendered config missing"

    # Ask systemd whether it can enforce network properties.
    local net_support=1
    if _p9c0_run_systemd_run --dry-run --property=IPAddressDeny=any --unit="p9-3c-probe-$run_id" true >/dev/null 2>&1; then
        net_support=1
    else
        net_support=0
    fi

    if [[ $net_support -eq 0 ]]; then
        _p9c0_ledger_append "network-property-unsupported unit=$unit"
        _p9c0_die "start: systemd manager does not support mandatory network properties"
    fi

    local start_ms
    start_ms=$(_p9c0_date_ms)

    # Build mandatory property list.
    local properties=()
    properties+=(--property="User=$user")
    properties+=(--property="Group=$group")
    properties+=(--property="WorkingDirectory=$P9C0_WORK_DIR")
    properties+=(--property="RuntimeMaxSec=300")
    properties+=(--property="TimeoutStopSec=30")
    properties+=(--property="KillMode=control-group")
    properties+=(--property="IPAddressDeny=any")
    properties+=(--property="RestrictAddressFamilies=AF_UNIX")
    properties+=(--property="NoNewPrivileges=yes")
    properties+=(--property="PrivateTmp=yes")
    properties+=(--property="ProtectSystem=strict")
    properties+=(--property="ProtectHome=yes")
    properties+=(--property="ReadWritePaths=$P9C0_STATE_ROOT")
    properties+=(--property="UMask=0077")

    local env_list=("PATH=/usr/local/bin:/usr/bin:/bin")

    _p9c0_run_systemd_run \
        --unit="$unit" \
        --service-type=simple \
        --collect \
        --remain-after-exit \
        "${properties[@]}" \
        --setenv="${env_list[0]}" \
        env -i "${env_list[@]}" \
        "$P9C0_PYTHON" -m multinexus.agentd \
            --config "$rendered" \
            --agent "$agent_id" || {
        _p9c0_ledger_append "start-failed unit=$unit"
        _p9c0_die "start: systemd-run failed for $unit"
    }

    # Capture post-start properties.
    local main_pid cgroup state result
    main_pid=$(_p9c0_systemctl show -p MainPID --value "$unit" 2>/dev/null || true)
    cgroup=$(_p9c0_systemctl show -p ControlGroup --value "$unit" 2>/dev/null || true)
    state=$(_p9c0_systemctl show -p ActiveState --value "$unit" 2>/dev/null || true)
    result=$(_p9c0_systemctl show -p Result --value "$unit" 2>/dev/null || true)

    # Validate mandatory properties.
    local verify_ok=1
    local expected_props
    expected_props=$(cat <<EOF
User=$user
Group=$group
WorkingDirectory=$P9C0_WORK_DIR
RuntimeMaxSec=300
TimeoutStopSec=30
KillMode=control-group
IPAddressDeny=any
RestrictAddressFamilies=AF_UNIX
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$P9C0_STATE_ROOT
UMask=0077
EOF
)
    local prop
    while IFS= read -r prop; do
        local key value actual
        key=${prop%%=*}
        value=${prop#*=}
        actual=$(_p9c0_systemctl show -p "$key" --value "$unit" 2>/dev/null || true)
        if [[ $actual != "$value" ]]; then
            verify_ok=0
            _p9c0_ledger_append "post-start-mismatch unit=$unit key=$key expected=$value actual=$actual"
        fi
    done <<< "$expected_props"

    if [[ $verify_ok -eq 0 ]]; then
        _p9c0_stop_exact_unit "$unit" "$cgroup"
        _p9c0_ledger_append "post-start-cleanup unit=$unit"
        _p9c0_die "start: post-start property mismatch; stopped $unit"
    fi

    _p9c0_ledger_append "unit $unit agent=$agent_id mode=$mode start_ms=$start_ms main_pid=$main_pid cgroup=$cgroup state=$state result=$result"
    printf 'started %s\n' "$unit"
}

# ---------------------------------------------------------------------------
# Status subcommand
# ---------------------------------------------------------------------------

_p9c0_cmd_status() {
    local state_root="" run_id="" agent_id=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --state-root) state_root="$2"; shift 2 ;;
            --run-id) run_id="$2"; shift 2 ;;
            --agent-id) agent_id="$2"; shift 2 ;;
            *) _p9c0_die "status: unknown flag $1" ;;
        esac
    done

    [[ -n $state_root ]] || _p9c0_die "status: --state-root required"
    [[ -n $run_id ]] || _p9c0_die "status: --run-id required"
    [[ -n $agent_id ]] || _p9c0_die "status: --agent-id required"
    _p9c0_validate_run_id "$run_id"
    _p9c0_validate_agent_id "$agent_id"

    _p9c0_load_values "$state_root" "$run_id"

    local unit
    unit=$(_p9c0_unit_name "$agent_id" "$run_id")
    _p9c0_require_ledger_unit "$unit"

    _p9c0_systemctl show \
        -p ActiveState \
        -p SubState \
        -p MainPID \
        -p ControlGroup \
        -p Result \
        "$unit"
}

# ---------------------------------------------------------------------------
# Stop subcommand
# ---------------------------------------------------------------------------

_p9c0_cmd_stop() {
    local state_root="" run_id="" agent_id="" start_ms="" evidence_run_id=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --state-root) state_root="$2"; shift 2 ;;
            --run-id) run_id="$2"; shift 2 ;;
            --agent-id) agent_id="$2"; shift 2 ;;
            --fixture-start-monotonic-ms) start_ms="$2"; shift 2 ;;
            --evidence-run-id) evidence_run_id="$2"; shift 2 ;;
            *) _p9c0_die "stop: unknown flag $1" ;;
        esac
    done

    [[ -n $state_root ]] || _p9c0_die "stop: --state-root required"
    [[ -n $run_id ]] || _p9c0_die "stop: --run-id required"
    [[ -n $agent_id ]] || _p9c0_die "stop: --agent-id required"
    _p9c0_validate_run_id "$run_id"
    _p9c0_validate_agent_id "$agent_id"

    _p9c0_load_values "$state_root" "$run_id"

    local unit
    unit=$(_p9c0_unit_name "$agent_id" "$run_id")
    _p9c0_require_ledger_unit "$unit"

    _p9c0_with_lock "$state_root" "$run_id" _p9c0_stop_locked "$unit" "$start_ms" "$evidence_run_id"
}

_p9c0_stop_locked() {
    local unit="$1" start_ms="$2" evidence_run_id="$3"

    local requested_ms actual_ms elapsed verdict timing_note
    requested_ms=$(_p9c0_date_ms)

    timing_note="no-hold-evidence"
    verdict=ok
    elapsed=0

    if [[ -n $start_ms || -n $evidence_run_id ]]; then
        [[ -n $start_ms ]] || verdict=missing-start
        [[ -n $evidence_run_id ]] || verdict=missing-run-id
        [[ $evidence_run_id == "$P9C0_RUN_ID" ]] || verdict=run-id-mismatch

        if [[ $verdict == ok ]]; then
            if [[ ! $start_ms =~ ^[0-9]+$ ]]; then
                verdict=non-decimal-start
            else
                if [[ $start_ms -gt $requested_ms ]]; then
                    verdict=future-start
                else
                    elapsed=$((requested_ms - start_ms))
                    if [[ $elapsed -ge 85000 ]]; then
                        verdict=late
                    elif [[ $elapsed -lt 75000 ]]; then
                        verdict=early
                    else
                        verdict=ok
                    fi
                fi
            fi
        fi
        timing_note="elapsed=${elapsed} verdict=$verdict start_ms=$start_ms requested_ms=$requested_ms"
    fi

    # Always stop, wait inactive, and prove cgroup cleanup first, using the
    # exact cgroup recorded at start time. If the recorded cgroup cannot be
    # determined, still stop the exact unit and then fail closed.
    local recorded_cgroup recorded_cgroup_error
    recorded_cgroup_error=""
    recorded_cgroup=$(_p9c0_recorded_cgroup_for_unit "$unit") || {
        recorded_cgroup_error="stop: cannot determine recorded cgroup for $unit"
        recorded_cgroup=""
    }

    _p9c0_stop_exact_unit "$unit" "$recorded_cgroup"

    actual_ms=$(_p9c0_date_ms)
    _p9c0_ledger_append "stop unit=$unit $timing_note actual_ms=$actual_ms"

    if [[ -n $recorded_cgroup_error ]]; then
        _p9c0_die "$recorded_cgroup_error"
    fi
    if [[ $verdict != ok ]]; then
        _p9c0_die "stop: timing evidence failed ($verdict)"
    fi
    printf 'stopped %s\n' "$unit"
}

_p9c0_stop_exact_unit() {
    local unit="$1" recorded_cgroup="$2"

    _p9c0_systemctl stop "$unit" >/dev/null 2>&1 || true

    # Bounded inactive wait.
    local attempts=0
    while [[ $attempts -lt 60 ]]; do
        local state
        state=$(_p9c0_systemctl show -p ActiveState --value "$unit" 2>/dev/null || true)
        [[ $state == inactive || $state == failed ]] && break
        _p9c0_sleep 0.5
        attempts=$((attempts + 1))
    done

    # Prove recorded cgroup is absent or empty. Fail closed if recorded cgroup
    # is known and still contains processes, or if the unit never went inactive.
    local cgroup_path procs stop_failed=0 stop_reason=""
    if [[ -n $recorded_cgroup ]]; then
        cgroup_path=$(_p9c0_cgroup_procs_path "$recorded_cgroup") || {
            _p9c0_ledger_append "cgroup-proof-invalid unit=$unit cgroup=$recorded_cgroup"
            _p9c0_die "stop: recorded cgroup is malformed or unsafe"
        }
        if [[ -e $cgroup_path ]]; then
            if [[ -f $cgroup_path && -r $cgroup_path ]]; then
                procs=$(_p9c0_read_cgroup_procs "$cgroup_path") || {
                    _p9c0_ledger_append "cgroup-proof-read-failed unit=$unit cgroup=$recorded_cgroup path=$cgroup_path"
                    stop_failed=1
                    stop_reason="cgroup.procs read failed"
                }
                if [[ -n ${procs:-} ]]; then
                    _p9c0_ledger_append "cgroup-not-empty unit=$unit cgroup=$recorded_cgroup procs=$procs"
                    stop_failed=1
                    stop_reason="cgroup $recorded_cgroup still has processes"
                fi
            else
                # Path exists but is not a readable regular file: fail closed
                # with a bounded ledger proof, not "empty".
                _p9c0_ledger_append "cgroup-proof-read-failed unit=$unit cgroup=$recorded_cgroup path=$cgroup_path"
                stop_failed=1
                stop_reason="cgroup.procs exists but is not readable"
            fi
        fi
    fi

    local final_state
    final_state=$(_p9c0_systemctl show -p ActiveState --value "$unit" 2>/dev/null || true)
    if [[ $final_state != inactive && $final_state != failed ]]; then
        _p9c0_ledger_append "stop-inactive-timeout unit=$unit attempts=$attempts state=$final_state"
        stop_failed=1
        stop_reason="unit $unit did not reach inactive/failed (state=$final_state)"
    fi

    if [[ $stop_failed -ne 0 ]]; then
        _p9c0_die "stop: $stop_reason"
    fi

    # Only claim cgroup-empty when we had a recorded cgroup to check.
    if [[ -n $recorded_cgroup ]]; then
        _p9c0_ledger_append "cgroup-empty unit=$unit"
    fi
}

# ---------------------------------------------------------------------------
# Cleanup subcommand
# ---------------------------------------------------------------------------

_p9c0_cmd_cleanup() {
    local state_root="" run_id="" agent_id=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --state-root) state_root="$2"; shift 2 ;;
            --run-id) run_id="$2"; shift 2 ;;
            --agent-id) agent_id="$2"; shift 2 ;;
            *) _p9c0_die "cleanup: unknown flag $1" ;;
        esac
    done

    [[ -n $state_root ]] || _p9c0_die "cleanup: --state-root required"
    [[ -n $run_id ]] || _p9c0_die "cleanup: --run-id required"
    [[ -n $agent_id ]] || _p9c0_die "cleanup: --agent-id required"
    _p9c0_validate_run_id "$run_id"
    _p9c0_validate_agent_id "$agent_id"

    _p9c0_load_values "$state_root" "$run_id"

    local unit
    unit=$(_p9c0_unit_name "$agent_id" "$run_id")
    _p9c0_require_ledger_unit "$unit"

    _p9c0_with_lock "$state_root" "$run_id" _p9c0_cleanup_locked "$unit"
}

_p9c0_cleanup_locked() {
    local unit="$1"

    # Cleanup requires cgroup-empty proof.
    local state_dir
    state_dir="$P9C0_STATE_ROOT/$P9C0_RUN_ID"
    if ! grep -qE "^cgroup-empty unit=$unit( |$)" "$state_dir/ledger" 2>/dev/null; then
        _p9c0_die "cleanup: stop/cgroup proof missing for $unit"
    fi

    # Delete only ledger-listed run files.
    local files=(
        "$state_dir/agents.rendered.toml"
        "$state_dir/values.rendered"
        "$state_dir/context-e1.sqlite3"
        "$state_dir/context-e2.sqlite3"
    )
    local f
    for f in "${files[@]}"; do
        if [[ -e $f ]]; then
            # Ensure the file is inside the state root.
            _p9c0_is_under_root "$f" "$P9C0_STATE_ROOT" || _p9c0_die "cleanup: file escapes state root: $f"
            rm -f "$f"
        fi
    done

    _p9c0_ledger_append "cleanup unit=$unit"
    printf 'cleaned up %s\n' "$unit"
}

# ---------------------------------------------------------------------------
# Ledger helpers
# ---------------------------------------------------------------------------

_p9c0_require_ledger_unit() {
    local unit="$1"
    local ledger
    ledger="$P9C0_STATE_ROOT/$P9C0_RUN_ID/ledger"
    [[ -f $ledger ]] || _p9c0_die "ledger missing"
    local line found=0
    while IFS= read -r line; do
        if [[ $line == "unit $unit "* ]]; then
            found=1
            break
        fi
    done < "$ledger"
    [[ $found -eq 1 ]] || _p9c0_die "unit not in ledger: $unit"
}

# Fail-closed extraction of the one recorded cgroup for an exact unit.
# Prints the cgroup to stdout and returns 0. On any failure prints a diagnostic
# to stderr and returns 1 so the caller can fail closed.
_p9c0_recorded_cgroup_for_unit() {
    local unit="$1"
    local ledger
    ledger="$P9C0_STATE_ROOT/$P9C0_RUN_ID/ledger"
    if [[ ! -f $ledger ]]; then
        printf 'recorded cgroup: ledger missing\n' >&2
        return 1
    fi

    local line lineno=0 count=0 last_line=""
    while IFS= read -r line; do
        lineno=$((lineno + 1))
        if [[ $line == "unit $unit "* ]]; then
            count=$((count + 1))
            last_line="$line"
        fi
    done < "$ledger"

    if [[ $count -eq 0 ]]; then
        printf 'recorded cgroup: unit not in ledger: %s\n' "$unit" >&2
        return 1
    fi
    if [[ $count -ne 1 ]]; then
        printf 'recorded cgroup: duplicate unit records (%s) for %s\n' "$count" "$unit" >&2
        return 1
    fi

    # Extract cgroup=... value. It is the last field with an equals sign.
    local cgroup
    cgroup=$(printf '%s\n' "$last_line" | sed -n 's/.* cgroup=\([^ ]*\).*/\1/p')
    if [[ -z $cgroup ]]; then
        printf 'recorded cgroup: missing for unit: %s\n' "$unit" >&2
        return 1
    fi
    printf '%s\n' "$cgroup"
}

_p9c0_load_values() {
    local state_root="$1" run_id="$2"
    _p9c0_is_absolute_path "$state_root" || _p9c0_die "state-root must be absolute"
    _p9c0_validate_run_id "$run_id"

    local values_file
    values_file="$state_root/$run_id/values.rendered"
    [[ -f $values_file ]] || _p9c0_die "values.rendered missing; run render first"

    while IFS='=' read -r key value; do
        [[ -n $key ]] || continue
        case $key in
            state_root) P9C0_STATE_ROOT="$value" ;;
            run_id) P9C0_RUN_ID="$value" ;;
            fixture_bin) P9C0_FIXTURE_BIN="$value" ;;
            wrapper) P9C0_WRAPPER="$value" ;;
            coord_db) P9C0_COORD_DB="$value" ;;
            work_dir) P9C0_WORK_DIR="$value" ;;
            python) P9C0_PYTHON="$value" ;;
            repo_root) P9C0_REPO_ROOT="$value" ;;
        esac
    done < "$values_file"

    # Cross-check state_root/run_id against caller values.
    [[ $P9C0_STATE_ROOT == "$state_root" ]] || _p9c0_die "state_root mismatch"
    [[ $P9C0_RUN_ID == "$run_id" ]] || _p9c0_die "run_id mismatch"
}

# ---------------------------------------------------------------------------
# Locking
# ---------------------------------------------------------------------------

_p9c0_with_lock() {
    local state_root="$1" run_id="$2"
    shift 2
    local lock_file
    lock_file="$state_root/$run_id/lock"
    mkdir -p "$(dirname "$lock_file")"
    chmod 700 "$(dirname "$lock_file")"
    (
        _p9c0_flock -x 9 || _p9c0_die "cannot acquire lock"
        chmod 600 "$lock_file"
        "$@"
    ) 9>"$lock_file" || _p9c0_die "lock operation failed"
}

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

main() {
    [[ $# -ge 1 ]] || _p9c0_usage
    local cmd="$1"
    shift

    case $cmd in
        render|preflight|start|status|stop|cleanup) "_p9c0_cmd_$cmd" "$@" ;;
        *) _p9c0_usage ;;
    esac
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
