#!/usr/bin/env bash
# P9-3C0 local-verify controller.
#
# Operator-only controller scaffolding for the Package 3 fixture slice.
# Builds the per-run state directory, fixed subdirectories, phase record,
# append-only ledger, the fixed Coordinate isolation wrapper plus its
# controller-sealed manifest, and the helper-rendered fixture assets.  Later
# subcommands drive only the isolated sidecar; canonical production identities
# remain read-only comparison authority.
#
# Sourceable: `source` runs only the seam/constant/function definitions and
# skips main. The Bash 3.2 guard `[[ ${BASH_SOURCE[0]} == "$0" ]]` gates the
# `prepare` subcommand so tests can override seams and call helpers directly.

set -uo pipefail

# ---------------------------------------------------------------------------
# Replaceable functions for testing; production entrypoint uses real commands.
# ---------------------------------------------------------------------------

_p9c0_real_euid() {
    id -u
}

_p9c0_real_identity_lookup_user() {
    id -u "$1"
}

_p9c0_real_identity_lookup_group() {
    getent group "$1" | awk -F: 'NR == 1 { print $3 }'
}

_p9c0_real_realpath() {
    realpath "$1"
}

# Canonicalize a path that may have non-existent leaf components, resolving
# all symlinks in the existing ancestor chain. Requires an absolute path and
# rejects missing suffix components that are empty, ".", or ".." so the
# reassembled value remains canonical. Fail-closed: if an existing ancestor
# cannot be resolved (e.g. permission denied or broken symlink), return
# non-zero. Do not use eval.
_p9c0_real_realpath_missing_ok() {
    local candidate="$1" parent resolved rest component
    candidate="${candidate%/}"
    [[ -n "$candidate" && "$candidate" == /* ]] || return 1
    if [[ -e "$candidate" || -L "$candidate" ]]; then
        realpath "$candidate"
        return $?
    fi
    parent="$candidate"
    rest=""
    while [[ "$parent" != "/" ]]; do
        if [[ -e "$parent" || -L "$parent" ]]; then
            break
        fi
        component="${parent##*/}"
        [[ -n "$component" && "$component" != "." && "$component" != ".." ]] || return 1
        rest="/${component}${rest}"
        parent="${parent%/*}"
        [[ -n "$parent" ]] || parent="/"
    done
    resolved="$(realpath "$parent")" || return 1
    printf '%s%s\n' "$resolved" "$rest"
}

_p9c0_real_stat_file() {
    stat -c '%d:%i:%s:%h:%u:%g:%a' "$1"
}

_p9c0_real_sha256_file() {
    sha256sum "$1" 2>/dev/null | awk '{print $1}'
}

_p9c0_real_chown() {
    chown "$1:$2" "$3"
}

_p9c0_real_chmod() {
    chmod "$1" "$2"
}

_p9c0_real_mkdir() {
    mkdir -m "$1" "$2"
}

_p9c0_real_install() {
    install -m "$1" "$2" "$3"
}

_p9c0_real_runuser() {
    env -i PATH=/usr/local/bin:/usr/bin:/bin /usr/sbin/runuser "$@"
}

_p9c0_real_helper_exact_stop() {
    local unit="$1" run_id="${2:-$P9C0_RUN_ID}" agent expected
    for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        expected="$agent-$run_id.service"
        if [[ "$unit" == "$expected" ]]; then
            /opt/multinexus/multinexus/fixture/bin/p9-3c0-unit.sh stop \
                --state-root "$P9C0_PROD_STATE_PREFIX" \
                --run-id "$run_id" \
                --agent-id "$agent"
            return $?
        fi
    done
    return 1
}

_p9c0_real_unit_helper() {
    /opt/multinexus/multinexus/fixture/bin/p9-3c0-unit.sh "$@"
}

_p9c0_real_flock() {
    flock "$@"
}

_p9c0_euid() { _p9c0_real_euid; }
_p9c0_identity_lookup_user() { _p9c0_real_identity_lookup_user "$@"; }
_p9c0_identity_lookup_group() { _p9c0_real_identity_lookup_group "$@"; }
_p9c0_realpath() { _p9c0_real_realpath "$@"; }
_p9c0_realpath_missing_ok() { _p9c0_real_realpath_missing_ok "$@"; }
_p9c0_stat_file() { _p9c0_real_stat_file "$@"; }
_p9c0_sha256_file() { _p9c0_real_sha256_file "$@"; }
_p9c0_chown() { _p9c0_real_chown "$@"; }
_p9c0_chmod() { _p9c0_real_chmod "$@"; }
_p9c0_mkdir() { _p9c0_real_mkdir "$@"; }
_p9c0_install() { _p9c0_real_install "$@"; }
_p9c0_runuser() { _p9c0_real_runuser "$@"; }
_p9c0_helper_exact_stop() { _p9c0_real_helper_exact_stop "$@"; }
_p9c0_unit_helper() { _p9c0_real_unit_helper "$@"; }
_p9c0_flock() { _p9c0_real_flock "$@"; }

# ---------------------------------------------------------------------------
# Static constants
# ---------------------------------------------------------------------------

P9C0_PROD_STATE_PREFIX="/var/tmp/multinexus-p9-3c0"
P9C0_RUN_ID_RE='^[a-z0-9]+(-[a-z0-9]+)*$'
P9C0_AGENT_ID_RE='^[a-z0-9]+(-[a-z0-9]+)*$'
P9C0_WRAPPER_BASENAME="coord-isolated"
P9C0_WRAPPER_MANIFEST_FILENAME="wrapper.manifest"
P9C0_WRAPPER_EXEC="/opt/coordinate/.venv/bin/coordinate"
P9C0_PROD_WRAPPER="/usr/local/bin/coord-local"
P9C0_PROD_DB="/var/lib/coordinate/coord.sqlite3"
P9C0_DEPLOYED_REPO_ROOT="/opt/multinexus"
P9C0_FIXTURE_BIN="/opt/multinexus/multinexus/fixture/bin/p9-3c0-fixture.py"
P9C0_FIXTURE_PYTHON="/opt/multinexus/.venv/bin/python"
P9C0_FIXTURE_CONFIG_ROOT="/opt/multinexus/multinexus/fixture/config"
P9C0_EXECUTOR_V1="$P9C0_FIXTURE_CONFIG_ROOT/executor.fixture.v1-disabled.toml"
P9C0_CAPACITY_V1="$P9C0_FIXTURE_CONFIG_ROOT/capacity.fixture.v1.toml"
P9C0_EXECUTOR_V2="$P9C0_FIXTURE_CONFIG_ROOT/executor.fixture.v2-enabled.toml"
P9C0_EXECUTOR_V3="$P9C0_FIXTURE_CONFIG_ROOT/executor.fixture.v3-disabled.toml"
P9C0_CAPACITY_V2="$P9C0_FIXTURE_CONFIG_ROOT/capacity.fixture.v2-empty.toml"
P9C0_EXECUTOR_V4="$P9C0_FIXTURE_CONFIG_ROOT/executor.fixture.v4-empty.toml"
P9C0_WORKSPACE_ID="p9-3c0-sidecar"
P9C0_AGENT_ALLOWLIST=("p9-3c-fixture-e1" "p9-3c-fixture-e2")

P9C0_PHASE_BOOT="boot"
P9C0_PHASE_INTAKE="intake"
P9C0_PHASE_AUTHORIZE="authorize"
P9C0_PHASE_RENDER="render"
P9C0_PHASE_READY="foundation-ready"
P9C0_PHASE_BASELINE="baseline"
P9C0_PHASE_CATALOG="catalog-ready"
P9C0_PHASE_BASE="base-complete"
P9C0_PHASE_HOLD="hold-stopped"
P9C0_PHASE_FIRST_REAP="first-reap"
P9C0_PHASE_RECOVERY="recovery-ready"
P9C0_PHASE_STALE="stale-rejected"
P9C0_PHASE_SECOND_REAP="second-reap"
P9C0_PHASE_CLEANUP_READY="cleanup-ready"
P9C0_PHASE_DONE="done"
P9C0_PHASE_FAILED="failed"
P9C0_PHASE_ORDER=(
    "$P9C0_PHASE_BOOT"
    "$P9C0_PHASE_INTAKE"
    "$P9C0_PHASE_AUTHORIZE"
    "$P9C0_PHASE_RENDER"
    "$P9C0_PHASE_READY"
    "$P9C0_PHASE_BASELINE"
    "$P9C0_PHASE_CATALOG"
    "$P9C0_PHASE_BASE"
    "$P9C0_PHASE_HOLD"
    "$P9C0_PHASE_FIRST_REAP"
    "$P9C0_PHASE_RECOVERY"
    "$P9C0_PHASE_STALE"
    "$P9C0_PHASE_SECOND_REAP"
    "$P9C0_PHASE_CLEANUP_READY"
    "$P9C0_PHASE_DONE"
)

P9C0_INTAKE_OPEN="open"
P9C0_INTAKE_FROZEN="frozen"

P9C0_ROOT_SUBDIRS=("control" "lock" "ledger" "evidence")
P9C0_UNIT_SUBDIRS=("db" "work" "harness" "context")

# Credential authority is expressed only as exact variable names.  Prefixes
# are expanded from the environment's *names* (never values); literal wildcard
# entries are never passed to systemd because UnsetEnvironment does not expand
# them.
P9C0_CREDENTIAL_DENYLIST=(
    "ANTHROPIC_API_KEY"
    "CLAUDE_API_KEY"
    "OPENAI_API_KEY"
    "CODEX_API_KEY"
    "KIMI_API_KEY"
    "MOONSHOT_API_KEY"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
    "AWS_SESSION_TOKEN"
    "AZURE_OPENAI_API_KEY"
    "GOOGLE_API_KEY"
    "GOOGLE_APPLICATION_CREDENTIALS"
    "VERTEX_API_KEY"
    "DISCORD_TOKEN"
    "KOOK_TOKEN"
    "HTTP_PROXY"
    "HTTPS_PROXY"
    "ALL_PROXY"
    "NO_PROXY"
    "http_proxy"
    "https_proxy"
    "all_proxy"
    "no_proxy"
    "MULTINEXUS_DB_ROOT_TOKEN"
    "MULTINEXUS_AGENT_REGISTRY_TOKEN"
    "MULTINEXUS_JWT_SIGNING_KEY"
    "MULTINEXUS_PROVIDER_API_KEY"
    "MULTINEXUS_OAUTH_CLIENT_SECRET"
)

P9C0_CREDENTIAL_PREFIXES=(
    "ANTHROPIC_" "CLAUDE_" "OPENAI_" "CODEX_" "KIMI_" "MOONSHOT_"
    "AWS_" "AZURE_" "GOOGLE_" "VERTEX_" "DISCORD_" "KOOK_"
)

# ---------------------------------------------------------------------------
# Production path resolution helpers
# ---------------------------------------------------------------------------

_p9c0_controller_state_prefix() {
    printf '%s\n' "$P9C0_PROD_STATE_PREFIX"
}

_p9c0_assert_state_prefix_authority() {
    [[ "$1" == "$P9C0_PROD_STATE_PREFIX" ]]
}

_p9c0_assert_state_prefix_resolved() {
    local prefix_resolved production_resolved
    prefix_resolved="$(_p9c0_realpath "$1")" || return 1
    production_resolved="$(_p9c0_realpath "$P9C0_PROD_STATE_PREFIX")" || return 1
    [[ "$prefix_resolved" == "$production_resolved" ]]
}

_p9c0_environment_names() {
    compgen -e
}

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

_p9c0_die() {
    printf 'p9-3c0-local-verify: %s\n' "$1" >&2
    exit "${2:-1}"
}

_p9c0_usage() {
    _p9c0_die "usage: $0 prepare|verify --run-id <id> --unit-user <name> --unit-group <name> [--agent <id>]" 2
}

# ---------------------------------------------------------------------------
# Path/identity validation
# ---------------------------------------------------------------------------

_p9c0_is_absolute_path() {
    [[ $1 == /* ]]
}

_p9c0_is_under_root() {
    local candidate="$1" root="$2"
    [[ "$candidate" == "$root" || "$candidate" == "$root"/* ]]
}

_p9c0_validate_run_id() {
    [[ -n "$1" && ${#1} -le 64 && "$1" =~ $P9C0_RUN_ID_RE ]]
}

_p9c0_validate_agent_id() {
    [[ "$1" =~ $P9C0_AGENT_ID_RE ]]
}

_p9c0_validate_credentials_denied() {
    local name
    for name in "${P9C0_CREDENTIAL_DENYLIST[@]}"; do
        [[ "$name" == *"*"* ]] && _p9c0_die "denylist entry contains wildcard: $name" 10
    done
    [[ $# -eq 0 ]] && return 0
    local request="$1"
    for name in "${P9C0_CREDENTIAL_DENYLIST[@]}"; do
        if [[ "$request" == "$name" ]]; then
            _p9c0_die "credential name denied: $name" 12
        fi
    done
    return 0
}

_p9c0_collect_unset_environment_names() {
    local name prefix seen=" "
    for name in "${P9C0_CREDENTIAL_DENYLIST[@]}"; do
        [[ "$name" != *"*"* ]] || _p9c0_die "denylist entry contains wildcard: $name" 10
        case "$seen" in *" $name "*) ;; *) printf '%s\n' "$name"; seen="$seen$name " ;; esac
    done
    while IFS= read -r name; do
        [[ -n "$name" && "$name" != *"*"* ]] || continue
        for prefix in "${P9C0_CREDENTIAL_PREFIXES[@]}"; do
            if [[ "$name" == "$prefix"* ]]; then
                case "$seen" in *" $name "*) ;; *) printf '%s\n' "$name"; seen="$seen$name " ;; esac
                break
            fi
        done
    done < <(_p9c0_environment_names)
}

# ---------------------------------------------------------------------------
# Ledger / phase record helpers
# ---------------------------------------------------------------------------

_p9c0_ledger_path() {
    printf '%s/%s/ledger/events.jsonl\n' "$(_p9c0_controller_state_prefix)" "$P9C0_RUN_ID"
}

_p9c0_phase_record_path() {
    printf '%s/%s/control/phase\n' "$(_p9c0_controller_state_prefix)" "$P9C0_RUN_ID"
}

_p9c0_intake_record_path() {
    printf '%s/%s/control/intake\n' "$(_p9c0_controller_state_prefix)" "$P9C0_RUN_ID"
}

_p9c0_evidence_record_path() {
    printf '%s/%s/evidence/evidence\n' "$(_p9c0_controller_state_prefix)" "$P9C0_RUN_ID"
}

_p9c0_failure_record_path() {
    printf '%s/%s/control/failure\n' "$(_p9c0_controller_state_prefix)" "$P9C0_RUN_ID"
}

_p9c0_ledger_append() {
    local line="$1"
    local ledger
    ledger="$(_p9c0_ledger_path)"
    [[ -f "$ledger" && ! -L "$ledger" ]] || _p9c0_die "ledger unavailable: $ledger" 17
    printf '%s\n' "$line" >> "$ledger" \
        || _p9c0_die "ledger append failed: $ledger" 17
}

_p9c0_atomic_root_record() {
    local path="$1" content="$2" tmp="$1.next.$$"
    [[ ! -e "$tmp" && ! -L "$tmp" ]] || _p9c0_die "record temp already exists: $tmp" 18
    (umask 077; set -o noclobber; printf '%s\n' "$content" > "$tmp") \
        || _p9c0_die "record temp create failed: $tmp" 19
    _p9c0_chown 0 0 "$tmp" || _p9c0_die "record chown failed: $tmp" 19
    _p9c0_chmod 0600 "$tmp" || _p9c0_die "record chmod failed: $tmp" 19
    mv -f "$tmp" "$path" || _p9c0_die "record replace failed: $path" 19
}

_p9c0_record_phase() {
    local phase="$1"
    _p9c0_atomic_root_record "$(_p9c0_phase_record_path)" "phase=$phase"
}

_p9c0_record_intake() {
    local state="$1"
    _p9c0_atomic_root_record "$(_p9c0_intake_record_path)" "intake=$state"
}

_p9c0_record_evidence() {
    local state="${1:-frozen}"
    _p9c0_atomic_root_record "$(_p9c0_evidence_record_path)" "evidence=$state"
}

_p9c0_phase_rank() {
    local phase="$1" idx
    for idx in "${!P9C0_PHASE_ORDER[@]}"; do
        if [[ "${P9C0_PHASE_ORDER[$idx]}" == "$phase" ]]; then
            printf '%s\n' "$idx"
            return 0
        fi
    done
    return 1
}

_p9c0_transition_phase() {
    local next_phase="$1" current rank_next rank_current
    if [[ "$next_phase" == "$P9C0_PHASE_FAILED" ]]; then
        if [[ -f "$(_p9c0_phase_record_path)" ]]; then
            current="$(sed -n 's/^phase=//p' "$(_p9c0_phase_record_path)")"
            [[ "$current" == "$P9C0_PHASE_FAILED" ]] && return 0
            [[ "$current" != "$P9C0_PHASE_DONE" ]] \
                || _p9c0_die "cannot fail completed phase" 13
        fi
        _p9c0_record_phase "$P9C0_PHASE_FAILED"
        return 0
    fi
    _p9c0_phase_rank "$next_phase" >/dev/null || _p9c0_die "unknown phase: $next_phase" 13
    if [[ -f "$(_p9c0_phase_record_path)" ]]; then
        current="$(cat "$(_p9c0_phase_record_path)" 2>/dev/null | sed -n 's/^phase=//p')"
        if [[ -z "$current" ]]; then
            _p9c0_die "phase record is empty" 14
        fi
        [[ "$current" != "$P9C0_PHASE_FAILED" ]] \
            || _p9c0_die "cannot leave failed phase" 16
        rank_current="$(_p9c0_phase_rank "$current")" || _p9c0_die "recorded phase unknown: $current" 15
        rank_next="$(_p9c0_phase_rank "$next_phase")"
        if (( rank_next <= rank_current )); then
            _p9c0_die "non-monotonic phase transition: $current -> $next_phase" 16
        fi
    fi
    _p9c0_record_phase "$next_phase"
}

# ---------------------------------------------------------------------------
# State directory layout
# ---------------------------------------------------------------------------

_p9c0_per_run_root() {
    printf '%s/%s\n' "$(_p9c0_controller_state_prefix)" "${P9C0_RUN_ID:-}"
}

_p9c0_worktree_path_for_agent() {
    local agent="$1" allowed
    for allowed in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        if [[ "$agent" == "$allowed" ]]; then
            printf '%s/work/%s\n' "$(_p9c0_per_run_root)" "$agent"
            return 0
        fi
    done
    return 1
}

_p9c0_wrapper_path() {
    printf '%s/%s\n' "$(_p9c0_per_run_root)" "$P9C0_WRAPPER_BASENAME"
}

_p9c0_wrapper_manifest_path() {
    printf '%s/%s\n' "$(_p9c0_per_run_root)" "$P9C0_WRAPPER_MANIFEST_FILENAME"
}

_p9c0_isolation_db_path() {
    printf '%s/%s/db/coord.sqlite3\n' "$(_p9c0_controller_state_prefix)" "${P9C0_RUN_ID:-}"
}

_p9c0_controller_db_path() {
    if [[ -n "${P9C0_COORD_DB:-}" ]]; then
        printf '%s\n' "$P9C0_COORD_DB"
    else
        _p9c0_isolation_db_path
    fi
}

_p9c0_enforce_root_owned_dir() {
    local path="$1" mode="$2" uid_owned="$3" gid_owned="$4"
    [[ -d "$path" ]] || return 1
    [[ ! -L "$path" ]] || return 1
    local stat_line nlink uid gid perms
    stat_line="$(_p9c0_stat_file "$path")"
    IFS=: read -r _ _ _ nlink uid gid perms <<< "$stat_line"
    [[ "$uid" == "$uid_owned" ]] || return 1
    [[ "$gid" == "$gid_owned" ]] || return 1
    [[ "$perms" == "$mode" ]] || return 1
    [[ "$nlink" =~ ^[0-9]+$ && "$nlink" -ge 2 ]] || return 1
    return 0
}

_p9c0_enforce_root_owned_file() {
    local path="$1" mode="$2" uid_owned="$3" gid_owned="$4"
    [[ -f "$path" ]] || return 1
    [[ ! -L "$path" ]] || return 1
    local stat_line nlink uid gid perms
    stat_line="$(_p9c0_stat_file "$path")"
    IFS=: read -r _ _ _ nlink uid gid perms <<< "$stat_line"
    [[ "$uid" == "$uid_owned" ]] || return 1
    [[ "$gid" == "$gid_owned" ]] || return 1
    [[ "$perms" == "$mode" ]] || return 1
    [[ "$nlink" == "1" ]] || return 1
    return 0
}

_p9c0_layout_prefix() {
    local prefix="$1"
    if [[ -e "$prefix" ]]; then
        _p9c0_enforce_root_owned_dir "$prefix" "755" "0" "0" \
            || _p9c0_die "state prefix not root:root 0755: $prefix" 20
        return 0
    fi
    _p9c0_mkdir 755 "$prefix" || {
        _p9c0_enforce_root_owned_dir "$prefix" "755" "0" "0" \
            || _p9c0_die "state prefix create race rejected: $prefix" 20
        return 0
    }
    _p9c0_chown 0 0 "$prefix" || _p9c0_die "state prefix chown failed: $prefix" 20
    _p9c0_chmod 755 "$prefix" || _p9c0_die "state prefix chmod failed: $prefix" 20
}

_p9c0_layout_per_run() {
    local run_root unit_uid unit_gid
    run_root="$(_p9c0_per_run_root)"
    unit_uid="$P9C0_UNIT_UID"
    unit_gid="$P9C0_UNIT_GID"

    [[ ! -e "$run_root" && ! -L "$run_root" ]] \
        || _p9c0_die "per-run root already exists; refusing repeat prepare: $run_root" 21
    _p9c0_mkdir 750 "$run_root" || _p9c0_die "per-run root create failed: $run_root" 21
    _p9c0_chown 0 "$unit_gid" "$run_root" || _p9c0_die "per-run root chown failed: $run_root" 21
    _p9c0_chmod 750 "$run_root" || _p9c0_die "per-run root chmod failed: $run_root" 21

    local sub
    for sub in "${P9C0_ROOT_SUBDIRS[@]}"; do
        local target="$run_root/$sub"
        _p9c0_mkdir 700 "$target" || _p9c0_die "root subdir create failed: $target" 22
        _p9c0_chown 0 0 "$target" || _p9c0_die "root subdir chown failed: $target" 22
        _p9c0_chmod 700 "$target" || _p9c0_die "root subdir chmod failed: $target" 22
    done

    for sub in "${P9C0_UNIT_SUBDIRS[@]}"; do
        local target="$run_root/$sub"
        _p9c0_mkdir 700 "$target" || _p9c0_die "unit subdir create failed: $target" 23
        _p9c0_chown "$unit_uid" "$unit_gid" "$target" || _p9c0_die "unit subdir chown failed: $target" 23
        _p9c0_chmod 700 "$target" || _p9c0_die "unit subdir chmod failed: $target" 23
    done

    local agent worktree
    for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        worktree="$(_p9c0_worktree_path_for_agent "$agent")" \
            || _p9c0_die "worktree path derivation failed: $agent" 23
        _p9c0_mkdir 700 "$worktree" \
            || _p9c0_die "agent worktree create failed: $worktree" 23
        _p9c0_chown "$unit_uid" "$unit_gid" "$worktree" \
            || _p9c0_die "agent worktree chown failed: $worktree" 23
        _p9c0_chmod 700 "$worktree" \
            || _p9c0_die "agent worktree chmod failed: $worktree" 23
    done

    local ledger
    ledger="$(_p9c0_ledger_path)"
    (umask 077; : > "$ledger") || _p9c0_die "cannot create ledger: $ledger" 24
    _p9c0_chown 0 0 "$ledger" || _p9c0_die "ledger chown failed: $ledger" 24
    _p9c0_chmod 0600 "$ledger" || _p9c0_die "ledger chmod failed: $ledger" 24

    local lock_file
    for lock_file in "$run_root/lock/controller.lock" "$run_root/lock/unit-helper.lock"; do
        (umask 077; : > "$lock_file") || _p9c0_die "lock file create failed: $lock_file" 24
        _p9c0_chown 0 0 "$lock_file" || _p9c0_die "lock file chown failed: $lock_file" 24
        _p9c0_chmod 0600 "$lock_file" || _p9c0_die "lock file chmod failed: $lock_file" 24
    done
}

_p9c0_reject_unknown_run_entries() {
    local run_root entry base
    run_root="$(_p9c0_per_run_root)"
    for entry in "$run_root"/* "$run_root"/.[!.]* "$run_root"/..?*; do
        [[ -e "$entry" || -L "$entry" ]] || continue
        base="${entry##*/}"
        case "$base" in
            control|lock|ledger|evidence|db|work|harness|context|coord-isolated|wrapper.manifest|agents.rendered.toml|values.rendered|systemd.verify.service)
                ;;
            *)
                _p9c0_die "unknown pre-existing per-run entry: $entry" 25
                ;;
        esac
    done
}

