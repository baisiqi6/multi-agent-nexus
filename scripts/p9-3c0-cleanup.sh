#!/usr/bin/env bash
# P9-3C0 Package 3 isolated-sidecar cleanup controller.
#
# Source-safe and fail-closed.  The production entrypoint accepts only the
# fixed /var/tmp/multinexus-p9-3c0 namespace.  All operating-system and
# Coordinate effects are behind replaceable seams for local unit tests.

set -uo pipefail

P9C0_CLEANUP_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=/dev/null
source "$P9C0_CLEANUP_SCRIPT_DIR/p9-3c0-local-verify.sh"

P9C0_CLEANUP_HELPER="/opt/multinexus/multinexus/fixture/bin/p9-3c0-unit.sh"
P9C0_CLEANUP_CONFIG_ROOT="/opt/multinexus/multinexus/fixture/config"
P9C0_EXECUTOR_V3="$P9C0_CLEANUP_CONFIG_ROOT/executor.fixture.v3-disabled.toml"
P9C0_CAPACITY_V2="$P9C0_CLEANUP_CONFIG_ROOT/capacity.fixture.v2-empty.toml"
P9C0_EXECUTOR_V4="$P9C0_CLEANUP_CONFIG_ROOT/executor.fixture.v4-empty.toml"

P9C0_CLEANUP_PHASES=(
    "freeze"
    "units-quiescent"
    "executor-v3-disabled"
    "capacity-v2-empty"
    "executor-v4-empty"
    "units-cleaned"
    "snapshot-retained"
    "done"
)

_p9c0_cleanup_die() {
    printf 'p9-3c0-cleanup: %s\n' "$1" >&2
    exit "${2:-1}"
}

_p9c0_cleanup_usage() {
    _p9c0_cleanup_die \
        "usage: $0 cleanup --run-id <id> --unit-user <name> --unit-group <name>" 2
}

_p9c0_cleanup_phase_path() {
    printf '%s/%s/control/cleanup-phase\n' \
        "$(_p9c0_controller_state_prefix)" "$P9C0_RUN_ID"
}

_p9c0_cleanup_phase_rank() {
    local phase="$1" index
    for index in "${!P9C0_CLEANUP_PHASES[@]}"; do
        if [[ "${P9C0_CLEANUP_PHASES[$index]}" == "$phase" ]]; then
            printf '%s\n' "$index"
            return 0
        fi
    done
    return 1
}

_p9c0_cleanup_current_phase() {
    local path line phase
    path="$(_p9c0_cleanup_phase_path)"
    [[ -e "$path" || -L "$path" ]] || return 1
    _p9c0_enforce_root_owned_file "$path" "600" "0" "0" \
        || _p9c0_cleanup_die "cleanup phase authority rejected: $path"
    [[ "$(wc -l < "$path" | tr -d ' ')" == "1" ]] \
        || _p9c0_cleanup_die "cleanup phase must be one line"
    line="$(cat "$path")" || _p9c0_cleanup_die "cleanup phase read failed"
    case "$line" in cleanup-phase=*) phase="${line#cleanup-phase=}" ;; *)
        _p9c0_cleanup_die "cleanup phase record malformed" ;;
    esac
    _p9c0_cleanup_phase_rank "$phase" >/dev/null \
        || _p9c0_cleanup_die "unknown cleanup phase: $phase"
    printf '%s\n' "$phase"
}

_p9c0_cleanup_record_phase() {
    local phase="$1"
    _p9c0_cleanup_phase_rank "$phase" >/dev/null \
        || _p9c0_cleanup_die "unknown cleanup phase: $phase"
    _p9c0_atomic_root_record "$(_p9c0_cleanup_phase_path)" "cleanup-phase=$phase"
    _p9c0_ledger_append "cleanup-phase=$phase"
}

_p9c0_cleanup_advance() {
    local expected="$1" next="$2" current
    current="$(_p9c0_cleanup_current_phase)" \
        || _p9c0_cleanup_die "cleanup phase missing before transition"
    [[ "$current" == "$expected" ]] \
        || _p9c0_cleanup_die "cleanup phase transition mismatch: $current != $expected"
    [[ "$(_p9c0_cleanup_phase_rank "$next")" -eq \
       $(( $(_p9c0_cleanup_phase_rank "$expected") + 1 )) ]] \
        || _p9c0_cleanup_die "cleanup phase transition is not adjacent"
    _p9c0_cleanup_record_phase "$next"
}

_p9c0_cleanup_load_sealed_identity() {
    local values key value users=0 groups=0 uids=0 gids=0
    values="$(_p9c0_per_run_root)/values.rendered"
    _p9c0_enforce_root_owned_file "$values" "600" "0" "0" \
        || _p9c0_cleanup_die "values.rendered authority rejected"
    P9C0_SEALED_USER=""
    P9C0_SEALED_GROUP=""
    P9C0_SEALED_UID=""
    P9C0_SEALED_GID=""
    while IFS='=' read -r key value; do
        case "$key" in
            unit_user) P9C0_SEALED_USER="$value"; users=$((users + 1)) ;;
            unit_group) P9C0_SEALED_GROUP="$value"; groups=$((groups + 1)) ;;
            unit_uid) P9C0_SEALED_UID="$value"; uids=$((uids + 1)) ;;
            unit_gid) P9C0_SEALED_GID="$value"; gids=$((gids + 1)) ;;
        esac
    done < "$values"
    [[ $users -eq 1 && $groups -eq 1 && $uids -eq 1 && $gids -eq 1 ]] \
        || _p9c0_cleanup_die "values.rendered identity fields missing or duplicate"
    [[ "$P9C0_SEALED_USER" == "$P9C0_UNIT_USER" && \
       "$P9C0_SEALED_GROUP" == "$P9C0_UNIT_GROUP" ]] \
        || _p9c0_cleanup_die "caller identity differs from sealed identity"
    [[ "$P9C0_SEALED_UID" =~ ^[0-9]+$ && "$P9C0_SEALED_GID" =~ ^[0-9]+$ ]] \
        || _p9c0_cleanup_die "sealed identity is non-numeric"
    P9C0_UNIT_UID="$P9C0_SEALED_UID"
    P9C0_UNIT_GID="$P9C0_SEALED_GID"
    _p9c0_enforce_unit_identity "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" \
        "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" \
        "$(_p9c0_isolation_db_path)" "$P9C0_PROD_DB"
}

_p9c0_cleanup_recheck_state() {
    local prefix run_root sub
    prefix="$(_p9c0_controller_state_prefix)"
    run_root="$(_p9c0_per_run_root)"
    _p9c0_assert_state_prefix_authority "$prefix" \
        || _p9c0_cleanup_die "state prefix is not fixed production namespace"
    _p9c0_assert_state_prefix_resolved "$prefix" \
        || _p9c0_cleanup_die "state prefix resolved authority rejected"
    _p9c0_enforce_root_owned_dir "$prefix" "755" "0" "0" \
        || _p9c0_cleanup_die "state prefix owner/mode rejected"
    _p9c0_enforce_root_owned_dir "$run_root" "750" "0" "$P9C0_UNIT_GID" \
        || _p9c0_cleanup_die "per-run root owner/mode rejected"
    for sub in control lock ledger evidence; do
        _p9c0_enforce_root_owned_dir "$run_root/$sub" "700" "0" "0" \
            || _p9c0_cleanup_die "root subdirectory authority rejected: $sub"
    done
    for sub in db work harness context; do
        _p9c0_enforce_root_owned_dir "$run_root/$sub" "700" \
            "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" \
            || _p9c0_cleanup_die "unit subdirectory authority rejected: $sub"
    done
    _p9c0_enforce_root_owned_file "$(_p9c0_ledger_path)" "600" "0" "0" \
        || _p9c0_cleanup_die "ledger authority rejected"
    _p9c0_enforce_root_owned_file "$(_p9c0_intake_record_path)" "600" "0" "0" \
        || _p9c0_cleanup_die "intake authority rejected"
    _p9c0_reject_unknown_run_entries
}

_p9c0_cleanup_value_once() {
    local file="$1" key="$2" count
    count="$(grep -c "^${key}=" "$file" 2>/dev/null || true)"
    [[ "$count" == "1" ]] || return 1
    sed -n "s/^${key}=//p" "$file"
}