_p9c0_with_run_lock() {
    local run_root lock_file status
    run_root="$(_p9c0_per_run_root)"
    lock_file="$run_root/lock/controller.lock"
    _p9c0_enforce_root_owned_dir "$run_root/lock" "700" "0" "0" \
        || _p9c0_die "run lock directory authority rejected: $run_root/lock" 26
    if [[ ! -e "$lock_file" && ! -L "$lock_file" ]]; then
        (umask 077; set -o noclobber; : > "$lock_file") \
            || _p9c0_die "run lock create failed: $lock_file" 26
        _p9c0_chown 0 0 "$lock_file" || _p9c0_die "run lock chown failed: $lock_file" 26
        _p9c0_chmod 0600 "$lock_file" || _p9c0_die "run lock chmod failed: $lock_file" 26
    fi
    _p9c0_enforce_root_owned_file "$lock_file" "600" "0" "0" \
        || _p9c0_die "run lock file authority rejected: $lock_file" 26
    exec 9>>"$lock_file" || _p9c0_die "run lock open failed: $lock_file" 26
    _p9c0_flock -x 9 || _p9c0_die "run lock acquire failed: $lock_file" 26
    "$@"
    status=$?
    _p9c0_flock -u 9 || status=1
    exec 9>&-
    return "$status"
}

# ---------------------------------------------------------------------------
# Wrapper authority / manifest
# ---------------------------------------------------------------------------

_p9c0_wrapper_manifest_record() {
    local wrapper_raw="$1" stat_line sha
    stat_line="$(_p9c0_stat_file "$wrapper_raw")" || return 1
    sha="$(_p9c0_sha256_file "$wrapper_raw")" || return 1
    printf 'wrapper_raw=%s\twrapper_dev_inode_size_nlink_uid_gid_mode=%s\twrapper_sha256=%s\n' \
        "$wrapper_raw" "$stat_line" "$sha"
}

_p9c0_is_production_resolved() {
    local candidate="$1" production="$2"
    local resolved production_resolved
    resolved="$(_p9c0_realpath "$candidate")" || return 1
    production_resolved="$(_p9c0_realpath "$production")" || return 1
    [[ "$resolved" == "$production_resolved" ]]
}

_p9c0_wrapper_is_safe_under_prefix() {
    local wrapper_raw="$1" prefix="$2" production="$3"
    _p9c0_is_under_root "$wrapper_raw" "$prefix" || return 1
    local resolved prefix_resolved production_resolved
    resolved="$(_p9c0_realpath "$wrapper_raw")" || return 1
    prefix_resolved="$(_p9c0_realpath "$prefix")" || return 1
    production_resolved="$(_p9c0_realpath "$production")" || return 1
    [[ "$resolved" != "$production_resolved" ]] || return 1
    _p9c0_is_under_root "$resolved" "$prefix_resolved" || return 1
    local stat_line nlink
    stat_line="$(_p9c0_stat_file "$wrapper_raw")"
    nlink="$(printf '%s\n' "$stat_line" | cut -d: -f4)"
    [[ "$nlink" == "1" ]] || return 1
    return 0
}

_p9c0_enforce_wrapper_authority() {
    local wrapper_raw="$1" prefix="$2" production="$3" expected_gid="$4" expected_sha="$5"
    local stat_line nlink uid gid perms
    [[ ! -L "$wrapper_raw" ]] || _p9c0_die "wrapper is symlink: $wrapper_raw" 30
    [[ -f "$wrapper_raw" ]] || _p9c0_die "wrapper missing: $wrapper_raw" 31
    stat_line="$(_p9c0_stat_file "$wrapper_raw")"
    IFS=: read -r _ _ _ nlink uid gid perms <<< "$stat_line"
    [[ "$nlink" == "1" ]] || _p9c0_die "wrapper hardlinked: $wrapper_raw" 33
    [[ "$uid" == "0" ]] || _p9c0_die "wrapper not root-owned: $wrapper_raw" 34
    [[ "$gid" == "$expected_gid" ]] || _p9c0_die "wrapper gid mismatch: $wrapper_raw" 35
    [[ "$perms" == "750" ]] || _p9c0_die "wrapper mode not 0750: $wrapper_raw" 36
    _p9c0_wrapper_is_safe_under_prefix "$wrapper_raw" "$prefix" "$production" \
        || _p9c0_die "wrapper raw/resolved path is unauthorized: $wrapper_raw" 39
    local sha
    sha="$(_p9c0_sha256_file "$wrapper_raw")"
    [[ -n "$expected_sha" && "$sha" == "$expected_sha" ]] \
        || _p9c0_die "wrapper SHA drift: $wrapper_raw" 40
}