_p9c0_cleanup_recheck_linked_states() {
    local primary="$P9C0_RUN_ID" run_id saved_run run_root values expected_db linked_runs
    local sealed_user sealed_group sealed_uid sealed_gid sealed_db
    saved_run="$P9C0_RUN_ID"
    linked_runs="$(_p9c0_linked_run_ids "$primary")" \
        || _p9c0_cleanup_die "linked-run state authority rejected"
    while IFS= read -r run_id; do
        P9C0_RUN_ID="$run_id"
        run_root="$(_p9c0_per_run_root)"
        values="$run_root/values.rendered"
        expected_db="$(_p9c0_controller_state_prefix)/$primary/db/coord.sqlite3"
        _p9c0_enforce_root_owned_dir "$run_root" "750" "0" "$P9C0_UNIT_GID" \
            || _p9c0_cleanup_die "linked run root authority rejected: $run_id"
        local sub
        for sub in control lock ledger evidence; do
            _p9c0_enforce_root_owned_dir "$run_root/$sub" "700" "0" "0" \
                || _p9c0_cleanup_die "linked root subdirectory rejected: $run_id/$sub"
        done
        for sub in db work harness context; do
            _p9c0_enforce_root_owned_dir "$run_root/$sub" "700" \
                "$P9C0_UNIT_UID" "$P9C0_UNIT_GID" \
                || _p9c0_cleanup_die "linked unit subdirectory rejected: $run_id/$sub"
        done
        _p9c0_enforce_root_owned_file "$values" "600" "0" "0" \
            || _p9c0_cleanup_die "linked values authority rejected: $run_id"
        sealed_user="$(_p9c0_cleanup_value_once "$values" unit_user)" \
            || _p9c0_cleanup_die "linked unit_user authority rejected: $run_id"
        sealed_group="$(_p9c0_cleanup_value_once "$values" unit_group)" \
            || _p9c0_cleanup_die "linked unit_group authority rejected: $run_id"
        sealed_uid="$(_p9c0_cleanup_value_once "$values" unit_uid)" \
            || _p9c0_cleanup_die "linked unit_uid authority rejected: $run_id"
        sealed_gid="$(_p9c0_cleanup_value_once "$values" unit_gid)" \
            || _p9c0_cleanup_die "linked unit_gid authority rejected: $run_id"
        sealed_db="$(_p9c0_cleanup_value_once "$values" coord_db)" \
            || _p9c0_cleanup_die "linked coord_db authority rejected: $run_id"
        [[ "$sealed_user" == "$P9C0_UNIT_USER" && \
           "$sealed_group" == "$P9C0_UNIT_GROUP" && \
           "$sealed_uid" == "$P9C0_UNIT_UID" && \
           "$sealed_gid" == "$P9C0_UNIT_GID" && \
           "$sealed_db" == "$expected_db" ]] \
            || _p9c0_cleanup_die "linked sealed identity/DB mismatch: $run_id"
        _p9c0_reject_unknown_run_entries
    done <<< "$linked_runs"
    P9C0_RUN_ID="$saved_run"
}

_p9c0_cleanup_collect_units() {
    local line unit agent expected seen=" " run_id ledger linked_runs
    P9C0_CLEANUP_UNITS=()
    P9C0_CLEANUP_UNIT_RUNS=()
    linked_runs="$(_p9c0_linked_run_ids "$P9C0_RUN_ID")" \
        || _p9c0_cleanup_die "linked-run authority rejected"
    while IFS= read -r run_id; do
        ledger="$(_p9c0_controller_state_prefix)/$run_id/ledger/events.jsonl"
        [[ -f "$ledger" && ! -L "$ledger" ]] \
            || _p9c0_cleanup_die "linked ledger missing or unsafe: $run_id"
        while IFS= read -r line; do
            case "$line" in
                "unit "*) unit="${line#unit }" ;;
                unit=*) unit="${line#unit=}" ;;
                *) continue ;;
            esac
            unit="${unit%% *}"
            expected=""
            for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
                [[ "$unit" == "$agent-$run_id.service" ]] && expected="$unit"
            done
            [[ -n "$expected" ]] \
                || _p9c0_cleanup_die "ledger contains unauthorized unit authority: $unit"
            case "$seen" in *" $expected "*)
                _p9c0_cleanup_die "ledger contains duplicate unit authority: $expected" ;;
            esac
            P9C0_CLEANUP_UNITS+=("$expected")
            P9C0_CLEANUP_UNIT_RUNS+=("$run_id")
            seen="$seen$expected "
        done < "$ledger"
    done <<< "$linked_runs"
}

_p9c0_cleanup_agent_for_unit() {
    local unit="$1" run_id="${2:-$P9C0_RUN_ID}" agent
    for agent in "${P9C0_AGENT_ALLOWLIST[@]}"; do
        [[ "$unit" == "$agent-$run_id.service" ]] && {
            printf '%s\n' "$agent"
            return 0
        }
    done
    return 1
}

_p9c0_real_cleanup_helper() {
    local operation="$1" agent="$2" run_id="${3:-$P9C0_RUN_ID}"
    "$P9C0_CLEANUP_HELPER" "$operation" \
        --state-root "$P9C0_PROD_STATE_PREFIX" \
        --run-id "$run_id" \
        --agent-id "$agent"
}

_p9c0_cleanup_helper() { _p9c0_real_cleanup_helper "$@"; }

_p9c0_cleanup_quiesce_units() {
    local unit agent output active run_id index ledger
    _p9c0_cleanup_collect_units
    for index in "${!P9C0_CLEANUP_UNITS[@]}"; do
        unit="${P9C0_CLEANUP_UNITS[$index]}"
        run_id="${P9C0_CLEANUP_UNIT_RUNS[$index]}"
        agent="$(_p9c0_cleanup_agent_for_unit "$unit" "$run_id")" \
            || _p9c0_cleanup_die "cannot map exact unit to agent: $unit"
        output="$(_p9c0_cleanup_helper status "$agent" "$run_id" 2>&1)" \
            || _p9c0_cleanup_die "helper status failed for $unit: $output"
        active="$(printf '%s\n' "$output" | sed -n 's/^ActiveState=//p')"
        [[ -n "$active" ]] || _p9c0_cleanup_die "helper status lacks ActiveState for $unit"
        if [[ "$active" != "inactive" && "$active" != "failed" ]]; then
            _p9c0_cleanup_helper stop "$agent" "$run_id" >/dev/null \
                || _p9c0_cleanup_die "helper stop failed for $unit"
        fi
        output="$(_p9c0_cleanup_helper status "$agent" "$run_id" 2>&1)" \
            || _p9c0_cleanup_die "post-stop helper status failed for $unit: $output"
        active="$(printf '%s\n' "$output" | sed -n 's/^ActiveState=//p')"
        [[ "$active" == "inactive" || "$active" == "failed" ]] \
            || _p9c0_cleanup_die "unit is not inactive after exact stop: $unit"
        ledger="$(_p9c0_controller_state_prefix)/$run_id/ledger/events.jsonl"
        grep -Fqx -- "cgroup-empty unit=$unit" "$ledger" \
            || _p9c0_cleanup_die "cgroup-empty proof missing for $unit"
    done
}

_p9c0_real_cleanup_query_counts() {
    local db="$1"
    python3 - "$db" <<'PY'
import pathlib, sqlite3, sys

db = pathlib.Path(sys.argv[1]).resolve()
uri = db.as_uri() + "?mode=ro"
conn = sqlite3.connect(uri, uri=True)
executor_source = "p9-3c0-fixture-executors"
capacity_source = "p9-3c0-fixture-capacity"
queries = {
    "active_leases": "SELECT COUNT(*) FROM execution_attempt_leases WHERE status='active'",
    "pending_running": "SELECT COUNT(*) FROM jobs WHERE status IN ('pending','running')",
    "capacity_refs": """SELECT COUNT(*) FROM execution_attempt_leases
        WHERE status='active' AND capacity_policy_id IN
        (SELECT capacity_policy_id FROM executor_capacity_policies WHERE source_id=?)""",
    "bindings": "SELECT COUNT(*) FROM executor_instance_bindings WHERE source_id=? AND enabled=1",
    "definitions": "SELECT COUNT(*) FROM executor_definitions WHERE source_id=?",
    "policies": "SELECT COUNT(*) FROM executor_capacity_policies WHERE source_id=?",
}
values = {}
values["active_leases"] = conn.execute(queries["active_leases"]).fetchone()[0]
values["pending_running"] = conn.execute(queries["pending_running"]).fetchone()[0]
values["capacity_refs"] = conn.execute(queries["capacity_refs"], (capacity_source,)).fetchone()[0]
values["bindings"] = conn.execute(queries["bindings"], (executor_source,)).fetchone()[0]
values["definitions"] = conn.execute(queries["definitions"], (executor_source,)).fetchone()[0]
values["policies"] = conn.execute(queries["policies"], (capacity_source,)).fetchone()[0]
print(" ".join(f"{key}={values[key]}" for key in (
    "active_leases", "pending_running", "capacity_refs",
    "bindings", "definitions", "policies")))
PY
}

_p9c0_cleanup_query_counts() {
    _p9c0_real_cleanup_query_counts "$(_p9c0_isolation_db_path)"
}

_p9c0_cleanup_parse_counts() {
    local record="$1" f1 f2 f3 f4 f5 f6 extra
    read -r f1 f2 f3 f4 f5 f6 extra <<< "$record"
    [[ -z "${extra:-}" ]] || _p9c0_cleanup_die "count record has extra fields"
    [[ "$f1" =~ ^active_leases=([0-9]+)$ ]] || _p9c0_cleanup_die "count record active_leases invalid"
    P9C0_COUNT_ACTIVE="${BASH_REMATCH[1]}"
    [[ "$f2" =~ ^pending_running=([0-9]+)$ ]] || _p9c0_cleanup_die "count record pending_running invalid"
    P9C0_COUNT_PENDING="${BASH_REMATCH[1]}"
    [[ "$f3" =~ ^capacity_refs=([0-9]+)$ ]] || _p9c0_cleanup_die "count record capacity_refs invalid"
    P9C0_COUNT_CAPACITY_REFS="${BASH_REMATCH[1]}"
    [[ "$f4" =~ ^bindings=([0-9]+)$ ]] || _p9c0_cleanup_die "count record bindings invalid"
    P9C0_COUNT_BINDINGS="${BASH_REMATCH[1]}"
    [[ "$f5" =~ ^definitions=([0-9]+)$ ]] || _p9c0_cleanup_die "count record definitions invalid"
    P9C0_COUNT_DEFINITIONS="${BASH_REMATCH[1]}"
    [[ "$f6" =~ ^policies=([0-9]+)$ ]] || _p9c0_cleanup_die "count record policies invalid"
    P9C0_COUNT_POLICIES="${BASH_REMATCH[1]}"
}