_p9c0_enforce_unit_identity() {
    local user="$1" group="$2" uid_owned="$3" gid_owned="$4" db="$5" production_db="$6"
    [[ "$user" != "root" ]] || _p9c0_die "unit user cannot be root" 50
    [[ "$group" != "root" ]] || _p9c0_die "unit group cannot be root" 51
    local uid gid
    uid="$(_p9c0_identity_lookup_user "$user")" || _p9c0_die "unit user missing: $user" 52
    gid="$(_p9c0_identity_lookup_group "$group")" || _p9c0_die "unit group missing: $group" 53
    [[ "$uid" =~ ^[0-9]+$ ]] || _p9c0_die "unit user non-numeric uid: $user" 54
    [[ "$gid" =~ ^[0-9]+$ ]] || _p9c0_die "unit group non-numeric gid: $group" 55
    [[ "$uid" != "0" ]] || _p9c0_die "unit user uid=0: $user" 56
    [[ "$gid" != "0" ]] || _p9c0_die "unit group gid=0: $group" 57
    [[ "$uid" == "$uid_owned" ]] || _p9c0_die "uid mismatch for $user" 58
    [[ "$gid" == "$gid_owned" ]] || _p9c0_die "gid mismatch for $group" 59
    _p9c0_is_under_root "$db" "$(_p9c0_controller_state_prefix)" \
        || _p9c0_die "isolation db raw path escapes state prefix: $db" 60
    local db_resolved prefix_resolved production_db_resolved
    db_resolved="$(_p9c0_realpath_missing_ok "$db")" || _p9c0_die "isolation db realpath failed: $db" 60
    prefix_resolved="$(_p9c0_realpath_missing_ok "$(_p9c0_controller_state_prefix)")" \
        || _p9c0_die "state prefix realpath failed" 60
    production_db_resolved="$(_p9c0_realpath "$production_db")" \
        || _p9c0_die "production db realpath failed" 60
    _p9c0_is_under_root "$db_resolved" "$prefix_resolved" \
        || _p9c0_die "isolation db resolved path escapes state prefix: $db" 60
    [[ "$db_resolved" != "$production_db_resolved" ]] \
        || _p9c0_die "isolation db resolves to production: $db" 60
    return 0
}

_p9c0_render_wrapper() {
    local wrapper_raw="$1" run_root="$2" unit_uid="$3" unit_gid="$4" db_path="$5"
    local manifest_path prefix_resolved production_wrapper_resolved production_db_resolved
    manifest_path="$(_p9c0_wrapper_manifest_path)"
    prefix_resolved="$(_p9c0_realpath "$(_p9c0_controller_state_prefix)")" \
        || _p9c0_die "state prefix realpath failed" 61
    production_wrapper_resolved="$(_p9c0_realpath "$P9C0_PROD_WRAPPER")" \
        || _p9c0_die "production wrapper realpath failed" 62
    production_db_resolved="$(_p9c0_realpath "$P9C0_PROD_DB")" \
        || _p9c0_die "production db realpath failed" 63
    local body
    body="$(printf '%s\n' \
        "#!/bin/sh" \
        "# Auto-generated by p9-3c0-local-verify. Do not edit by hand." \
        "# Revalidates its sealed manifest before fixed-argv Coordinate exec." \
        "set -eu" \
        "set -f" \
        "" \
        "SELF='$wrapper_raw'" \
        "MANIFEST='$manifest_path'" \
        "STATE_PREFIX_RESOLVED='$prefix_resolved'" \
        "PRODUCTION_WRAPPER_RESOLVED='$production_wrapper_resolved'" \
        "PRODUCTION_DB_RESOLVED='$production_db_resolved'" \
        "EXPECTED_EXEC='$P9C0_WRAPPER_EXEC'" \
        "EXPECTED_DB='$db_path'" \
        "EXPECTED_GID='$unit_gid'" \
        "" \
        "die() { echo \"coord-isolated: \$1\" >&2; exit \"\${2:-70}\"; }" \
        "[ \"\$0\" = \"\$SELF\" ] || die 'raw wrapper path mismatch' 70" \
        "[ -f \"\$SELF\" ] && [ ! -L \"\$SELF\" ] || die 'wrapper type rejected' 71" \
        "[ -f \"\$MANIFEST\" ] && [ ! -L \"\$MANIFEST\" ] || die 'manifest type rejected' 72" \
        "[ \"\$(wc -l < \"\$MANIFEST\" | tr -d ' ')\" = 1 ] || die 'manifest must be one line' 73" \
        "MANIFEST_STAT=\$(stat -c '%d:%i:%s:%h:%u:%g:%a' -- \"\$MANIFEST\") || die 'manifest stat failed' 74" \
        "MANIFEST_NLINK=\$(printf '%s\\n' \"\$MANIFEST_STAT\" | cut -d: -f4)" \
        "MANIFEST_UID=\$(printf '%s\\n' \"\$MANIFEST_STAT\" | cut -d: -f5)" \
        "MANIFEST_GID=\$(printf '%s\\n' \"\$MANIFEST_STAT\" | cut -d: -f6)" \
        "MANIFEST_MODE=\$(printf '%s\\n' \"\$MANIFEST_STAT\" | cut -d: -f7)" \
        "[ \"\$MANIFEST_NLINK\" = 1 ] && [ \"\$MANIFEST_UID\" = 0 ] && [ \"\$MANIFEST_GID\" = \"\$EXPECTED_GID\" ] && [ \"\$MANIFEST_MODE\" = 640 ] || die 'manifest metadata drift' 75" \
        "SELF_RESOLVED=\$(realpath -- \"\$SELF\") || die 'wrapper realpath failed' 76" \
        "DB_RESOLVED=\$(realpath -m -- \"\$EXPECTED_DB\") || die 'db realpath failed' 77" \
        "case \"\$SELF_RESOLVED\" in \"\$STATE_PREFIX_RESOLVED\"/*) ;; *) die 'wrapper escapes state prefix' 78;; esac" \
        "[ \"\$SELF_RESOLVED\" != \"\$PRODUCTION_WRAPPER_RESOLVED\" ] || die 'production wrapper rejected' 79" \
        "case \"\$DB_RESOLVED\" in \"\$STATE_PREFIX_RESOLVED\"/*) ;; *) die 'db escapes state prefix' 80;; esac" \
        "[ \"\$DB_RESOLVED\" != \"\$PRODUCTION_DB_RESOLVED\" ] || die 'production db rejected' 81" \
        "LIVE_STAT=\$(stat -c '%d:%i:%s:%h:%u:%g:%a' -- \"\$SELF\") || die 'wrapper stat failed' 82" \
        "LIVE_SHA=\$(sha256sum \"\$SELF\" | awk '{print \$1}') || die 'wrapper sha failed' 83" \
        "TAB=\$(printf '\\t')" \
        "LIVE_LINE=\"wrapper_raw=\$SELF\${TAB}wrapper_dev_inode_size_nlink_uid_gid_mode=\$LIVE_STAT\${TAB}wrapper_sha256=\$LIVE_SHA\"" \
        "READ_BYTES=\$(cat \"\$MANIFEST\") || die 'manifest read failed' 84" \
        "[ \"\$READ_BYTES\" = \"\$LIVE_LINE\" ] || die 'manifest content drift' 85" \
        "exec \"\$EXPECTED_EXEC\" --db \"\$EXPECTED_DB\" \"\$@\"" \
    )"
    _p9c0_install 750 <(printf '%s\n' "$body") "$wrapper_raw" \
        || _p9c0_die "wrapper install failed: $wrapper_raw" 63
    _p9c0_chown 0 "$unit_gid" "$wrapper_raw" \
        || _p9c0_die "wrapper chown failed: $wrapper_raw" 63
    _p9c0_chmod 750 "$wrapper_raw" \
        || _p9c0_die "wrapper chmod failed: $wrapper_raw" 63
}

_p9c0_seal_wrapper_manifest() {
    local wrapper_raw="$1"
    local manifest_path
    manifest_path="$(_p9c0_wrapper_manifest_path)"
    [[ ! -e "$manifest_path" && ! -L "$manifest_path" ]] \
        || _p9c0_die "manifest already exists: $manifest_path" 64
    (umask 027; set -o noclobber; _p9c0_wrapper_manifest_record "$wrapper_raw" > "$manifest_path") \
        || _p9c0_die "manifest create failed: $manifest_path" 65
    _p9c0_chown 0 "$P9C0_UNIT_GID" "$manifest_path" \
        || _p9c0_die "manifest chown failed: $manifest_path" 66
    _p9c0_chmod 640 "$manifest_path" \
        || _p9c0_die "manifest chmod failed: $manifest_path" 66
    _p9c0_enforce_root_owned_file "$manifest_path" "640" "0" "$P9C0_UNIT_GID" \
        || _p9c0_die "manifest metadata invalid: $manifest_path" 66
}

# ---------------------------------------------------------------------------
# Coordinator invocation
# ---------------------------------------------------------------------------

_p9c0_controller_run_coordinate() {
    local user="$1"; shift
    local unit_uid="$1"; shift
    local wrapper manifest prefix expected_line current_line sha
    wrapper="$(_p9c0_wrapper_path)"
    manifest="$(_p9c0_wrapper_manifest_path)"
    prefix="$(_p9c0_controller_state_prefix)"
    [[ "$user" == "$P9C0_UNIT_USER" && "$unit_uid" == "$P9C0_UNIT_UID" ]] \
        || _p9c0_die "caller identity differs from sealed unit identity" 67
    _p9c0_reject_unknown_run_entries
    _p9c0_enforce_unit_identity "$user" "$P9C0_UNIT_GROUP" \
        "$unit_uid" "$P9C0_UNIT_GID" "$(_p9c0_controller_db_path)" "$P9C0_PROD_DB"
    _p9c0_enforce_root_owned_file "$manifest" "640" "0" "$P9C0_UNIT_GID" \
        || _p9c0_die "manifest metadata drift before Coordinate invocation" 67
    [[ "$(wc -l < "$manifest" | tr -d ' ')" == "1" ]] \
        || _p9c0_die "manifest line count drift before Coordinate invocation" 68
    expected_line="$(cat "$manifest")" || _p9c0_die "manifest read failed" 69
    current_line="$(_p9c0_wrapper_manifest_record "$wrapper")" \
        || _p9c0_die "wrapper record failed" 70
    [[ "$current_line" == "$expected_line" ]] \
        || _p9c0_die "wrapper manifest drift before Coordinate invocation" 71
    sha="$(printf '%s\n' "$expected_line" | sed -n 's/^.*wrapper_sha256=//p')"
    _p9c0_enforce_wrapper_authority "$wrapper" "$prefix" "$P9C0_PROD_WRAPPER" \
        "$P9C0_UNIT_GID" "$sha"
    _p9c0_runuser --user "$user" -- "$wrapper" "$@"
}

# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

_p9c0_primary_run_id_for() {
    local run_id="$1" ledger line parent="" count=0 expected shared_db
    ledger="$(_p9c0_controller_state_prefix)/$run_id/ledger/events.jsonl"
    [[ -f "$ledger" && ! -L "$ledger" ]] || return 1
    while IFS= read -r line; do
        case "$line" in
            "parent-run run_id="*" shared_db="*)
                parent="${line#parent-run run_id=}"
                parent="${parent%% shared_db=*}"
                shared_db="${line#* shared_db=}"
                count=$((count + 1))
                ;;
        esac
    done < "$ledger"
    [[ $count -le 1 ]] || return 1
    if [[ $count -eq 0 ]]; then
        printf '%s\n' "$run_id"
        return 0
    fi
    _p9c0_validate_run_id "$parent" || return 1
    expected="$(_p9c0_recovery_run_id "$parent")" || return 1
    [[ "$run_id" == "$expected" ]] || return 1
    [[ "$shared_db" == "$(_p9c0_controller_state_prefix)/$parent/db/coord.sqlite3" ]] \
        || return 1
    printf '%s\n' "$parent"
}

_p9c0_linked_run_ids() {
    local primary="$1" ledger line linked="" shared_db count=0 expected
    ledger="$(_p9c0_controller_state_prefix)/$primary/ledger/events.jsonl"
    [[ -f "$ledger" && ! -L "$ledger" ]] || return 1
    printf '%s\n' "$primary"
    while IFS= read -r line; do
        case "$line" in
            "recovery-run run_id="*" shared_db="*)
                linked="${line#recovery-run run_id=}"
                linked="${linked%% shared_db=*}"
                shared_db="${line#* shared_db=}"
                count=$((count + 1))
                ;;
        esac
    done < "$ledger"
    [[ $count -le 1 ]] || return 1
    [[ $count -eq 1 ]] || return 0
    expected="$(_p9c0_recovery_run_id "$primary")" || return 1
    [[ "$linked" == "$expected" ]] || return 1
    [[ "$shared_db" == "$(_p9c0_controller_state_prefix)/$primary/db/coord.sqlite3" ]] \
        || return 1
    [[ -f "$(_p9c0_controller_state_prefix)/$linked/ledger/events.jsonl" ]] \
        || return 1
    printf '%s\n' "$linked"
}

_p9c0_failure_stop_run() {
    local run_id="$1" ledger line unit expected agent stopped=" "
    ledger="$(_p9c0_controller_state_prefix)/$run_id/ledger/events.jsonl"
    [[ -f "$ledger" && ! -L "$ledger" ]] || return 1
    while IFS= read -r line; do
        case "$line" in
            unit=*) unit="${line#unit=}" ;;
            "unit "*) unit="${line#unit }" ;;
            *) continue ;;
        esac
        unit="${unit%% *}"
        expected=""
        for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
            [[ "$unit" == "$agent-$run_id.service" ]] && expected="$unit"
        done
        [[ -n "$expected" ]] || continue
        case "$stopped" in *" $expected "*) continue ;; esac
        _p9c0_helper_exact_stop "$expected" "$run_id" || true
        stopped="$stopped$expected "
    done < "$ledger"
}

_p9c0_failure_trap() {
    local ledger current_run primary_run run_id linked_runs authority_error=0 seen=" "
    current_run="$P9C0_RUN_ID"
    ledger="$(_p9c0_ledger_path)"
    [[ -f "$ledger" ]] || return 0
    primary_run="$(_p9c0_primary_run_id_for "$current_run")" || return 1
    if ! linked_runs="$(_p9c0_linked_run_ids "$primary_run")"; then
        authority_error=1
        linked_runs="$primary_run
$current_run"
    fi
    while IFS= read -r run_id; do
        [[ -n "$run_id" ]] || continue
        case "$seen" in *" $run_id "*) continue ;; esac
        seen="$seen$run_id "
        P9C0_RUN_ID="$run_id"
        if [[ -f "$(_p9c0_intake_record_path)" ]]; then
            [[ "$(cat "$(_p9c0_intake_record_path)")" == "intake=$P9C0_INTAKE_FROZEN" ]] \
                || _p9c0_record_intake "$P9C0_INTAKE_FROZEN"
        fi
        _p9c0_failure_stop_run "$run_id" || true
    done <<< "$linked_runs"
    P9C0_RUN_ID="$current_run"

    if [[ ! -e "$(_p9c0_failure_record_path)" && ! -L "$(_p9c0_failure_record_path)" ]]; then
        (umask 077; set -o noclobber; printf 'failure=preserved\n' > "$(_p9c0_failure_record_path)") \
            || true
        [[ -f "$(_p9c0_failure_record_path)" ]] && {
            _p9c0_chown 0 0 "$(_p9c0_failure_record_path)"
            _p9c0_chmod 0600 "$(_p9c0_failure_record_path)"
            _p9c0_record_evidence failed
        }
    fi
    if [[ -f "$(_p9c0_phase_record_path)" ]]; then
        local recorded_phase
        recorded_phase="$(sed -n 's/^phase=//p' "$(_p9c0_phase_record_path)")"
        # Cleanup has its own durable, idempotent phase record.  Preserve the
        # verification handoff phase so an interrupted cleanup can resume.
        [[ "$recorded_phase" == "$P9C0_PHASE_CLEANUP_READY" ]] \
            || _p9c0_transition_phase "$P9C0_PHASE_FAILED"
    fi
    return "$authority_error"
}

_p9c0_on_exit() {
    local status="$1"
    [[ "$status" == "0" ]] || _p9c0_failure_trap
    return "$status"
}

# ---------------------------------------------------------------------------
# Prepare subcommand
# ---------------------------------------------------------------------------

_p9c0_controller_prepare_locked() {
    local prefix="$1" run_root="$2" db_path="$3"
    _p9c0_transition_phase "$P9C0_PHASE_BOOT"
    _p9c0_ledger_append "controller boot run=$P9C0_RUN_ID agent=$P9C0_AGENT_ID"
    _p9c0_record_intake "$P9C0_INTAKE_OPEN"

    _p9c0_transition_phase "$P9C0_PHASE_INTAKE"
    _p9c0_ledger_append "intake open run=$P9C0_RUN_ID"

    _p9c0_transition_phase "$P9C0_PHASE_AUTHORIZE"
    _p9c0_ledger_append "authorize unit_user=$P9C0_UNIT_USER unit_group=$P9C0_UNIT_GROUP"

    _p9c0_transition_phase "$P9C0_PHASE_RENDER"
    local wrapper_raw sha
    wrapper_raw="$(_p9c0_wrapper_path)"
    _p9c0_render_wrapper "$wrapper_raw" "$run_root" \
        "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" "$db_path"
    sha="$(_p9c0_sha256_file "$wrapper_raw")" \
        || _p9c0_die "wrapper SHA capture failed: $wrapper_raw" 87
    _p9c0_enforce_wrapper_authority "$wrapper_raw" "$prefix" \
        "$P9C0_PROD_WRAPPER" "$P9C0_UNIT_GID" "$sha"
    _p9c0_seal_wrapper_manifest "$wrapper_raw"
    _p9c0_reject_unknown_run_entries
    _p9c0_enforce_unit_identity "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" \
        "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" "$db_path" "$P9C0_PROD_DB"
    _p9c0_ledger_append "wrapper render path=$wrapper_raw sha256=$sha"

    # The lifecycle helper consumes the controller-created directory layout and
    # sealed wrapper manifest directly.  Keeping this in prepare makes a layout
    # mismatch fail before any workspace, catalog, job, or unit mutation.
    _p9c0_unit_helper render \
        --state-root "$prefix" \
        --run-id "$P9C0_RUN_ID" \
        --fixture-bin "$P9C0_FIXTURE_BIN" \
        --wrapper "$wrapper_raw" \
        --coord-db "$db_path" \
        --work-dir "$run_root/work" \
        --python "$P9C0_FIXTURE_PYTHON" \
        --repo-root "$P9C0_DEPLOYED_REPO_ROOT" \
        --user "$P9C0_UNIT_USER" \
        --group "$P9C0_UNIT_GROUP" \
        --runtime-parent "$run_root" \
        || _p9c0_die "fixture helper render failed" 88
    [[ -f "$run_root/agents.rendered.toml" && -f "$run_root/values.rendered" \
        && -f "$run_root/systemd.verify.service" ]] \
        || _p9c0_die "fixture helper render omitted required assets" 88
    _p9c0_ledger_append "fixture render run=$P9C0_RUN_ID"

    _p9c0_transition_phase "$P9C0_PHASE_READY"
    _p9c0_ledger_append "foundation ready run=$P9C0_RUN_ID"
    _p9c0_record_evidence foundation-ready
}

_p9c0_controller_prepare() {
    P9C0_RUN_ID="$P9C0_ARG_RUN_ID"
    P9C0_UNIT_USER="$P9C0_ARG_UNIT_USER"
    P9C0_UNIT_GROUP="$P9C0_ARG_UNIT_GROUP"
    P9C0_AGENT_ID="$P9C0_ARG_AGENT_ID"
    P9C0_COORD_DB=""

    _p9c0_validate_run_id "$P9C0_RUN_ID" || _p9c0_die "invalid run id: $P9C0_RUN_ID" 70
    _p9c0_validate_agent_id "$P9C0_AGENT_ID" || _p9c0_die "invalid agent id: $P9C0_AGENT_ID" 71
    [[ "$P9C0_UNIT_USER" != "root" ]] || _p9c0_die "unit user cannot be root" 72
    [[ "$P9C0_UNIT_GROUP" != "root" ]] || _p9c0_die "unit group cannot be root" 73

    local euid
    euid="$(_p9c0_euid)"
    [[ "$euid" == "0" ]] || _p9c0_die "controller must run as root" 74

    P9C0_UNIT_UID="$(_p9c0_identity_lookup_user "$P9C0_UNIT_USER")" \
        || _p9c0_die "unit user missing: $P9C0_UNIT_USER" 75
    P9C0_UNIT_GID="$(_p9c0_identity_lookup_group "$P9C0_UNIT_GROUP")" \
        || _p9c0_die "unit group missing: $P9C0_UNIT_GROUP" 76
    [[ "$P9C0_UNIT_UID" =~ ^[0-9]+$ ]] || _p9c0_die "unit uid non-numeric" 77
    [[ "$P9C0_UNIT_GID" =~ ^[0-9]+$ ]] || _p9c0_die "unit gid non-numeric" 78
    [[ "$P9C0_UNIT_UID" != "0" ]] || _p9c0_die "unit uid=0" 79
    [[ "$P9C0_UNIT_GID" != "0" ]] || _p9c0_die "unit gid=0" 80

    _p9c0_collect_unset_environment_names >/dev/null

    local prefix run_root
    prefix="$(_p9c0_controller_state_prefix)"
    _p9c0_is_absolute_path "$prefix" || _p9c0_die "state prefix not absolute: $prefix" 81
    _p9c0_assert_state_prefix_authority "$prefix" \
        || _p9c0_die "state prefix is not the fixed production namespace: $prefix" 82
    run_root="$(_p9c0_per_run_root)"
    _p9c0_is_under_root "$run_root" "$prefix" \
        || _p9c0_die "per-run root escapes state prefix: $run_root" 83
    [[ ! -e "$run_root" && ! -L "$run_root" ]] \
        || _p9c0_die "run id already has state; refusing repeat prepare: $P9C0_RUN_ID" 84

    local db_path
    db_path="$(_p9c0_isolation_db_path)"

    _p9c0_enforce_unit_identity "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" \
        "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" "$db_path" "$P9C0_PROD_DB"

    _p9c0_layout_prefix "$prefix"
    _p9c0_assert_state_prefix_resolved "$prefix" \
        || _p9c0_die "state prefix resolved alias rejected: $prefix" 86
    _p9c0_layout_per_run
    _p9c0_with_run_lock _p9c0_controller_prepare_locked "$prefix" "$run_root" "$db_path"
}

# ---------------------------------------------------------------------------
# Recovery namespace
# ---------------------------------------------------------------------------

_p9c0_recovery_run_id() {
    local primary="$1"
    _p9c0_validate_run_id "$primary" || return 1
    [[ ${#primary} -le 61 ]] || return 1
    printf '%s-r2\n' "$primary"
}

_p9c0_prepare_recovery_namespace() {
    local primary_run="$1" recovery_run prefix primary_root recovery_root primary_db
    local saved_run saved_db saved_agent
    recovery_run="$(_p9c0_recovery_run_id "$primary_run")" \
        || _p9c0_die "primary run id cannot derive bounded recovery namespace" 89
    prefix="$(_p9c0_controller_state_prefix)"
    primary_root="$prefix/$primary_run"
    recovery_root="$prefix/$recovery_run"
    primary_db="$primary_root/db/coord.sqlite3"

    [[ "$P9C0_RUN_ID" == "$primary_run" ]] \
        || _p9c0_die "recovery namespace caller is not on primary run" 89
    [[ "$(cat "$primary_root/control/intake" 2>/dev/null)" == \
       "intake=$P9C0_INTAKE_FROZEN" ]] \
        || _p9c0_die "recovery namespace requires frozen primary intake" 89
    [[ -f "$primary_db" && ! -L "$primary_db" ]] \
        || _p9c0_die "primary isolated DB missing before recovery namespace" 89
    [[ ! -e "$recovery_root" && ! -L "$recovery_root" ]] \
        || _p9c0_die "recovery namespace already exists" 89

    saved_run="$P9C0_RUN_ID"
    saved_db="${P9C0_COORD_DB:-}"
    saved_agent="$P9C0_AGENT_ID"
    P9C0_RUN_ID="$recovery_run"
    P9C0_COORD_DB="$primary_db"
    P9C0_AGENT_ID="recovery-operator"

    _p9c0_layout_per_run
    _p9c0_ledger_append "parent-run run_id=$primary_run shared_db=$primary_db"
    P9C0_RUN_ID="$saved_run"
    P9C0_COORD_DB="$saved_db"
    P9C0_AGENT_ID="$saved_agent"
    _p9c0_ledger_append \
        "recovery-run run_id=$recovery_run shared_db=$primary_db"
    P9C0_RUN_ID="$recovery_run"
    P9C0_COORD_DB="$primary_db"
    P9C0_AGENT_ID="recovery-operator"
    _p9c0_with_run_lock _p9c0_controller_prepare_locked \
        "$prefix" "$recovery_root" "$primary_db"

    P9C0_RUN_ID="$saved_run"
    P9C0_COORD_DB="$saved_db"
    P9C0_AGENT_ID="$saved_agent"
}

# ---------------------------------------------------------------------------
# Full isolated verification: production baseline and catalog preparation
# ---------------------------------------------------------------------------

_p9c0_real_hostname() { hostname; }
_p9c0_hostname() { _p9c0_real_hostname; }

_p9c0_expected_catalog_sha() {
    case "$1" in
        executor-v1-disabled) echo 9560942a1e8dbd921135fb7c8ae3697c408c718e0b3bcd9fca234976e4f9c960 ;;
        capacity-v1) echo b3de918630fc7f0cc0126b0f638c8733c2587190d2a0946adb68ffb15bb10a40 ;;
        executor-v2-enabled) echo 32f1d04aaafc90e21443d36ad7ae43782f47fc282d4e21dc0778f45f495d006c ;;
        executor-v3-disabled) echo 220cf01eedbf753c98c51cf3451a3991340126d2dfe67929fbb6cd8319113105 ;;
        capacity-v2-empty) echo f33065c74eb4a0d825dde345f04e0b207658b209b002db05764613ef47f20155 ;;
        executor-v4-empty) echo 7dc13eb10aa0673c90af0d7140b01d89d4703fc7f6ed90af7da775fd1979d3eb ;;
        *) return 1 ;;
    esac
}