_p9c0_cleanup_refresh_counts() {
    local record
    record="$(_p9c0_cleanup_query_counts)" \
        || _p9c0_cleanup_die "isolated read-only count query failed"
    [[ -n "$record" && "$(printf '%s\n' "$record" | wc -l | tr -d ' ')" == "1" ]] \
        || _p9c0_cleanup_die "isolated count query is empty or multiline"
    _p9c0_cleanup_parse_counts "$record"
}

_p9c0_real_cleanup_latest_expiry() {
    local expected_count="$1"; shift
    python3 - "$expected_count" "$@" <<'PY'
import re, sys

active = {}
terminal = set()
for path in sys.argv[2:]:
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        match = re.fullmatch(r"lease-active lease_id=([^ ]+) expires_at=([^ ]+)", line)
        if match:
            if match.group(1) in active:
                raise SystemExit("duplicate lease-active authority")
            active[match.group(1)] = match.group(2)
            continue
        match = re.fullmatch(r"lease-terminal lease_id=([^ ]+)", line)
        if match:
            terminal.add(match.group(1))
remaining = {key: value for key, value in active.items() if key not in terminal}
if len(remaining) != int(sys.argv[1]):
    raise SystemExit("active lease ledger/count mismatch")
if not remaining:
    raise SystemExit("no active expiry authority")
print(max(remaining.values()))
PY
}

_p9c0_cleanup_latest_expiry() {
    local expected="$1" run_id linked_runs
    local ledgers=()
    linked_runs="$(_p9c0_linked_run_ids "$P9C0_RUN_ID")" \
        || _p9c0_cleanup_die "linked-run lease authority rejected"
    while IFS= read -r run_id; do
        ledgers+=("$(_p9c0_controller_state_prefix)/$run_id/ledger/events.jsonl")
    done <<< "$linked_runs"
    _p9c0_real_cleanup_latest_expiry "$expected" "${ledgers[@]}"
}

_p9c0_real_cleanup_wait_past_expiry() {
    python3 - "$1" <<'PY'
import datetime as dt, sys, time

raw = sys.argv[1]
expiry = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
if expiry.tzinfo is None:
    raise SystemExit("expiry lacks timezone")
while dt.datetime.now(dt.timezone.utc) <= expiry:
    time.sleep(min(1.0, max(0.01, (expiry - dt.datetime.now(dt.timezone.utc)).total_seconds() + 0.01)))
PY
}

_p9c0_cleanup_wait_past_expiry() { _p9c0_real_cleanup_wait_past_expiry "$@"; }

_p9c0_cleanup_require_zero_inflight() {
    _p9c0_cleanup_refresh_counts
    [[ "$P9C0_COUNT_ACTIVE" -eq 0 && "$P9C0_COUNT_PENDING" -eq 0 ]] \
        || _p9c0_cleanup_die "active lease or pending/running job survives cleanup gate"
}

_p9c0_cleanup_expire_and_reap_if_needed() {
    local expiry
    _p9c0_cleanup_refresh_counts
    if [[ "$P9C0_COUNT_ACTIVE" -gt 0 ]]; then
        expiry="$(_p9c0_cleanup_latest_expiry "$P9C0_COUNT_ACTIVE")" \
            || _p9c0_cleanup_die "active lease expiry authority rejected"
        _p9c0_cleanup_wait_past_expiry "$expiry" \
            || _p9c0_cleanup_die "wait past recorded expiry failed"
        _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
            runtime job lease reap \
            || _p9c0_cleanup_die "isolated lease reap failed"
        _p9c0_ledger_append "cleanup-reap expires_at=$expiry"
    fi
    _p9c0_cleanup_require_zero_inflight
}