_p9c0_authorize_catalog() {
    local stage="$1" path="$2" expected_path expected_sha sha stat_line nlink uid gid mode record count
    case "$stage" in
        executor-v1-disabled) expected_path="$P9C0_EXECUTOR_V1" ;;
        capacity-v1) expected_path="$P9C0_CAPACITY_V1" ;;
        executor-v2-enabled) expected_path="$P9C0_EXECUTOR_V2" ;;
        executor-v3-disabled) expected_path="$P9C0_EXECUTOR_V3" ;;
        capacity-v2-empty) expected_path="$P9C0_CAPACITY_V2" ;;
        executor-v4-empty) expected_path="$P9C0_EXECUTOR_V4" ;;
        *) _p9c0_die "unknown catalog authority stage: $stage" 90 ;;
    esac
    [[ "$path" == "$expected_path" && "$path" == /* && -f "$path" && ! -L "$path" ]] \
        || _p9c0_die "catalog authority path/type rejected: $stage" 90
    [[ "$(_p9c0_realpath "$path")" == "$path" ]] \
        || _p9c0_die "catalog authority alias rejected: $stage" 90
    stat_line="$(_p9c0_stat_file "$path")" || _p9c0_die "catalog stat failed: $stage" 90
    IFS=: read -r _ _ _ nlink uid gid mode <<< "$stat_line"
    [[ "$nlink" == "1" && "$uid" =~ ^[0-9]+$ && "$gid" =~ ^[0-9]+$ ]] \
        || _p9c0_die "catalog link/owner metadata rejected: $stage" 90
    [[ "$uid" != "$P9C0_UNIT_UID" ]] \
        || _p9c0_die "catalog is owned by fixture unit user: $stage" 90
    [[ "$mode" == "644" || "$mode" == "600" ]] \
        || _p9c0_die "catalog mode rejected: $stage" 90
    sha="$(_p9c0_sha256_file "$path")" || _p9c0_die "catalog SHA failed: $stage" 90
    expected_sha="$(_p9c0_expected_catalog_sha "$stage")" \
        || _p9c0_die "catalog expected SHA unavailable: $stage" 90
    [[ "$sha" == "$expected_sha" ]] \
        || _p9c0_die "catalog SHA differs from reviewed Package 2 asset: $stage" 90
    record="catalog-authority stage=$stage path=$path stat=$stat_line sha256=$sha"
    count="$(grep -Fxc -- "$record" "$(_p9c0_ledger_path)" 2>/dev/null || true)"
    [[ "$count" == "0" || "$count" == "1" ]] \
        || _p9c0_die "catalog authority ledger duplicated: $stage" 90
    [[ "$count" == "1" ]] || _p9c0_ledger_append "$record"
}

_p9c0_real_production_snapshot() {
    local mode="$1" output="$2"
    python3 - "$mode" "$output" "$P9C0_PROD_DB" "$P9C0_RUN_ID" <<'PY'
import hashlib, json, os, pathlib, sqlite3, subprocess, sys

mode, output, db_raw, run_id = sys.argv[1:]
output = pathlib.Path(output)
services = (
    "coordinate.service",
    "multinexus-discord-bridge.service",
    "kook-nexus-hermes.service",
)
fixture_ids = ("p9-3c-fixture-e1", "p9-3c-fixture-e2")

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def show(unit, props):
    cp = subprocess.run(
        ["systemctl", "show", *sum((["-p", p] for p in props), []), unit],
        text=True, capture_output=True, timeout=10,
    )
    if cp.returncode:
        raise SystemExit(f"systemctl show failed for {unit}: {cp.stderr[:300]}")
    values = {}
    for line in cp.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in values:
                raise SystemExit(f"duplicate systemctl property {key} for {unit}")
            values[key] = value
    if set(values) != set(props):
        raise SystemExit(f"missing systemctl property for {unit}")
    return values

service_state = {}
for unit in services:
    row = show(unit, ("Id", "LoadState", "ActiveState", "SubState", "MainPID", "NRestarts", "FragmentPath"))
    if row["Id"] != unit or row["LoadState"] != "loaded" or row["ActiveState"] != "active" or row["SubState"] != "running":
        raise SystemExit(f"canonical service is not exact active/running: {unit}")
    fragment = row.pop("FragmentPath")
    if not fragment or not os.path.isfile(fragment) or os.path.islink(fragment):
        raise SystemExit(f"canonical service fragment unsafe: {unit}")
    row["fragment_path"] = fragment
    row["fragment_sha256"] = sha(fragment)
    service_state[unit] = row

fixture_units = {}
for agent in fixture_ids:
    unit = f"{agent}-{run_id}.service"
    fixture_units[unit] = show(unit, ("Id", "LoadState", "ActiveState"))
    if fixture_units[unit]["LoadState"] != "not-found" or fixture_units[unit]["ActiveState"] != "inactive":
        raise SystemExit(f"fixture unit existed at production baseline: {unit}")

db = pathlib.Path(db_raw).resolve()
conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
    raise SystemExit("production DB integrity_check failed")
if conn.execute("PRAGMA user_version").fetchone()[0] != 13:
    raise SystemExit("production DB schema is not 13")
if conn.execute("SELECT COUNT(*) FROM pragma_foreign_key_check").fetchone()[0] != 0:
    raise SystemExit("production DB foreign_key_check failed")
ph = ",".join("?" for _ in fixture_ids)
db_state = {
    "pending_running": conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0],
    "active_leases": conn.execute("SELECT COUNT(*) FROM execution_attempt_leases WHERE status='active'").fetchone()[0],
    "fixture_agents": conn.execute(f"SELECT COUNT(*) FROM agents WHERE id IN ({ph})", fixture_ids).fetchone()[0],
    "fixture_runners": conn.execute(f"SELECT COUNT(*) FROM runner_profiles WHERE id IN ({ph})", fixture_ids).fetchone()[0],
    "fixture_jobs": conn.execute(f"SELECT COUNT(*) FROM jobs WHERE assigned_agent IN ({ph})", fixture_ids).fetchone()[0],
    "fixture_leases": conn.execute(f"SELECT COUNT(*) FROM execution_attempt_leases WHERE agent_id IN ({ph})", fixture_ids).fetchone()[0],
    "executor_sources": [list(r) for r in conn.execute("SELECT source_id,source_version,catalog_hash FROM executor_catalog_sources ORDER BY source_id")],
    "capacity_sources": [list(r) for r in conn.execute("SELECT source_id,source_version,catalog_hash FROM executor_capacity_sources ORDER BY source_id")],
}
if any(db_state[k] for k in ("fixture_agents", "fixture_runners", "fixture_jobs", "fixture_leases")):
    raise SystemExit("production DB contains fixture identity")

config_paths = (
    "/opt/multinexus/config/agent-registry.toml",
    "/opt/multinexus/agents.toml",
    "/opt/multinexus/VERSION_DEPLOYED",
)
configs = {}
for raw in config_paths:
    if not os.path.isfile(raw) or os.path.islink(raw):
        raise SystemExit(f"canonical config missing/unsafe: {raw}")
    configs[raw] = sha(raw)
payload = {"services": service_state, "fixture_units": fixture_units, "db": db_state, "configs": configs}

if mode == "capture":
    if output.exists():
        previous = json.loads(output.read_text(encoding="utf-8"))
        if previous != payload:
            raise SystemExit("pre-existing baseline differs from current production state")
    else:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, sort_keys=True, separators=(",", ":"))
            f.write("\n")
elif mode == "compare":
    if not output.is_file() or json.loads(output.read_text(encoding="utf-8")) != payload:
        raise SystemExit("production state drifted from captured baseline")
else:
    raise SystemExit("unknown snapshot mode")
PY
}

_p9c0_production_snapshot() { _p9c0_real_production_snapshot "$@"; }

_p9c0_verify_capture_baseline() {
    local output
    output="$(_p9c0_per_run_root)/evidence/production-baseline.json"
    _p9c0_production_snapshot capture "$output" \
        || _p9c0_die "production baseline capture failed" 91
    _p9c0_chown 0 0 "$output" || _p9c0_die "baseline chown failed" 91
    _p9c0_chmod 0600 "$output" || _p9c0_die "baseline chmod failed" 91
    _p9c0_ledger_append "production-baseline path=$output sha256=$(_p9c0_sha256_file "$output")"
}

_p9c0_real_verify_catalog_state() {
    python3 - "$(_p9c0_controller_db_path)" "$P9C0_HOST_ID" <<'PY'
import pathlib, sqlite3, sys
db, host = sys.argv[1:]
conn = sqlite3.connect(pathlib.Path(db).resolve().as_uri() + "?mode=ro", uri=True)
ids = ("p9-3c-fixture-e1", "p9-3c-fixture-e2")
agents = conn.execute("SELECT id,host_id,client_type FROM agents ORDER BY id").fetchall()
if agents != [(ids[0],host,"agentd"),(ids[1],host,"agentd")]: raise SystemExit(f"agents mismatch: {agents}")
runners = conn.execute("SELECT id,runner_type FROM runner_profiles ORDER BY id").fetchall()
if runners != [(ids[0],"agentd"),(ids[1],"agentd")]: raise SystemExit(f"runners mismatch: {runners}")
sources = conn.execute("SELECT source_id,source_version FROM executor_catalog_sources").fetchall()
if sources != [("p9-3c0-fixture-executors",2)]: raise SystemExit(f"executor source mismatch: {sources}")
defs = conn.execute("SELECT id,provider,adapter FROM executor_definitions").fetchall()
if defs != [("p9-3c-local-fixture","local-fixture","claude")]: raise SystemExit(f"definitions mismatch: {defs}")
bindings = conn.execute("SELECT agent_id,runner_profile_id,enabled FROM executor_instance_bindings ORDER BY agent_id").fetchall()
if bindings != [(ids[0],ids[0],1),(ids[1],ids[1],1)]: raise SystemExit(f"bindings mismatch: {bindings}")
cap_sources = conn.execute("SELECT source_id,source_version FROM executor_capacity_sources").fetchall()
if cap_sources != [("p9-3c0-fixture-capacity",1)]: raise SystemExit(f"capacity source mismatch: {cap_sources}")
policies = conn.execute("SELECT agent_id,max_concurrent_jobs FROM executor_capacity_policies ORDER BY agent_id").fetchall()
if policies != [(ids[0],1),(ids[1],1)]: raise SystemExit(f"policies mismatch: {policies}")
if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] != 0: raise SystemExit("isolated jobs not empty")
if conn.execute("SELECT COUNT(*) FROM execution_attempt_leases").fetchone()[0] != 0: raise SystemExit("isolated leases not empty")
PY
}

_p9c0_verify_catalog_state() { _p9c0_real_verify_catalog_state; }

_p9c0_verify_prepare_catalog() {
    local run_root agent
    run_root="$(_p9c0_per_run_root)"
    P9C0_HOST_ID="$(_p9c0_hostname)" || _p9c0_die "hostname lookup failed" 92
    [[ "$P9C0_HOST_ID" =~ ^[A-Za-z0-9._-]{1,64}$ ]] \
        || _p9c0_die "hostname is not a bounded Coordinate host id" 92
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" --version >/dev/null \
        || _p9c0_die "isolated DB initialization failed" 92
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        workspace add "$P9C0_WORKSPACE_ID" --path "$run_root/work" \
        --harness-root "$run_root/harness" \
        || _p9c0_die "isolated workspace add failed" 92
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        workspace host-profile set "$P9C0_WORKSPACE_ID" \
        --host-id "$P9C0_HOST_ID" --workspace-path "$run_root/work" \
        --harness-root "$run_root/harness" \
        --coordinator-cli-path "$(_p9c0_wrapper_path)" \
        --coordinator-db-path "$(_p9c0_controller_db_path)" \
        || _p9c0_die "isolated host profile failed" 92
    for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
            runtime agent register --agent-id "$agent" --host-id "$P9C0_HOST_ID" \
            --client-type agentd \
            || _p9c0_die "isolated agent registration failed: $agent" 92
    done
    _p9c0_authorize_catalog executor-v1-disabled "$P9C0_EXECUTOR_V1"
    _p9c0_authorize_catalog capacity-v1 "$P9C0_CAPACITY_V1"
    _p9c0_authorize_catalog executor-v2-enabled "$P9C0_EXECUTOR_V2"
    _p9c0_authorize_catalog executor-v3-disabled "$P9C0_EXECUTOR_V3"
    _p9c0_authorize_catalog capacity-v2-empty "$P9C0_CAPACITY_V2"
    _p9c0_authorize_catalog executor-v4-empty "$P9C0_EXECUTOR_V4"
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        runtime executor sync --source "$P9C0_EXECUTOR_V1" \
        || _p9c0_die "executor v1 disabled sync failed" 92
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        runtime capacity sync --source "$P9C0_CAPACITY_V1" \
        || _p9c0_die "capacity v1 sync failed" 92
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        runtime executor sync --source "$P9C0_EXECUTOR_V2" \
        || _p9c0_die "executor v2 enabled sync failed" 92
    _p9c0_verify_catalog_state || _p9c0_die "isolated catalog postcondition failed" 92
    _p9c0_ledger_append "catalog-ready host_id=$P9C0_HOST_ID"
}

_p9c0_verify_value_once() {
    local file="$1" key="$2" count
    count="$(grep -c "^${key}=" "$file" 2>/dev/null || true)"
    [[ "$count" == "1" ]] || return 1
    sed -n "s/^${key}=//p" "$file"
}

_p9c0_verify_load_sealed_identity() {
    local values sealed_user sealed_group sealed_uid sealed_gid sealed_db
    values="$(_p9c0_per_run_root)/values.rendered"
    _p9c0_enforce_root_owned_file "$values" "600" "0" "0" \
        || _p9c0_die "values.rendered authority rejected" 93
    sealed_user="$(_p9c0_verify_value_once "$values" unit_user)" \
        || _p9c0_die "sealed unit_user missing or duplicate" 93
    sealed_group="$(_p9c0_verify_value_once "$values" unit_group)" \
        || _p9c0_die "sealed unit_group missing or duplicate" 93
    sealed_uid="$(_p9c0_verify_value_once "$values" unit_uid)" \
        || _p9c0_die "sealed unit_uid missing or duplicate" 93
    sealed_gid="$(_p9c0_verify_value_once "$values" unit_gid)" \
        || _p9c0_die "sealed unit_gid missing or duplicate" 93
    sealed_db="$(_p9c0_verify_value_once "$values" coord_db)" \
        || _p9c0_die "sealed coord_db missing or duplicate" 93
    [[ "$sealed_user" == "$P9C0_UNIT_USER" && "$sealed_group" == "$P9C0_UNIT_GROUP" ]] \
        || _p9c0_die "caller unit identity differs from sealed identity" 93
    [[ "$sealed_uid" =~ ^[0-9]+$ && "$sealed_gid" =~ ^[0-9]+$ ]] \
        || _p9c0_die "sealed unit identity is non-numeric" 93
    P9C0_UNIT_UID="$sealed_uid"
    P9C0_UNIT_GID="$sealed_gid"
    P9C0_COORD_DB="$sealed_db"
    [[ "$P9C0_COORD_DB" == "$(_p9c0_isolation_db_path)" ]] \
        || _p9c0_die "primary namespace does not seal its own isolated DB" 93
    _p9c0_enforce_unit_identity "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" \
        "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" "$P9C0_COORD_DB" "$P9C0_PROD_DB"
}

_p9c0_verify_current_phase() {
    local path line phase
    path="$(_p9c0_phase_record_path)"
    _p9c0_enforce_root_owned_file "$path" "600" "0" "0" \
        || _p9c0_die "verification phase authority rejected" 94
    [[ "$(wc -l < "$path" | tr -d ' ')" == "1" ]] \
        || _p9c0_die "verification phase must be one line" 94
    line="$(cat "$path")" || _p9c0_die "verification phase read failed" 94
    case "$line" in phase=*) phase="${line#phase=}" ;; *)
        _p9c0_die "verification phase record malformed" 94 ;;
    esac
    _p9c0_phase_rank "$phase" >/dev/null \
        || _p9c0_die "verification phase unknown: $phase" 94
    printf '%s\n' "$phase"
}

_p9c0_real_sleep() { sleep "$1"; }
_p9c0_sleep() { _p9c0_real_sleep "$@"; }
_p9c0_real_unit_journal() { journalctl -u "$1" --no-pager -o cat; }
_p9c0_unit_journal() { _p9c0_real_unit_journal "$@"; }

# ``journalctl -o cat`` returns the Python logging formatter prefix as part of
# MESSAGE (timestamp, logger name, and level).  Normalize only an exact marker
# at the end of a journal line so scenario code can count provider boundaries
# without depending on the active logging formatter.
_p9c0_claude_boundary_lines() {
    sed -nE 's/^.*(claude_child_boundary monotonic_ns=[0-9]+ pid=[0-9]+)$/\1/p'
}

_p9c0_unit_start() {
    local agent="$1" mode="$2"; shift 2
    _p9c0_unit_helper start \
        --state-root "$(_p9c0_controller_state_prefix)" \
        --run-id "$P9C0_RUN_ID" \
        --agent-id "$agent" \
        --mode "$mode" \
        --user "$P9C0_UNIT_USER" \
        --group "$P9C0_UNIT_GROUP" "$@"
}

_p9c0_unit_stop() {
    local agent="$1"; shift
    _p9c0_unit_helper stop \
        --state-root "$(_p9c0_controller_state_prefix)" \
        --run-id "$P9C0_RUN_ID" \
        --agent-id "$agent" "$@"
}

_p9c0_submit_request() {
    local agent="$1" mode="$2" descendant="$3" suffix="$4"
    local prompt origin reply key worktree
    [[ "$(cat "$(_p9c0_intake_record_path)" 2>/dev/null)" == \
       "intake=$P9C0_INTAKE_OPEN" ]] \
        || _p9c0_die "fixture intake is frozen; submit refused before Coordinate" 97
    prompt="{\"contract_version\":1,\"mode\":\"$mode\",\"quiet_seconds\":75,\"spawn_descendant\":$descendant}"
    origin="{\"platform\":\"local-fixture\",\"destination\":\"$agent\",\"session_scope_id\":\"$P9C0_RUN_ID:$agent:$suffix\",\"message_id\":\"$P9C0_RUN_ID-$agent-$suffix\"}"
    reply="{\"platform\":\"local-fixture\",\"destination\":\"$agent\"}"
    key="p9-3c0:$P9C0_RUN_ID:$agent:$suffix"
    worktree="$(_p9c0_worktree_path_for_agent "$agent")" \
        || _p9c0_die "fixture worktree agent is not allowlisted: $agent" 97
    _p9c0_enforce_root_owned_dir "$worktree" "700" \
        "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" \
        || _p9c0_die "fixture worktree authority rejected: $worktree" 97
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        runtime request submit "$P9C0_WORKSPACE_ID" \
        --target-agent "$agent" --worktree-path "$worktree" --prompt "$prompt" \
        --origin-json "$origin" --reply-json "$reply" \
        --idempotency-key "$key" --actor p9-3c0-local-verify
}

_p9c0_real_base_monitor() {
    local output="$1"
    python3 - "$(_p9c0_controller_db_path)" "$P9C0_RUN_ID" "$output" <<'PY'
import datetime as dt, json, os, pathlib, sqlite3, sys, time
db_raw, run_id, output = sys.argv[1:]
ids = ("p9-3c-fixture-e1", "p9-3c-fixture-e2")
expected_prompt = '{"contract_version":1,"mode":"complete","quiet_seconds":75,"spawn_descendant":false}'
db_path = pathlib.Path(db_raw).resolve()
expected_worktrees = {agent: str(db_path.parent.parent / "work" / agent) for agent in ids}
conn = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
seen_running = {a: False for a in ids}
deadlines = {a: [] for a in ids}
initial = {}
started = time.monotonic()
rows_by_agent = {}
resource_keys = {}

def stamp(raw):
    value = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None: raise SystemExit("lease timestamp lacks timezone")
    return value

while time.monotonic() - started < 105:
    rows_by_agent = {}
    for agent in ids:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE workspace_id=? AND assigned_agent=? ORDER BY created_at",
            ("p9-3c0-sidecar", agent),
        ).fetchall()
        if len(rows) != 1:
            continue
        job = rows[0]
        payload = json.loads(job["payload_json"])
        if payload.get("prompt") != expected_prompt:
            raise SystemExit(f"base prompt mismatch for {agent}")
        expected_worktree = expected_worktrees[agent]
        context = payload.get("execution_context")
        if job["worktree_path"] != expected_worktree or not isinstance(context, dict) or context.get("worktree_path") != expected_worktree:
            raise SystemExit(f"base worktree authority mismatch for {agent}")
        origin, reply = payload.get("origin", {}), payload.get("reply", {})
        if origin.get("platform") != "local-fixture" or origin.get("destination") != agent or reply != {"platform":"local-fixture","destination":agent}:
            raise SystemExit(f"base envelope routing mismatch for {agent}")
        rows_by_agent[agent] = job
        if job["status"] == "running": seen_running[agent] = True
        leases = conn.execute("SELECT * FROM execution_attempt_leases WHERE job_id=? ORDER BY attempt_token", (job["id"],)).fetchall()
        if leases:
            if len(leases) != 1: raise SystemExit(f"base lease count mismatch for {agent}")
            lease = leases[0]
            if lease["attempt_token"] != 1 or lease["agent_id"] != agent or lease["runner_profile_id"] != agent or lease["host_id"] == "":
                raise SystemExit(f"base lease identity mismatch for {agent}")
            if lease["normalized_path"] != expected_worktree:
                raise SystemExit(f"base lease worktree mismatch for {agent}")
            resource_keys[agent] = lease["resource_key"]
            expiry = lease["expires_at"]
            if agent not in initial:
                acquired, first = stamp(lease["acquired_at"]), stamp(expiry)
                if (first-acquired).total_seconds() != 120:
                    raise SystemExit(f"base initial TTL mismatch for {agent}")
                if dt.datetime.now(dt.timezone.utc) >= acquired + dt.timedelta(seconds=30):
                    raise SystemExit(f"base initial lease first observed too late for {agent}")
                initial[agent] = dict(lease)
            if not deadlines[agent] or deadlines[agent][-1] != expiry:
                if deadlines[agent] and stamp(expiry) <= stamp(deadlines[agent][-1]):
                    raise SystemExit(f"base renewal deadline did not increase for {agent}")
                deadlines[agent].append(expiry)
    if time.monotonic() - started > 5 and not all(seen_running.values()):
        raise SystemExit("base job did not reach running within five seconds")
    if len(rows_by_agent) == 2 and all(row["status"] == "done" for row in rows_by_agent.values()):
        break
    time.sleep(0.25)
else:
    raise SystemExit("base jobs did not complete in bounded window")

if len(resource_keys) != 2 or len(set(resource_keys.values())) != 2:
    raise SystemExit("base worktree resource keys are not distinct")
evidence=[]
for agent in ids:
    job=rows_by_agent[agent]
    if not seen_running[agent] or len(deadlines[agent]) < 3:
        raise SystemExit(f"base renewal observation count too small for {agent}")
    result=json.loads(job["result_json"] or "null")
    if not isinstance(result,dict) or result.get("response_text") != "fixture complete" or result.get("session_id") != "":
        raise SystemExit(f"base result mismatch for {agent}")
    duration=result.get("duration_ms")
    if not isinstance(duration,int) or not 75000 <= duration < 90000:
        raise SystemExit(f"base quiet duration mismatch for {agent}: {duration}")
    if result.get("progress"):
        raise SystemExit(f"base fixture emitted progress for {agent}")
    lease=conn.execute("SELECT * FROM execution_attempt_leases WHERE job_id=?",(job["id"],)).fetchone()
    if lease["status"] != "released": raise SystemExit(f"base lease not released for {agent}")
    evidence.append({"agent_id":agent,"job_id":job["id"],"lease_id":lease["lease_id"],"attempt_token":1,"deadlines":deadlines[agent],"duration_ms":duration,"worktree_path":expected_worktrees[agent],"resource_key":resource_keys[agent]})
fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w",encoding="utf-8") as f:
    for row in evidence: f.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
for row in evidence:
    print("base-job agent={agent_id} job_id={job_id} lease_id={lease_id} attempt=1 renewals={renewals}".format(renewals=len(row["deadlines"])-1,**row))
PY
}

_p9c0_base_monitor() { _p9c0_real_base_monitor "$@"; }

_p9c0_real_verify_base_scenario() {
    local agent unit output summaries lease renewals
    for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        _p9c0_unit_start "$agent" complete \
            || _p9c0_die "base fixture unit start failed: $agent" 98
    done
    for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        _p9c0_submit_request "$agent" complete false complete >/dev/null \
            || _p9c0_die "base request submit failed: $agent" 98
    done
    output="$(_p9c0_per_run_root)/evidence/base-jobs.jsonl"
    summaries="$(_p9c0_base_monitor "$output")" \
        || _p9c0_die "base job/lease monitor failed" 98
    _p9c0_chown 0 0 "$output" || _p9c0_die "base evidence chown failed" 98
    _p9c0_chmod 0600 "$output" || _p9c0_die "base evidence chmod failed" 98
    while IFS= read -r summary; do
        [[ "$summary" =~ ^base-job\ agent=([^\ ]+)\ job_id=([^\ ]+)\ lease_id=([^\ ]+)\ attempt=1\ renewals=([0-9]+)$ ]] \
            || _p9c0_die "base monitor summary malformed" 98
        agent="${BASH_REMATCH[1]}"; lease="${BASH_REMATCH[3]}"; renewals="${BASH_REMATCH[4]}"
        [[ "$renewals" -ge 2 ]] || _p9c0_die "base renewal count too small: $agent" 98
        unit="$agent-$P9C0_RUN_ID.service"
        [[ "$(_p9c0_unit_journal "$unit" | grep -F -c "Lease $lease renewed; new deadline" || true)" -ge 2 ]] \
            || _p9c0_die "unit journal lacks two accepted renewals: $unit" 98
        _p9c0_ledger_append "$summary"
    done <<< "$summaries"
    _p9c0_ledger_append "base-complete evidence=$output"
}

_p9c0_verify_base_scenario() { _p9c0_real_verify_base_scenario; }
_p9c0_real_hold_monitor() {
    python3 - "$(_p9c0_controller_db_path)" <<'PY'
import json, pathlib, sqlite3, time, sys
db=pathlib.Path(sys.argv[1]).resolve()
conn=sqlite3.connect(db.as_uri()+"?mode=ro",uri=True); conn.row_factory=sqlite3.Row
agent="p9-3c-fixture-e1"
expected_worktree=str(db.parent.parent / "work" / agent)
prompt='{"contract_version":1,"mode":"hold","quiet_seconds":75,"spawn_descendant":true}'
start=time.monotonic()
while time.monotonic()-start < 5:
    rows=conn.execute("SELECT * FROM jobs WHERE assigned_agent=? ORDER BY created_at",(agent,)).fetchall()
    matches=[]
    for row in rows:
        payload=json.loads(row["payload_json"])
        if payload.get("prompt")==prompt: matches.append(row)
    if len(matches)>1: raise SystemExit("multiple hold jobs")
    if matches and matches[0]["status"]=="running":
        job=matches[0]
        payload=json.loads(job["payload_json"]); context=payload.get("execution_context")
        if job["worktree_path"]!=expected_worktree or not isinstance(context,dict) or context.get("worktree_path")!=expected_worktree: raise SystemExit("hold worktree authority mismatch")
        leases=conn.execute("SELECT * FROM execution_attempt_leases WHERE job_id=? AND status='active'",(job["id"],)).fetchall()
        if len(leases)!=1: raise SystemExit("hold active lease count mismatch")
        lease=leases[0]
        if lease["attempt_token"]!=1 or lease["agent_id"]!=agent: raise SystemExit("hold lease identity mismatch")
        if lease["normalized_path"]!=expected_worktree: raise SystemExit("hold lease worktree mismatch")
        print(json.dumps({"job_id":job["id"],"lease_id":lease["lease_id"],"attempt_token":1,"acquired_at":lease["acquired_at"],"expires_at":lease["expires_at"]},sort_keys=True,separators=(",",":")))
        raise SystemExit(0)
    time.sleep(.1)
raise SystemExit("hold job did not reach running in five seconds")
PY
}
_p9c0_hold_monitor() { _p9c0_real_hold_monitor; }

_p9c0_real_process_tree_proof() {
    local unit="$1" fixture_pid="$2"
    python3 - "$(_p9c0_ledger_path)" "$unit" "$fixture_pid" "$P9C0_FIXTURE_BIN" \
        "$(_p9c0_worktree_path_for_agent p9-3c-fixture-e1)" <<'PY'
import pathlib, re, shutil, sys, time
ledger, unit, fixture_pid, fixture_bin, expected_worktree = sys.argv[1:]
fixture_pid=int(fixture_pid)
fixture_path=pathlib.Path(fixture_bin)
records=[]
for line in open(ledger,encoding="utf-8"):
    if line.startswith("unit "+unit+" "): records.append(line.rstrip())
if len(records)!=1: raise SystemExit("exact unit ledger record count mismatch")
fields={}
for token in records[0].split()[2:]:
    if "=" in token:
        key,value=token.split("=",1); fields[key]=value
main=int(fields.get("main_pid","0")); cgroup=fields.get("cgroup","")
if main<=1 or not cgroup.startswith("/") or ".." in cgroup.split("/"): raise SystemExit("unit main_pid/cgroup authority malformed")
cgroup_file=pathlib.Path("/sys/fs/cgroup"+cgroup+"/cgroup.procs")
if not cgroup_file.is_file(): raise SystemExit("recorded cgroup.procs missing")

def cmd(pid):
    return pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().rstrip(b"\0").split(b"\0")
def env(pid):
    raw=pathlib.Path(f"/proc/{pid}/environ").read_bytes().rstrip(b"\0")
    return [x.decode("utf-8","strict") for x in raw.split(b"\0") if x]
def ppid(pid):
    text=pathlib.Path(f"/proc/{pid}/status").read_text()
    return int(re.search(r"^PPid:\s+(\d+)$",text,re.M).group(1))

for _ in range(20):
    pids=[int(x) for x in cgroup_file.read_text().split()]
    if main not in pids or fixture_pid not in pids: raise SystemExit("main/fixture pid outside recorded cgroup")
    commands={pid:cmd(pid) for pid in pids}
    sleeps=[pid for pid,c in commands.items() if c==[b"/bin/sleep",b"300"]]
    if len(sleeps)!=1: raise SystemExit("exact sleep descendant count mismatch")
    sleep_pid=sleeps[0]
    if ppid(fixture_pid)!=main or ppid(sleep_pid)!=fixture_pid: raise SystemExit("fixture process parentage mismatch")
    main_args=[x.decode("utf-8","strict") for x in commands[main]]
    if "-m" not in main_args or "multinexus.agentd" not in main_args or "--log-level" not in main_args or "DEBUG" not in main_args: raise SystemExit("agentd argv mismatch")
    allowed={main,fixture_pid,sleep_pid}
    extras=[pid for pid in pids if pid not in allowed]
    if extras:
        time.sleep(.1); continue
    main_env=env(main); fixture_env=env(fixture_pid)
    if main_env != ["PATH=/usr/local/bin:/usr/bin:/bin"]: raise SystemExit(f"agentd environment mismatch: {main_env}")
    # CPython's PEP 538 locale coercion adds this exact non-secret value to
    # ``os.environ`` after process start, so filtered_env forwards it even
    # though the agentd process's original /proc environ contains only PATH.
    expected_env=[
        "PATH=/usr/local/bin:/usr/bin:/bin", "LC_CTYPE=C.UTF-8",
        f"PWD={expected_worktree}",
    ]
    if sorted(fixture_env) != sorted(expected_env): raise SystemExit(f"fixture environment mismatch: {fixture_env}")
    with fixture_path.open("rb") as source:
        if source.readline().rstrip(b"\r\n") != b"#!/usr/bin/env python3": raise SystemExit("fixture shebang mismatch")
    fixture_args=[x.decode("utf-8","strict") for x in commands[fixture_pid]]
    expected_fixture_args=[
        "python3", fixture_bin, "-p", "--verbose", "--output-format",
        "stream-json", "--include-partial-messages",
    ]
    if fixture_args != expected_fixture_args: raise SystemExit(f"fixture argv mismatch: {fixture_args}")
    expected_python=shutil.which("python3", path="/usr/local/bin:/usr/bin:/bin")
    if not expected_python: raise SystemExit("approved python3 interpreter missing")
    actual_executable=pathlib.Path(f"/proc/{fixture_pid}/exe").resolve(strict=True)
    if actual_executable != pathlib.Path(expected_python).resolve(strict=True): raise SystemExit("fixture interpreter mismatch")
    print(f"process-tree unit={unit} main_pid={main} fixture_pid={fixture_pid} sleep_pid={sleep_pid} cgroup={cgroup}")
    raise SystemExit(0)
raise SystemExit("ephemeral Coordinate child did not quiesce for exact sample")
PY
}
_p9c0_process_tree_proof() { _p9c0_real_process_tree_proof "$@"; }

_p9c0_real_wait_monotonic_target() {
    python3 - "$1" "$2" <<'PY'
import sys,time
start=int(sys.argv[1]); target=int(sys.argv[2]); now=int(time.monotonic()*1000)
if start>now: raise SystemExit("monotonic boundary is in the future")
delay=(start+target-now)/1000
if delay>0: time.sleep(delay)
PY
}
_p9c0_wait_monotonic_target() { _p9c0_real_wait_monotonic_target "$@"; }

_p9c0_real_hold_authority() {
    local seed_json="$1" output="$2"
    python3 - "$(_p9c0_controller_db_path)" "$seed_json" "$output" <<'PY'
import json,os,pathlib,sqlite3,sys
db,seed_raw,out=sys.argv[1:]; seed=json.loads(seed_raw)
conn=sqlite3.connect(pathlib.Path(db).resolve().as_uri()+"?mode=ro",uri=True); conn.row_factory=sqlite3.Row
attempt=int(seed["attempt_token"])
job=conn.execute("SELECT * FROM jobs WHERE id=?",(seed["job_id"],)).fetchone()
lease=conn.execute("SELECT * FROM execution_attempt_leases WHERE lease_id=?",(seed["lease_id"],)).fetchone()
if not job or not lease or job["status"]!="running" or job["attempt_count"]!=attempt or lease["status"]!="active" or lease["attempt_token"]!=attempt: raise SystemExit("hold authority changed before expiry")
payload={"job_id":job["id"],"lease_id":lease["lease_id"],"attempt_token":attempt,"expires_at":lease["expires_at"],"agent_id":lease["agent_id"]}
fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(payload,f,sort_keys=True,separators=(",",":")); f.write("\n")
print("lease-active lease_id={lease_id} expires_at={expires_at}".format(**payload))
PY
}
_p9c0_hold_authority() { _p9c0_real_hold_authority "$@"; }

_p9c0_real_verify_hold_scenario() {
    local agent="p9-3c-fixture-e1" unit boundary_before boundary_after seed boundary_line ns pid start_ms proof now_ms authority output
    unit="$agent-$P9C0_RUN_ID.service"
    boundary_before="$(_p9c0_unit_journal "$unit" | _p9c0_claude_boundary_lines | wc -l | tr -d '[:space:]')"
    _p9c0_submit_request "$agent" hold true hold >/dev/null \
        || _p9c0_die "hold request submit failed" 99
    seed="$(_p9c0_hold_monitor)" || _p9c0_die "hold job/lease monitor failed" 99
    local tries=0 journal=""
    while [[ $tries -lt 50 ]]; do
        journal="$(_p9c0_unit_journal "$unit")" || _p9c0_die "hold unit journal read failed" 99
        boundary_after="$(printf '%s\n' "$journal" | _p9c0_claude_boundary_lines | wc -l | tr -d '[:space:]')"
        [[ "$boundary_after" -eq $((boundary_before + 1)) ]] && break
        [[ "$boundary_after" -le $((boundary_before + 1)) ]] \
            || _p9c0_die "ambiguous extra Claude adapter boundary" 99
        _p9c0_sleep 0.1; tries=$((tries + 1))
    done
    [[ "$boundary_after" -eq $((boundary_before + 1)) ]] \
        || _p9c0_die "hold adapter boundary missing" 99
    boundary_line="$(printf '%s\n' "$journal" | _p9c0_claude_boundary_lines | tail -n 1)"
    [[ "$boundary_line" =~ ^claude_child_boundary\ monotonic_ns=([0-9]+)\ pid=([0-9]+)$ ]] \
        || _p9c0_die "hold adapter boundary malformed" 99
    ns="${BASH_REMATCH[1]}"; pid="${BASH_REMATCH[2]}"; start_ms=$((ns / 1000000))
    proof="$(_p9c0_process_tree_proof "$unit" "$pid")" \
        || _p9c0_die "hold process/cgroup/environment proof failed" 99
    _p9c0_ledger_append "$boundary_line"
    _p9c0_ledger_append "$proof"
    _p9c0_record_intake "$P9C0_INTAKE_FROZEN"
    _p9c0_ledger_append "intake frozen run=$P9C0_RUN_ID"
    _p9c0_wait_monotonic_target "$start_ms" 80000 \
        || _p9c0_die "hold stop target wait failed" 99
    _p9c0_unit_stop "$agent" --crash \
        --fixture-start-monotonic-ms "$start_ms" --evidence-run-id "$P9C0_RUN_ID" \
        || _p9c0_die "hold exact timed stop failed" 99
    now_ms="$(python3 -c 'import time; print(int(time.monotonic()*1000))')"
    [[ $((now_ms - start_ms)) -lt 88000 ]] \
        || _p9c0_die "hold stop/cgroup proof exceeded absolute 88-second margin" 99
    _p9c0_unit_stop p9-3c-fixture-e2 \
        || _p9c0_die "E2 exact stop failed after hold" 99
    output="$(_p9c0_per_run_root)/evidence/hold-authority.json"
    authority="$(_p9c0_hold_authority "$seed" "$output")" \
        || _p9c0_die "hold lease authority capture failed" 99
    _p9c0_chown 0 0 "$output"; _p9c0_chmod 0600 "$output"
    _p9c0_ledger_append "$authority"
    _p9c0_production_snapshot compare "$(_p9c0_per_run_root)/evidence/production-baseline.json" \
        || _p9c0_die "production state drifted during hold scenario" 99
}
_p9c0_verify_hold_scenario() { _p9c0_real_verify_hold_scenario; }

_p9c0_real_wait_expiry() {
    python3 - "$1" <<'PY'
import datetime as dt,sys,time
x=dt.datetime.fromisoformat(sys.argv[1].replace("Z","+00:00"))
if x.tzinfo is None: raise SystemExit("expiry lacks timezone")
while dt.datetime.now(dt.timezone.utc)<=x:
    time.sleep(min(1,max(.01,(x-dt.datetime.now(dt.timezone.utc)).total_seconds()+.01)))
PY
}
_p9c0_wait_expiry() { _p9c0_real_wait_expiry "$@"; }

_p9c0_real_reap_state() {
    local when="$1" authority="$2"
    python3 - "$(_p9c0_controller_db_path)" "$when" "$authority" <<'PY'
import json,pathlib,sqlite3,sys
db,when,auth_raw=sys.argv[1:]; auth=json.loads(pathlib.Path(auth_raw).read_text())
conn=sqlite3.connect(pathlib.Path(db).resolve().as_uri()+"?mode=ro",uri=True); conn.row_factory=sqlite3.Row
job=conn.execute("SELECT * FROM jobs WHERE id=?",(auth["job_id"],)).fetchone(); lease=conn.execute("SELECT * FROM execution_attempt_leases WHERE lease_id=?",(auth["lease_id"],)).fetchone()
if not job or not lease: raise SystemExit("reap authority row missing")
active=conn.execute("SELECT * FROM execution_attempt_leases WHERE status='active'").fetchall()
inflight=conn.execute("SELECT * FROM jobs WHERE status IN ('pending','running')").fetchall()
if when=="before":
    if len(active)!=1 or active[0]["lease_id"]!=auth["lease_id"] or len(inflight)!=1 or inflight[0]["id"]!=auth["job_id"]: raise SystemExit("literal pre-reap quiescence mismatch")
    if job["status"]!="running" or lease["status"]!="active": raise SystemExit("pre-reap state mismatch")
elif when=="after":
    if job["status"]!="timed_out" or not job["recoverable"] or lease["status"]!="expired": raise SystemExit("post-reap recovery state mismatch")
    events=conn.execute("SELECT event_type FROM events WHERE json_extract(payload_json,'$.job_id')=?",(auth["job_id"],)).fetchall()
    kinds={r[0] for r in events}
    if not {"execution_lease.expired","job.timed_out"}.issubset(kinds): raise SystemExit("expiry event evidence missing")
else: raise SystemExit("unknown reap state")
PY
}
_p9c0_reap_state() { _p9c0_real_reap_state "$@"; }

_p9c0_reap_once() {
    local authority="$1" output
    _p9c0_reap_state before "$authority" || _p9c0_die "pre-reap exact quiescence failed" 100
    output="$(_p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" runtime job lease reap --actor p9-3c0-local-verify --batch-size 100)" \
        || _p9c0_die "isolated lease reap command failed" 100
    python3 - "$output" <<'PY' || exit 100
import json,sys
x=json.loads(sys.argv[1]); r=x.get("result",{})
if r.get("due_found")!=1 or r.get("reaped_count")!=1 or r.get("errors")!=[] or len(r.get("reaped",[]))!=1: raise SystemExit("reap summary mismatch")
PY
    _p9c0_reap_state after "$authority" || _p9c0_die "post-reap state failed" 100
}

_p9c0_real_verify_first_reap() {
    local authority expiry lease
    authority="$(_p9c0_per_run_root)/evidence/hold-authority.json"
    expiry="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["expires_at"])' "$authority")" \
        || _p9c0_die "hold expiry evidence unreadable" 100
    lease="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease_id"])' "$authority")"
    grep -Fqx "cgroup-empty unit=p9-3c-fixture-e1-$P9C0_RUN_ID.service" "$(_p9c0_ledger_path)" \
        || _p9c0_die "E1 cgroup-empty proof missing before reap" 100
    grep -Fqx "cgroup-empty unit=p9-3c-fixture-e2-$P9C0_RUN_ID.service" "$(_p9c0_ledger_path)" \
        || _p9c0_die "E2 cgroup-empty proof missing before reap" 100
    _p9c0_wait_expiry "$expiry" || _p9c0_die "wait past N expiry failed" 100
    _p9c0_reap_once "$authority"
    _p9c0_ledger_append "lease-terminal lease_id=$lease"
    _p9c0_ledger_append "first-reap job-authority=$authority"
}
_p9c0_verify_first_reap() { _p9c0_real_verify_first_reap; }
_p9c0_real_recovery_monitor() {
    local old_authority="$1" output="$2"
    python3 - "$(_p9c0_controller_db_path)" "$old_authority" "$output" <<'PY'
import datetime as dt,json,os,pathlib,sqlite3,sys,time
db,old_path,out=sys.argv[1:]; old=json.loads(pathlib.Path(old_path).read_text())
db_path=pathlib.Path(db).resolve(); agent="p9-3c-fixture-e1"; expected_worktree=str(db_path.parent.parent / "work" / agent)
conn=sqlite3.connect(db_path.as_uri()+"?mode=ro",uri=True); conn.row_factory=sqlite3.Row
start=time.monotonic()
while time.monotonic()-start<5:
    job=conn.execute("SELECT * FROM jobs WHERE id=?",(old["job_id"],)).fetchone()
    if job and job["status"]=="running" and job["attempt_count"]==old["attempt_token"]+1:
        payload=json.loads(job["payload_json"]); context=payload.get("execution_context")
        if job["worktree_path"]!=expected_worktree or not isinstance(context,dict) or context.get("worktree_path")!=expected_worktree: raise SystemExit("recovery worktree authority mismatch")
        leases=conn.execute("SELECT * FROM execution_attempt_leases WHERE job_id=? AND status='active'",(job["id"],)).fetchall()
        if len(leases)!=1: raise SystemExit("recovery active lease count mismatch")
        lease=leases[0]; attempt=old["attempt_token"]+1
        if lease["attempt_token"]!=attempt or lease["lease_id"]==old["lease_id"] or lease["agent_id"]!=agent: raise SystemExit("recovery lease identity mismatch")
        if lease["normalized_path"]!=expected_worktree: raise SystemExit("recovery lease worktree mismatch")
        acquired=dt.datetime.fromisoformat(lease["acquired_at"].replace("Z","+00:00")); expiry=dt.datetime.fromisoformat(lease["expires_at"].replace("Z","+00:00"))
        if (expiry-acquired).total_seconds()!=120: raise SystemExit("recovery lease TTL mismatch")
        events=conn.execute("SELECT payload_json FROM events WHERE event_type='job.claimed' AND idempotency_key=?",(f"runtime:job:{job['id']}:claimed:{attempt}",)).fetchall()
        if len(events)!=1: raise SystemExit("recovery job.claimed event missing")
        payload=json.loads(events[0][0])
        if payload.get("previous_status")!="timed_out" or payload.get("recovered") is not True or payload.get("recovery_reason")!="p9-3c0-expired-after-exact-unit-stop" or payload.get("prior_process_stopped") is not True: raise SystemExit("recovery claim evidence mismatch")
        result={"job_id":job["id"],"lease_id":lease["lease_id"],"attempt_token":attempt,"expires_at":lease["expires_at"],"agent_id":lease["agent_id"],"host_id":lease["host_id"]}
        fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(result,f,sort_keys=True,separators=(",",":")); f.write("\n")
        print(json.dumps(result,sort_keys=True,separators=(",",":")))
        raise SystemExit(0)
    time.sleep(.1)
raise SystemExit("recovery N+1 did not reach running within five seconds")
PY
}
_p9c0_recovery_monitor() { _p9c0_real_recovery_monitor "$@"; }

_p9c0_real_verify_recovery_start() {
    local primary="$P9C0_RUN_ID" recovery old_authority old_unit reason reason_sha saved_db
    local unit boundary_before boundary_after journal line pid evidence seed output
    old_authority="$(_p9c0_per_run_root)/evidence/hold-authority.json"
    old_unit="p9-3c-fixture-e1-$primary.service"
    grep -Fqx "cgroup-empty unit=$old_unit" "$(_p9c0_ledger_path)" \
        || _p9c0_die "prior-process-stopped lacks exact cgroup proof" 101
    _p9c0_prepare_recovery_namespace "$primary"
    recovery="$(_p9c0_recovery_run_id "$primary")" || _p9c0_die "recovery id derivation failed" 101
    reason="p9-3c0-expired-after-exact-unit-stop"
    reason_sha="$(printf '%s' "$reason" | sha256sum | awk '{print $1}')"
    saved_db="$P9C0_COORD_DB"
    P9C0_RUN_ID="$recovery"
    P9C0_COORD_DB="$(_p9c0_controller_state_prefix)/$primary/db/coord.sqlite3"
    _p9c0_ledger_append "recovery-of original_unit=$old_unit prior_proof=cgroup-empty reason_sha256=$reason_sha"
    unit="p9-3c-fixture-e1-$recovery.service"
    boundary_before="$(_p9c0_unit_journal "$unit" | _p9c0_claude_boundary_lines | wc -l | tr -d '[:space:]')"
    [[ "$boundary_before" -eq 0 ]] || _p9c0_die "recovery unit has pre-existing adapter boundary" 101
    _p9c0_unit_start p9-3c-fixture-e1 hold \
        --recoverable --recovery-reason "$reason" --prior-process-stopped \
        || _p9c0_die "recovery unit start failed" 101
    output="$(_p9c0_controller_state_prefix)/$primary/evidence/recovery-authority.json"
    seed="$(_p9c0_recovery_monitor "$old_authority" "$output")" \
        || _p9c0_die "recovery N+1 monitor failed" 101
    _p9c0_chown 0 0 "$output"; _p9c0_chmod 0600 "$output"
    local tries=0
    while [[ $tries -lt 50 ]]; do
        journal="$(_p9c0_unit_journal "$unit")" || _p9c0_die "recovery journal read failed" 101
        boundary_after="$(printf '%s\n' "$journal" | _p9c0_claude_boundary_lines | wc -l | tr -d '[:space:]')"
        [[ "$boundary_after" -eq 1 ]] && break
        [[ "$boundary_after" -le 1 ]] || _p9c0_die "ambiguous recovery adapter boundary" 101
        _p9c0_sleep .1; tries=$((tries+1))
    done
    [[ "$boundary_after" -eq 1 ]] || _p9c0_die "recovery adapter boundary missing" 101
    line="$(printf '%s\n' "$journal" | _p9c0_claude_boundary_lines)"
    [[ "$line" =~ ^claude_child_boundary\ monotonic_ns=[0-9]+\ pid=([0-9]+)$ ]] \
        || _p9c0_die "recovery boundary malformed" 101
    pid="${BASH_REMATCH[1]}"
    evidence="$(_p9c0_process_tree_proof "$unit" "$pid")" \
        || _p9c0_die "recovery process proof failed" 101
    _p9c0_ledger_append "$line"; _p9c0_ledger_append "$evidence"
    _p9c0_record_intake "$P9C0_INTAKE_FROZEN"
    P9C0_RUN_ID="$primary"
    P9C0_COORD_DB="$saved_db"
    _p9c0_ledger_append "recovery-ready run_id=$recovery evidence=$output"
}
_p9c0_verify_recovery_start() { _p9c0_real_verify_recovery_start; }

_p9c0_real_stale_snapshot() {
    local authority="$1"
    python3 - "$(_p9c0_controller_db_path)" "$authority" <<'PY'
import hashlib,json,pathlib,sqlite3,sys
db,auth_path=sys.argv[1:]; auth=json.loads(pathlib.Path(auth_path).read_text())
conn=sqlite3.connect(pathlib.Path(db).resolve().as_uri()+"?mode=ro",uri=True); conn.row_factory=sqlite3.Row
job=conn.execute("SELECT * FROM jobs WHERE id=?",(auth["job_id"],)).fetchone(); lease=conn.execute("SELECT * FROM execution_attempt_leases WHERE lease_id=?",(auth["lease_id"],)).fetchone()
if not job or not lease or job["status"]!="running" or job["attempt_count"]!=auth["attempt_token"] or lease["status"]!="active": raise SystemExit("N+1 is not exact running authority")
payload={"job":dict(job),"lease":dict(lease),"events":[tuple(r) for r in conn.execute("SELECT COUNT(*),COALESCE(MAX(rowid),0) FROM events")],"deliveries":[tuple(r) for r in conn.execute("SELECT COUNT(*),COALESCE(MAX(rowid),0) FROM deliveries")]}
print(hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest())
PY
}
_p9c0_stale_snapshot() { _p9c0_real_stale_snapshot "$@"; }

_p9c0_real_verify_stale_reject() {
    local primary="$P9C0_RUN_ID" recovery old new before after output status agent="p9-3c-fixture-e1" saved_db authority_line
    old="$(_p9c0_per_run_root)/evidence/hold-authority.json"
    new="$(_p9c0_per_run_root)/evidence/recovery-authority.json"
    before="$(_p9c0_stale_snapshot "$new")" || _p9c0_die "pre-stale N+1 snapshot failed" 102
    local job old_lease old_attempt
    job="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["job_id"])' "$old")"
    old_lease="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease_id"])' "$old")"
    old_attempt="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["attempt_token"])' "$old")"
    if output="$(_p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
            runtime job report "$job" --agent-id "$agent" --status "done" \
            --result-json '{"response_text":"stale attempt must reject"}' \
            --attempt-token "$old_attempt" --lease-id "$old_lease" \
            --actor p9-3c0-stale-probe 2>&1)"; then
        _p9c0_die "old-N stale report was accepted" 102
    else
        status=$?
    fi
    [[ "$status" -ne 0 ]] || _p9c0_die "old-N stale report status invalid" 102
    [[ ${#output} -le 2000 && "$output" =~ [Ss]tale|attempt|lease ]] \
        || _p9c0_die "stale rejection output is missing bounded authority" 102
    after="$(_p9c0_stale_snapshot "$new")" || _p9c0_die "post-stale N+1 snapshot failed" 102
    [[ "$before" == "$after" ]] || _p9c0_die "rejected stale report mutated durable state" 102
    recovery="$(_p9c0_recovery_run_id "$primary")"
    saved_db="$P9C0_COORD_DB"
    P9C0_RUN_ID="$recovery"; P9C0_COORD_DB="$(_p9c0_controller_state_prefix)/$primary/db/coord.sqlite3"
    _p9c0_unit_stop "$agent" --crash \
        || _p9c0_die "recovery exact crash stop failed" 102
    authority_line="$(_p9c0_hold_authority "$(cat "$new")" "$(_p9c0_per_run_root)/evidence/recovery-stopped-authority.json")" \
        || _p9c0_die "recovery latest expiry capture failed" 102
    _p9c0_ledger_append "$authority_line"
    P9C0_RUN_ID="$primary"; P9C0_COORD_DB="$saved_db"
    _p9c0_ledger_append "stale-rejected old_lease=$old_lease recovery_run=$recovery snapshot=$before"
}
_p9c0_verify_stale_reject() { _p9c0_real_verify_stale_reject; }

_p9c0_real_verify_second_reap() {
    local primary="$P9C0_RUN_ID" recovery authority expiry lease recovery_ledger saved_db
    recovery="$(_p9c0_recovery_run_id "$primary")"
    authority="$(_p9c0_controller_state_prefix)/$recovery/evidence/recovery-stopped-authority.json"
    expiry="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["expires_at"])' "$authority")" \
        || _p9c0_die "N+1 expiry evidence unreadable" 103
    lease="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["lease_id"])' "$authority")"
    recovery_ledger="$(_p9c0_controller_state_prefix)/$recovery/ledger/events.jsonl"
    grep -Fqx "cgroup-empty unit=p9-3c-fixture-e1-$recovery.service" "$recovery_ledger" \
        || _p9c0_die "recovery cgroup-empty proof missing before second reap" 103
    _p9c0_wait_expiry "$expiry" || _p9c0_die "wait past N+1 expiry failed" 103
    _p9c0_reap_once "$authority"
    saved_db="$P9C0_COORD_DB"
    P9C0_RUN_ID="$recovery"
    P9C0_COORD_DB="$(_p9c0_controller_state_prefix)/$primary/db/coord.sqlite3"
    _p9c0_ledger_append "lease-terminal lease_id=$lease"
    P9C0_RUN_ID="$primary"
    P9C0_COORD_DB="$saved_db"
    _p9c0_ledger_append "second-reap recovery_run=$recovery lease_id=$lease"
}
_p9c0_verify_second_reap() { _p9c0_real_verify_second_reap; }

_p9c0_real_run_cleanup() {
    /opt/multinexus/scripts/p9-3c0-cleanup.sh cleanup \
        --run-id "$P9C0_RUN_ID" \
        --unit-user "$P9C0_UNIT_USER" \
        --unit-group "$P9C0_UNIT_GROUP"
}
_p9c0_run_cleanup() { _p9c0_real_run_cleanup; }

_p9c0_verify_run_locked() {
    local current
    current="$(_p9c0_verify_current_phase)"
    [[ "$current" != "$P9C0_PHASE_FAILED" ]] \
        || _p9c0_die "cannot resume a failed verification run" 95
    if [[ "$current" == "$P9C0_PHASE_READY" ]]; then
        _p9c0_verify_capture_baseline
        _p9c0_transition_phase "$P9C0_PHASE_BASELINE"
        current="$P9C0_PHASE_BASELINE"
    fi
    if [[ "$current" == "$P9C0_PHASE_BASELINE" ]]; then
        _p9c0_verify_prepare_catalog
        _p9c0_transition_phase "$P9C0_PHASE_CATALOG"
        current="$P9C0_PHASE_CATALOG"
    fi
    if [[ "$current" == "$P9C0_PHASE_CATALOG" ]]; then
        _p9c0_verify_base_scenario
        _p9c0_transition_phase "$P9C0_PHASE_BASE"
        current="$P9C0_PHASE_BASE"
    fi
    if [[ "$current" == "$P9C0_PHASE_BASE" ]]; then
        _p9c0_verify_hold_scenario
        _p9c0_transition_phase "$P9C0_PHASE_HOLD"
        current="$P9C0_PHASE_HOLD"
    fi
    if [[ "$current" == "$P9C0_PHASE_HOLD" ]]; then
        _p9c0_verify_first_reap
        _p9c0_transition_phase "$P9C0_PHASE_FIRST_REAP"
        current="$P9C0_PHASE_FIRST_REAP"
    fi
    if [[ "$current" == "$P9C0_PHASE_FIRST_REAP" ]]; then
        _p9c0_verify_recovery_start
        _p9c0_transition_phase "$P9C0_PHASE_RECOVERY"
        current="$P9C0_PHASE_RECOVERY"
    fi
    if [[ "$current" == "$P9C0_PHASE_RECOVERY" ]]; then
        _p9c0_verify_stale_reject
        _p9c0_transition_phase "$P9C0_PHASE_STALE"
        current="$P9C0_PHASE_STALE"
    fi
    if [[ "$current" == "$P9C0_PHASE_STALE" ]]; then
        _p9c0_verify_second_reap
        _p9c0_transition_phase "$P9C0_PHASE_SECOND_REAP"
        current="$P9C0_PHASE_SECOND_REAP"
    fi
    if [[ "$current" == "$P9C0_PHASE_SECOND_REAP" ]]; then
        _p9c0_production_snapshot compare \
            "$(_p9c0_per_run_root)/evidence/production-baseline.json" \
            || _p9c0_die "production state changed during isolated verification" 95
        _p9c0_transition_phase "$P9C0_PHASE_CLEANUP_READY"
        current="$P9C0_PHASE_CLEANUP_READY"
    fi
    [[ "$current" == "$P9C0_PHASE_CLEANUP_READY" || "$current" == "$P9C0_PHASE_DONE" ]] \
        || _p9c0_die "verification stopped at unsupported phase: $current" 95
}

_p9c0_verify_finish_locked() {
    local current
    current="$(_p9c0_verify_current_phase)"
    [[ "$current" == "$P9C0_PHASE_CLEANUP_READY" ]] \
        || _p9c0_die "cleanup returned outside cleanup-ready phase" 96
    _p9c0_transition_phase "$P9C0_PHASE_DONE"
    _p9c0_record_evidence verified-and-cleaned
    _p9c0_ledger_append "verification done run=$P9C0_RUN_ID"
}

_p9c0_controller_verify() {
    P9C0_RUN_ID="$P9C0_ARG_RUN_ID"
    P9C0_UNIT_USER="$P9C0_ARG_UNIT_USER"
    P9C0_UNIT_GROUP="$P9C0_ARG_UNIT_GROUP"
    P9C0_AGENT_ID="local-operator"
    P9C0_COORD_DB=""
    _p9c0_validate_run_id "$P9C0_RUN_ID" || _p9c0_die "invalid run id" 93
    _p9c0_recovery_run_id "$P9C0_RUN_ID" >/dev/null \
        || _p9c0_die "run id cannot derive a bounded recovery namespace" 93
    [[ "$(_p9c0_euid)" == "0" ]] || _p9c0_die "verification controller must run as root" 93
    [[ "$P9C0_UNIT_USER" != "root" && "$P9C0_UNIT_GROUP" != "root" ]] \
        || _p9c0_die "unit user/group cannot be root" 93
    _p9c0_verify_load_sealed_identity
    _p9c0_with_run_lock _p9c0_verify_run_locked
    if [[ "$(_p9c0_verify_current_phase)" == "$P9C0_PHASE_CLEANUP_READY" ]]; then
        _p9c0_run_cleanup || _p9c0_die "isolated cleanup controller failed" 96
        _p9c0_with_run_lock _p9c0_verify_finish_locked
    fi
}

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

main() {
    P9C0_ARG_RUN_ID=""
    P9C0_ARG_UNIT_USER=""
    P9C0_ARG_UNIT_GROUP=""
    P9C0_ARG_AGENT_ID=""

    local subcommand="${1:-}"; shift || true
    case "$subcommand" in
        prepare|verify)
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --run-id)
                        [[ $# -ge 2 ]] || _p9c0_usage
                        P9C0_ARG_RUN_ID="$2"; shift 2;;
                    --unit-user)
                        [[ $# -ge 2 ]] || _p9c0_usage
                        P9C0_ARG_UNIT_USER="$2"; shift 2;;
                    --unit-group)
                        [[ $# -ge 2 ]] || _p9c0_usage
                        P9C0_ARG_UNIT_GROUP="$2"; shift 2;;
                    --agent)
                        [[ $# -ge 2 ]] || _p9c0_usage
                        P9C0_ARG_AGENT_ID="$2"; shift 2;;
                    *)
                        _p9c0_usage;;
                esac
            done
            [[ -n "$P9C0_ARG_RUN_ID" ]] || _p9c0_usage
            [[ -n "$P9C0_ARG_UNIT_USER" ]] || _p9c0_usage
            [[ -n "$P9C0_ARG_UNIT_GROUP" ]] || _p9c0_usage
            if [[ "$subcommand" == "prepare" ]]; then
                [[ -n "$P9C0_ARG_AGENT_ID" ]] || _p9c0_usage
            else
                [[ -z "$P9C0_ARG_AGENT_ID" ]] || _p9c0_usage
            fi
            trap '_p9c0_on_exit $?' EXIT
            trap 'exit 129' HUP
            trap 'exit 130' INT
            trap 'exit 143' TERM
            if [[ "$subcommand" == "prepare" ]]; then
                _p9c0_controller_prepare
            else
                _p9c0_controller_verify
            fi
            trap - EXIT HUP INT TERM
            ;;
        *)
            _p9c0_usage;;
    esac
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