_p9c0_cleanup_authorize_catalog() {
    local stage="$1" path="$2" expected_path stat_line nlink uid gid mode sha expected count
    case "$stage" in
        executor-v3-disabled) expected_path="$P9C0_EXECUTOR_V3" ;;
        capacity-v2-empty) expected_path="$P9C0_CAPACITY_V2" ;;
        executor-v4-empty) expected_path="$P9C0_EXECUTOR_V4" ;;
        *) _p9c0_cleanup_die "unknown catalog stage: $stage" ;;
    esac
    [[ "$path" == "$expected_path" && "$path" == /* ]] \
        || _p9c0_cleanup_die "catalog path is not fixed authority: $stage"
    [[ -f "$path" && ! -L "$path" ]] \
        || _p9c0_cleanup_die "catalog authority missing or unsafe: $stage"
    [[ "$(_p9c0_realpath "$path")" == "$path" ]] \
        || _p9c0_cleanup_die "catalog authority resolves through alias: $stage"
    stat_line="$(_p9c0_stat_file "$path")" \
        || _p9c0_cleanup_die "catalog stat failed: $stage"
    IFS=: read -r _ _ _ nlink uid gid mode <<< "$stat_line"
    [[ "$nlink" == "1" && "$uid" =~ ^[0-9]+$ && "$gid" =~ ^[0-9]+$ ]] \
        || _p9c0_cleanup_die "catalog owner/link authority rejected: $stage"
    [[ "$uid" != "$P9C0_UNIT_UID" ]] \
        || _p9c0_cleanup_die "catalog authority is owned by fixture unit user: $stage"
    [[ "$mode" == "600" || "$mode" == "644" ]] \
        || _p9c0_cleanup_die "catalog mode authority rejected: $stage"
    sha="$(_p9c0_sha256_file "$path")" \
        || _p9c0_cleanup_die "catalog SHA failed: $stage"
    expected="catalog-authority stage=$stage path=$path stat=$stat_line sha256=$sha"
    count="$(grep -Fxc -- "$expected" "$(_p9c0_ledger_path)" 2>/dev/null || true)"
    [[ "$count" == "1" ]] \
        || _p9c0_cleanup_die "catalog ledger authority missing or duplicate: $stage"
}

_p9c0_cleanup_sync_executor() {
    local stage="$1" path="$2"
    _p9c0_cleanup_authorize_catalog "$stage" "$path"
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        runtime executor sync --source "$path"
}

_p9c0_cleanup_sync_capacity() {
    local stage="$1" path="$2"
    _p9c0_cleanup_authorize_catalog "$stage" "$path"
    _p9c0_controller_run_coordinate "$P9C0_UNIT_USER" "$P9C0_UNIT_UID" \
        runtime capacity sync --source "$path"
}

_p9c0_real_cleanup_capture_snapshot() {
    local out
    out="$(_p9c0_per_run_root)/evidence/cleanup-final.json"
    [[ ! -e "$out" && ! -L "$out" ]] || return 0
    python3 - "$(_p9c0_isolation_db_path)" "$P9C0_PROD_DB" "$out" <<'PY'
import hashlib, json, os, pathlib, sqlite3, sys

isolated, production, out = map(pathlib.Path, sys.argv[1:])
def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def fixture_counts(path):
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    ids = ("p9-3c-fixture-e1", "p9-3c-fixture-e2")
    return {
        "agents": conn.execute("SELECT COUNT(*) FROM agents WHERE id IN (?,?)", ids).fetchone()[0],
        "active_leases": conn.execute("SELECT COUNT(*) FROM execution_attempt_leases WHERE status='active'").fetchone()[0],
        "pending_running": conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0],
    }
payload = {
    "isolated_sha256": digest(isolated),
    "production_sha256": digest(production),
    "isolated": fixture_counts(isolated),
    "production": fixture_counts(production),
}
fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
    handle.write("\n")
PY
    _p9c0_chown 0 0 "$out" || return 1
    _p9c0_chmod 0600 "$out" || return 1
}

_p9c0_cleanup_capture_snapshot() { _p9c0_real_cleanup_capture_snapshot; }

_p9c0_real_cleanup_verify_final_residue() {
    python3 - "$(_p9c0_isolation_db_path)" "$P9C0_PROD_DB" <<'PY'
import pathlib, sqlite3, sys
isolated, production = map(pathlib.Path, sys.argv[1:])
ids=("p9-3c-fixture-e1","p9-3c-fixture-e2")
def ro(path):
    conn=sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True)
    conn.row_factory=sqlite3.Row
    return conn
c=ro(isolated)
agents=[tuple(x) for x in c.execute("SELECT id,client_type FROM agents ORDER BY id")]
if agents != [(ids[0],"agentd"),(ids[1],"agentd")]: raise SystemExit(f"final dormant agents mismatch: {agents}")
runners=[tuple(x) for x in c.execute("SELECT id,runner_type FROM runner_profiles ORDER BY id")]
if runners != [(ids[0],"agentd"),(ids[1],"agentd")]: raise SystemExit(f"final dormant runners mismatch: {runners}")
if [tuple(x) for x in c.execute("SELECT source_id,source_version FROM executor_catalog_sources")] != [("p9-3c0-fixture-executors",4)]: raise SystemExit("final executor source is not v4")
if [tuple(x) for x in c.execute("SELECT source_id,source_version FROM executor_capacity_sources")] != [("p9-3c0-fixture-capacity",2)]: raise SystemExit("final capacity source is not v2")
for table in ("executor_definitions","executor_instance_bindings","executor_capacity_policies"):
    if c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] != 0: raise SystemExit(f"final {table} not empty")
if c.execute("SELECT COUNT(*) FROM execution_attempt_leases WHERE status='active'").fetchone()[0] != 0: raise SystemExit("final active lease survives")
if c.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('pending','running')").fetchone()[0] != 0: raise SystemExit("final inflight job survives")
statuses=[tuple(x) for x in c.execute("SELECT status,COUNT(*) FROM jobs GROUP BY status ORDER BY status")]
if statuses != [("done",2),("timed_out",1)]: raise SystemExit(f"final job residue mismatch: {statuses}")
leases=[tuple(x) for x in c.execute("SELECT status,COUNT(*) FROM execution_attempt_leases GROUP BY status ORDER BY status")]
if leases != [("expired",2),("released",2)]: raise SystemExit(f"final lease residue mismatch: {leases}")
p=ro(production); ph=','.join('?' for _ in ids)
checks=(
    p.execute(f"SELECT COUNT(*) FROM agents WHERE id IN ({ph})",ids).fetchone()[0],
    p.execute(f"SELECT COUNT(*) FROM runner_profiles WHERE id IN ({ph})",ids).fetchone()[0],
    p.execute(f"SELECT COUNT(*) FROM jobs WHERE assigned_agent IN ({ph})",ids).fetchone()[0],
    p.execute(f"SELECT COUNT(*) FROM execution_attempt_leases WHERE agent_id IN ({ph})",ids).fetchone()[0],
)
if any(checks): raise SystemExit(f"production fixture residue appeared: {checks}")
PY
}
_p9c0_cleanup_verify_final_residue() { _p9c0_real_cleanup_verify_final_residue; }

_p9c0_cleanup_run_locked() {
    local current unit agent index run_id
    _p9c0_cleanup_recheck_state
    _p9c0_cleanup_recheck_linked_states
    if [[ -e "$(_p9c0_cleanup_phase_path)" || -L "$(_p9c0_cleanup_phase_path)" ]]; then
        current="$(_p9c0_cleanup_current_phase)" \
            || _p9c0_cleanup_die "cleanup phase read failed"
    else
        current=""
    fi
    if [[ -z "$current" ]]; then
        [[ "$(cat "$(_p9c0_intake_record_path)")" == "intake=$P9C0_INTAKE_FROZEN" ]] \
            || _p9c0_record_intake "$P9C0_INTAKE_FROZEN"
        _p9c0_cleanup_record_phase freeze
        current=freeze
    fi

    if [[ "$current" == "freeze" ]]; then
        _p9c0_cleanup_quiesce_units
        _p9c0_cleanup_expire_and_reap_if_needed
        _p9c0_cleanup_advance freeze units-quiescent
        current=units-quiescent
    fi
    if [[ "$current" == "units-quiescent" ]]; then
        _p9c0_cleanup_require_zero_inflight
        _p9c0_cleanup_sync_executor executor-v3-disabled "$P9C0_EXECUTOR_V3" \
            || _p9c0_cleanup_die "executor v3 disabled sync failed"
        _p9c0_cleanup_refresh_counts
        [[ "$P9C0_COUNT_ACTIVE" -eq 0 && "$P9C0_COUNT_PENDING" -eq 0 && \
           "$P9C0_COUNT_BINDINGS" -eq 0 ]] \
            || _p9c0_cleanup_die "executor v3 postcondition failed"
        _p9c0_cleanup_advance units-quiescent executor-v3-disabled
        current=executor-v3-disabled
    fi
    if [[ "$current" == "executor-v3-disabled" ]]; then
        _p9c0_cleanup_require_zero_inflight
        [[ "$P9C0_COUNT_CAPACITY_REFS" -eq 0 ]] \
            || _p9c0_cleanup_die "active lease still references fixture capacity"
        _p9c0_cleanup_sync_capacity capacity-v2-empty "$P9C0_CAPACITY_V2" \
            || _p9c0_cleanup_die "capacity v2 empty sync failed"
        _p9c0_cleanup_refresh_counts
        [[ "$P9C0_COUNT_ACTIVE" -eq 0 && "$P9C0_COUNT_PENDING" -eq 0 && \
           "$P9C0_COUNT_CAPACITY_REFS" -eq 0 && "$P9C0_COUNT_POLICIES" -eq 0 ]] \
            || _p9c0_cleanup_die "capacity v2 postcondition failed"
        _p9c0_cleanup_advance executor-v3-disabled capacity-v2-empty
        current=capacity-v2-empty
    fi
    if [[ "$current" == "capacity-v2-empty" ]]; then
        _p9c0_cleanup_require_zero_inflight
        [[ "$P9C0_COUNT_BINDINGS" -eq 0 && "$P9C0_COUNT_POLICIES" -eq 0 ]] \
            || _p9c0_cleanup_die "executor v4 precondition failed"
        _p9c0_cleanup_sync_executor executor-v4-empty "$P9C0_EXECUTOR_V4" \
            || _p9c0_cleanup_die "executor v4 empty sync failed"
        _p9c0_cleanup_refresh_counts
        [[ "$P9C0_COUNT_ACTIVE" -eq 0 && "$P9C0_COUNT_PENDING" -eq 0 && \
           "$P9C0_COUNT_CAPACITY_REFS" -eq 0 && "$P9C0_COUNT_BINDINGS" -eq 0 && \
           "$P9C0_COUNT_DEFINITIONS" -eq 0 && "$P9C0_COUNT_POLICIES" -eq 0 ]] \
            || _p9c0_cleanup_die "executor v4 final catalog postcondition failed"
        _p9c0_cleanup_advance capacity-v2-empty executor-v4-empty
        current=executor-v4-empty
    fi
    if [[ "$current" == "executor-v4-empty" ]]; then
        _p9c0_cleanup_collect_units
        for index in "${!P9C0_CLEANUP_UNITS[@]}"; do
            unit="${P9C0_CLEANUP_UNITS[$index]}"
            run_id="${P9C0_CLEANUP_UNIT_RUNS[$index]}"
            agent="$(_p9c0_cleanup_agent_for_unit "$unit" "$run_id")" \
                || _p9c0_cleanup_die "cannot map cleanup unit: $unit"
            _p9c0_cleanup_helper cleanup "$agent" "$run_id" >/dev/null \
                || _p9c0_cleanup_die "helper exact cleanup failed for $unit"
        done
        _p9c0_cleanup_advance executor-v4-empty units-cleaned
        current=units-cleaned
    fi
    if [[ "$current" == "units-cleaned" ]]; then
        _p9c0_cleanup_require_zero_inflight
        _p9c0_cleanup_verify_final_residue \
            || _p9c0_cleanup_die "final isolated/production residue verification failed"
        _p9c0_cleanup_capture_snapshot \
            || _p9c0_cleanup_die "final read-only snapshot failed"
        _p9c0_cleanup_advance units-cleaned snapshot-retained
        current=snapshot-retained
    fi
    if [[ "$current" == "snapshot-retained" ]]; then
        _p9c0_cleanup_advance snapshot-retained "done"
        current="done"
    fi
    [[ "$current" == "done" ]] || _p9c0_cleanup_die "cleanup stopped at unknown phase"
    printf 'p9-3c0 cleanup complete run=%s\n' "$P9C0_RUN_ID"
}

_p9c0_cleanup_controller() {
    P9C0_RUN_ID="$P9C0_ARG_RUN_ID"
    P9C0_UNIT_USER="$P9C0_ARG_UNIT_USER"
    P9C0_UNIT_GROUP="$P9C0_ARG_UNIT_GROUP"
    _p9c0_validate_run_id "$P9C0_RUN_ID" \
        || _p9c0_cleanup_die "invalid run id: $P9C0_RUN_ID"
    [[ "$(_p9c0_euid)" == "0" ]] || _p9c0_cleanup_die "cleanup controller must run as root"
    [[ "$P9C0_UNIT_USER" != "root" && "$P9C0_UNIT_GROUP" != "root" ]] \
        || _p9c0_cleanup_die "unit user/group cannot be root"
    _p9c0_cleanup_load_sealed_identity
    _p9c0_cleanup_recheck_state
    _p9c0_with_run_lock _p9c0_cleanup_run_locked
}

main() {
    P9C0_ARG_RUN_ID=""
    P9C0_ARG_UNIT_USER=""
    P9C0_ARG_UNIT_GROUP=""
    local command="${1:-}"
    shift || true
    [[ "$command" == "cleanup" ]] || _p9c0_cleanup_usage
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --run-id) [[ $# -ge 2 ]] || _p9c0_cleanup_usage; P9C0_ARG_RUN_ID="$2"; shift 2 ;;
            --unit-user) [[ $# -ge 2 ]] || _p9c0_cleanup_usage; P9C0_ARG_UNIT_USER="$2"; shift 2 ;;
            --unit-group) [[ $# -ge 2 ]] || _p9c0_cleanup_usage; P9C0_ARG_UNIT_GROUP="$2"; shift 2 ;;
            *) _p9c0_cleanup_usage ;;
        esac
    done
    [[ -n "$P9C0_ARG_RUN_ID" && -n "$P9C0_ARG_UNIT_USER" && -n "$P9C0_ARG_UNIT_GROUP" ]] \
        || _p9c0_cleanup_usage
    trap '_p9c0_on_exit $?' EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM
    _p9c0_cleanup_controller
    trap - EXIT HUP INT TERM
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
