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

_p9c0_real_systemd_analyze() {
    systemd-analyze "$@"
}

_p9c0_real_python_normalize() {
    # Argument form: <normalizer-name> <value> <expected>
    # Normalizer names: runtime-max-usec, timeout-stop-usec, kill-mode,
    # umask, bool, protect-system, read-write-paths,
    # restrict-address-families, ip-address-deny.
    local name="$1" value="$2" expected="$3"
    "${P9C0_PYTHON:-python3}" - "$name" "$value" "$expected" <<'PYEOF'
import re, sys

name, value, expected = sys.argv[1], sys.argv[2], sys.argv[3]


def parse_usec_duration(raw):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Pure microsecond integer (systemd canonical).
    if s.isdigit():
        return int(s)
    # Human duration: e.g. "5min", "30s", "1h 30min", "500ms".
    total = 0
    pos = 0
    pattern = re.compile(r'(?P<num>\d+)\s*(?P<unit>us|usec|ms|msec|s|sec|seconds|second|min|minutes|minute|h|hours|hour)?')
    matched_any = False
    for m in pattern.finditer(s):
        if m.start() != pos:
            return None
        pos = m.end()
        matched_any = True
        n = int(m.group('num'))
        unit = m.group('unit') or 'us'
        if unit in ('us', 'usec'):
            total += n
        elif unit in ('ms', 'msec'):
            total += n * 1000
        elif unit in ('s', 'sec', 'seconds', 'second'):
            total += n * 1_000_000
        elif unit in ('min', 'minutes', 'minute'):
            total += n * 60_000_000
        elif unit in ('h', 'hours', 'hour'):
            total += n * 3_600_000_000
        else:
            sys.stderr.write(f'normalize: unknown duration unit: {unit}\n')
            sys.exit(2)
    if not matched_any or pos != len(s):
        return None
    return total


if name == 'runtime-max-usec':
    got = parse_usec_duration(value)
    if got is None:
        sys.stderr.write(f'normalize: cannot parse RuntimeMaxUSec: {value!r}\n')
        sys.exit(2)
    if got != int(expected):
        sys.stderr.write(f'normalize: RuntimeMaxUSec mismatch {got} != {expected}\n')
        sys.exit(2)
elif name == 'timeout-stop-usec':
    got = parse_usec_duration(value)
    if got is None:
        sys.stderr.write(f'normalize: cannot parse TimeoutStopUSec: {value!r}\n')
        sys.exit(2)
    if got != int(expected):
        sys.stderr.write(f'normalize: TimeoutStopUSec mismatch {got} != {expected}\n')
        sys.exit(2)
elif name == 'kill-mode':
    if str(value).strip() != str(expected):
        sys.stderr.write(f'normalize: KillMode mismatch {value!r} != {expected!r}\n')
        sys.exit(2)
elif name == 'umask':
    raw = str(value).strip()
    if not re.fullmatch(r'0[0-7]{3,4}', raw):
        sys.stderr.write(f'normalize: UMask not octal: {raw!r}\n')
        sys.exit(2)
    if raw != str(expected):
        sys.stderr.write(f'normalize: UMask mismatch {raw} != {expected}\n')
        sys.exit(2)
elif name == 'bool':
    norm = str(value).strip().lower()
    truthy = norm in ('yes', 'true', 'on', '1')
    falsy = norm in ('no', 'false', 'off', '0')
    if not (truthy or falsy):
        sys.stderr.write(f'normalize: unknown bool encoding: {value!r}\n')
        sys.exit(2)
    if expected == 'yes' and not truthy:
        sys.stderr.write(f'normalize: bool {value!r} != yes\n')
        sys.exit(2)
    if expected == 'no' and not falsy:
        sys.stderr.write(f'normalize: bool {value!r} != no\n')
        sys.exit(2)
elif name == 'protect-system':
    raw = str(value).strip().lower()
    # Canonical systemd 255 display: yes | no | strict | full | auto
    if raw != str(expected).strip().lower():
        sys.stderr.write(f'normalize: ProtectSystem mismatch {raw} != {expected}\n')
        sys.exit(2)
elif name == 'read-write-paths':
    # Expected is the single canonical state root absolute path.
    expected_root = str(expected)
    tokens = [t for t in str(value).strip().split() if t]
    if len(tokens) != 1:
        sys.stderr.write(f'normalize: ReadWritePaths must be exactly one path: {value!r}\n')
        sys.exit(2)
    import os
    canonical = os.path.realpath(tokens[0])
    expected_canonical = os.path.realpath(expected_root)
    if canonical != expected_canonical:
        sys.stderr.write(f'normalize: ReadWritePaths canonical {canonical} != {expected_canonical}\n')
        sys.exit(2)
elif name == 'restrict-address-families':
    # Must be a positive allow-set containing only AF_UNIX; deny/complement
    # (~ prefix) or any other family is rejected.
    tokens = [t for t in str(value).strip().split() if t]
    if tokens != ['AF_UNIX']:
        sys.stderr.write(f'normalize: RestrictAddressFamilies not AF_UNIX allow-set: {value!r}\n')
        sys.exit(2)
elif name == 'ip-address-deny':
    raw = str(value).strip()
    # Accept "any" or the complete canonical "0.0.0.0/0 ::/0" pair.
    if raw == 'any':
        sys.exit(0)
    tokens = raw.split()
    if sorted(tokens) != ['0.0.0.0/0', '::/0']:
        sys.stderr.write(f'normalize: IPAddressDeny not full IPv4+IPv6: {raw!r}\n')
        sys.exit(2)
elif name == 'unset-environment':
    actual_tokens = [t for t in str(value).strip().split() if t]
    expected_tokens = [t for t in str(expected).split(',') if t]
    if any('*' in t for t in actual_tokens + expected_tokens):
        sys.stderr.write('normalize: UnsetEnvironment contains wildcard\n')
        sys.exit(2)
    if len(actual_tokens) != len(set(actual_tokens)):
        sys.stderr.write('normalize: UnsetEnvironment contains duplicate names\n')
        sys.exit(2)
    if sorted(actual_tokens) != sorted(expected_tokens):
        sys.stderr.write(f'normalize: UnsetEnvironment mismatch {actual_tokens!r} != {expected_tokens!r}\n')
        sys.exit(2)
else:
    sys.stderr.write(f'normalize: unknown normalizer: {name}\n')
    sys.exit(2)

sys.exit(0)
PYEOF
}

_p9c0_real_sha256_file() {
    sha256sum "$1" 2>/dev/null | awk '{print $1}'
}

_p9c0_real_stat_file() {
    # Emits "<device>:<inode>:<size>:<nlink>:<uid>:<gid>:<mode>" for the path.
    stat -c '%d:%i:%s:%h:%u:%g:%a' "$1" 2>/dev/null
}

_p9c0_real_set_owner_group_mode() {
    local path="$1" uid="$2" gid="$3" mode="$4"
    chown "$uid:$gid" "$path" && chmod "$mode" "$path"
}

# Identity seams used by _p9c0_enforce_unit_identity. Each returns the
# numeric id via stdout and exits non-zero if the name does not exist.
# Tests override _p9c0_identity_lookup_user / _p9c0_identity_lookup_group
# without touching real NSS databases.
_p9c0_real_identity_lookup_user() {
    local name="$1"
    id -u "$name" 2>/dev/null
}
_p9c0_real_identity_lookup_group() {
    local name="$1"
    # Prefer getent for portable NSS coverage; fall back to /etc/group parsing.
    if command -v getent >/dev/null 2>&1; then
        getent group "$name" 2>/dev/null | awk -F: 'NR==1{print $3; exit}'
    else
        awk -F: -v n="$name" '$1==n {print $3; exit}' /etc/group 2>/dev/null
    fi
}

_p9c0_date_ms() { _p9c0_real_date_ms; }
_p9c0_systemctl() { _p9c0_real_systemctl "$@"; }
_p9c0_run_systemd_run() { _p9c0_real_run_systemd_run "$@"; }
_p9c0_flock() { _p9c0_real_flock "$@"; }
_p9c0_sleep() { _p9c0_real_sleep "$1"; }
_p9c0_cgroup_procs_path() { _p9c0_real_cgroup_procs_path "$@"; }
_p9c0_read_cgroup_procs() { _p9c0_real_read_cgroup_procs "$1"; }
_p9c0_systemd_analyze() { _p9c0_real_systemd_analyze "$@"; }
_p9c0_python_normalize() { _p9c0_real_python_normalize "$@"; }
_p9c0_sha256_file() { _p9c0_real_sha256_file "$@"; }
_p9c0_stat_file() { _p9c0_real_stat_file "$@"; }
_p9c0_identity_lookup_user() { _p9c0_real_identity_lookup_user "$@"; }
_p9c0_identity_lookup_group() { _p9c0_real_identity_lookup_group "$@"; }
_p9c0_set_owner_group_mode() { _p9c0_real_set_owner_group_mode "$@"; }

_p9c0_lock_file_authority() {
    local lock_file="$1" stat_line nlink uid gid mode
    [[ -f $lock_file && ! -L $lock_file ]] || return 1
    stat_line=$(_p9c0_stat_file "$lock_file") || return 1
    IFS=: read -r _ _ _ nlink uid gid mode <<< "$stat_line"
    [[ $nlink == 1 && $uid == 0 && $gid == 0 && $mode == 600 ]]
}

# ---------------------------------------------------------------------------
# Static constants
# ---------------------------------------------------------------------------

P9C0_AGENT_ALLOWLIST=("p9-3c-fixture-e1" "p9-3c-fixture-e2")
P9C0_PROD_DB="/var/lib/coordinate/coord.sqlite3"
P9C0_PROD_WRAPPER="/usr/local/bin/coord-local"
P9C0_RUN_ID_RE='^[a-z0-9]+(-[a-z0-9]+)*$'
P9C0_MAX_UNITS=2
P9C0_CREDENTIAL_DENYLIST=(
    ANTHROPIC_API_KEY CLAUDE_API_KEY OPENAI_API_KEY CODEX_API_KEY
    KIMI_API_KEY MOONSHOT_API_KEY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
    AWS_SESSION_TOKEN AZURE_OPENAI_API_KEY GOOGLE_API_KEY
    GOOGLE_APPLICATION_CREDENTIALS VERTEX_API_KEY DISCORD_TOKEN KOOK_TOKEN
    HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY
    http_proxy https_proxy all_proxy no_proxy
    MULTINEXUS_DB_ROOT_TOKEN MULTINEXUS_AGENT_REGISTRY_TOKEN
    MULTINEXUS_JWT_SIGNING_KEY MULTINEXUS_PROVIDER_API_KEY
    MULTINEXUS_OAUTH_CLIENT_SECRET
)
P9C0_CREDENTIAL_PREFIXES=(
    ANTHROPIC_ CLAUDE_ OPENAI_ CODEX_ KIMI_ MOONSHOT_
    AWS_ AZURE_ GOOGLE_ VERTEX_ DISCORD_ KOOK_
)

_p9c0_environment_names() { compgen -e; }

_p9c0_collect_unset_environment_names() {
    local name prefix seen=" "
    for name in "${P9C0_CREDENTIAL_DENYLIST[@]}"; do
        [[ "$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ && "$name" != *"*"* ]] || return 1
        case "$seen" in *" $name "*) ;; *) printf '%s\n' "$name"; seen="$seen$name " ;; esac
    done
    while IFS= read -r name; do
        [[ "$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ && "$name" != *"*"* ]] || continue
        for prefix in "${P9C0_CREDENTIAL_PREFIXES[@]}"; do
            if [[ "$name" == "$prefix"* ]]; then
                case "$seen" in *" $name "*) ;; *) printf '%s\n' "$name"; seen="$seen$name " ;; esac
                break
            fi
        done
    done < <(_p9c0_environment_names)
}

_p9c0_join_unset_environment_names() {
    local name joined="" collected
    collected="$(_p9c0_collect_unset_environment_names)" || return 1
    while IFS= read -r name; do
        [[ -n "$name" ]] || continue
        if [[ -n "$joined" ]]; then joined="$joined,$name"; else joined="$name"; fi
    done <<< "$collected"
    [[ -n "$joined" ]] || return 1
    printf '%s\n' "$joined"
}

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
    [[ -n $root ]] || return 1
    [[ -n $path ]] || return 1
    _p9c0_is_absolute_path "$path" || return 1
    _p9c0_is_absolute_path "$root" || return 1
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
# Wrapper manifest authority and ownership matrix
# ---------------------------------------------------------------------------

# P9C0_WRAPPER_MANIFEST_FILENAME lives next to the wrapper and records the
# wrapper root/dev/inode/size/nlink/owner/group/mode/SHA-256 captured at creation.
# The helper refuses symlinks, hard-link counts other than one, wrong owner/group,
# wrong mode, drift on recheck, and unknown entries.
P9C0_WRAPPER_MANIFEST_FILENAME="wrapper.manifest"

# Layout the manifest record. Tab-separated so values with spaces stay parseable.
_p9c0_wrapper_manifest_record() {
    local wrapper="$1"
    local stat_line sha
    stat_line=$(_p9c0_stat_file "$wrapper") || return 1
    sha=$(_p9c0_sha256_file "$wrapper") || return 1
    printf 'wrapper_raw=%s\twrapper_dev_inode_size_nlink_uid_gid_mode=%s\twrapper_sha256=%s\n' \
        "$wrapper" "$stat_line" "$sha"
}

# Compare a current stat/sha line against the expected manifest line. Used by
# both controller recheck (render/start) and agentd self-check before invocation.
_p9c0_validate_wrapper_manifest_match() {
    local wrapper="$1" expected_line="$2"
    local current
    current=$(_p9c0_wrapper_manifest_record "$wrapper") || return 1
    [[ $current == "$expected_line" ]] || {
        printf 'wrapper manifest mismatch: expected=%s current=%s\n' "$expected_line" "$current" >&2
        return 1
    }
}

# Authority gates for the wrapper executable and isolated DB. Called at render
# time and before every controller invocation.
_p9c0_enforce_wrapper_authority() {
    local wrapper="$1" coord_db="$2" state_root="$3"
    local -a errors=()

    [[ -n $wrapper ]] || errors+=("wrapper path empty")
    [[ -n $coord_db ]] || errors+=("coord-db path empty")
    _p9c0_is_absolute_path "$wrapper" || errors+=("wrapper must be absolute")
    _p9c0_is_absolute_path "$coord_db" || errors+=("coord-db must be absolute")

    # Production wrappers/DBs are always refused, even via resolution.
    [[ $wrapper != "$P9C0_PROD_WRAPPER" ]] || errors+=("wrapper is production wrapper")
    [[ $coord_db != "$P9C0_PROD_DB" ]] || errors+=("coord-db is production DB")
    if _p9c0_is_resolved_production_wrapper "$wrapper" 2>/dev/null; then
        errors+=("wrapper resolves to production wrapper")
    fi
    if _p9c0_is_resolved_production_db "$coord_db" 2>/dev/null; then
        errors+=("coord-db resolves to production DB")
    fi

    # Wrapper must be a regular file with one link, no symlink, no traversal.
    [[ -L $wrapper ]] && errors+=("wrapper is a symlink")
    [[ -e $wrapper ]] || errors+=("wrapper missing")
    if [[ -e $wrapper && ! -f $wrapper ]]; then
        errors+=("wrapper is not a regular file")
    fi
    case $wrapper in
        *..*) errors+=("wrapper contains path traversal") ;;
    esac

    # Coord-DB must be an absolute path under the approved state prefix.
    [[ -n $state_root ]] || errors+=("state-root empty")
    if [[ -n $state_root ]] && ! _p9c0_is_under_root "$coord_db" "$state_root"; then
        errors+=("coord-db must be under state-root")
    fi

    if (( ${#errors[@]} > 0 )); then
        local e
        for e in "${errors[@]}"; do
            printf 'wrapper authority: %s\n' "$e" >&2
        done
        return 1
    fi
    return 0
}

# Static check for raw-and-resolved paths + nlink count. Returns 0 if both
# raw and realpath are under the approved prefix and nlink == 1.
_p9c0_wrapper_is_safe_under_prefix() {
    local wrapper="$1" prefix="$2"
    [[ -n $wrapper && -n $prefix ]] || return 1
    _p9c0_is_absolute_path "$wrapper" || return 1
    case $wrapper in
        "$prefix"/*) ;;
        *) return 1 ;;
    esac
    local resolved prefix_resolved
    resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$wrapper" 2>/dev/null) || return 1
    prefix_resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$prefix" 2>/dev/null) || return 1
    case $resolved in
        "$prefix_resolved"/*|"$prefix_resolved") ;;
        *) return 1 ;;
    esac
    local nlink
    nlink=$(_p9c0_stat_file "$wrapper") || return 1
    local link_count
    link_count=$(printf '%s' "$nlink" | awk -F: '{print $4}')
    [[ $link_count == 1 ]] || return 1
}

# Recheck wrapper authority before every controller invocation. Returns 0 on
# pass; ledger entry is the caller's responsibility.
_p9c0_recheck_wrapper_authority() {
    local wrapper="$1" manifest_line="$2"
    _p9c0_validate_wrapper_manifest_match "$wrapper" "$manifest_line"
}

# Detect production DB by resolved path. Symlink/alias/traversal all resolve.
_p9c0_is_resolved_production_db() {
    local db="$1"
    local resolved prod_resolved
    resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$db") || return 1
    prod_resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$P9C0_PROD_DB") || return 1
    [[ $resolved == "$prod_resolved" ]]
}

# Refuse root/unknown identities, require that the requested user/group
# exist on the host with non-zero numeric ids, that the group gid matches
# the wrapper's and manifest's gid exactly, and that the runtime parent
# path is a safe non-symlink directory under the approved prefix.
# The wrapper_path / manifest_path arguments are optional; when supplied,
# gid equality is enforced.
_p9c0_enforce_unit_identity() {
    local user="$1" group="$2" runtime_parent="$3" wrapper_path="${4:-}" manifest_path="${5:-}" approved_prefix="${6:-}"
    local -a errors=()
    local uid="" gid="" wrapper_gid="" manifest_gid=""

    [[ -n $user ]] || errors+=("user empty")
    [[ -n $group ]] || errors+=("group empty")

    if [[ -n $user ]]; then
        [[ $user =~ ^[a-z_][a-z0-9_-]*$ ]] || errors+=("user not a valid name: $user")
        case $user in
            root|0) errors+=("refusing root unit user: $user") ;;
        esac
        uid=$(_p9c0_identity_lookup_user "$user" 2>/dev/null) || errors+=("user does not exist: $user")
        if [[ -n $uid && ! $uid =~ ^[0-9]+$ ]]; then
            errors+=("user uid not numeric: $uid")
            uid=""
        fi
        if [[ -n $uid && $uid -eq 0 ]]; then
            errors+=("refusing zero uid for user: $user")
        fi
    fi
    if [[ -n $group ]]; then
        [[ $group =~ ^[a-z_][a-z0-9_-]*$ ]] || errors+=("group not a valid name: $group")
        case $group in
            root|0) errors+=("refusing root unit group: $group") ;;
        esac
        gid=$(_p9c0_identity_lookup_group "$group" 2>/dev/null) || errors+=("group does not exist: $group")
        if [[ -n $gid && ! $gid =~ ^[0-9]+$ ]]; then
            errors+=("group gid not numeric: $gid")
            gid=""
        fi
        if [[ -n $gid && $gid -eq 0 ]]; then
            errors+=("refusing zero gid for group: $group")
        fi
    fi

    if [[ -n $wrapper_path ]]; then
        local wstat
        wstat=$(_p9c0_stat_file "$wrapper_path" 2>/dev/null) || errors+=("wrapper stat failed: $wrapper_path")
        if [[ -n $wstat ]]; then
            IFS=: read -r _ _ _ _ _ wrapper_gid _ <<< "$wstat"
        fi
    fi
    if [[ -n $manifest_path ]]; then
        local mstat
        mstat=$(_p9c0_stat_file "$manifest_path" 2>/dev/null) || errors+=("manifest stat failed: $manifest_path")
        if [[ -n $mstat ]]; then
            IFS=: read -r _ _ _ _ _ manifest_gid _ <<< "$mstat"
        fi
    fi
    if [[ -n $gid ]]; then
        [[ -z $wrapper_path || -z $wrapper_gid || $gid == "$wrapper_gid" ]] \
            || errors+=("group gid=$gid does not match wrapper gid=$wrapper_gid")
        [[ -z $manifest_path || -z $manifest_gid || $gid == "$manifest_gid" ]] \
            || errors+=("group gid=$gid does not match manifest gid=$manifest_gid")
    fi

    if [[ -n $runtime_parent ]]; then
        _p9c0_is_absolute_path "$runtime_parent" || errors+=("runtime parent must be absolute: $runtime_parent")
        [[ -L $runtime_parent ]] && errors+=("runtime parent is a symlink: $runtime_parent")
        case $runtime_parent in
            *..*) errors+=("runtime parent contains path traversal: $runtime_parent") ;;
        esac
        [[ -n $approved_prefix ]] || errors+=("runtime parent requires approved_prefix")
        if [[ -n $approved_prefix ]]; then
            local rp_resolved prefix_resolved
            rp_resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$runtime_parent" 2>/dev/null) || rp_resolved=""
            prefix_resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$approved_prefix" 2>/dev/null) || prefix_resolved=""
            case $runtime_parent in
                "$approved_prefix") ;;
                "$approved_prefix"/*) ;;
                *) errors+=("runtime parent raw outside approved prefix: $runtime_parent (approved=$approved_prefix)") ;;
            esac
            if [[ -n $rp_resolved && -n $prefix_resolved ]]; then
                case $rp_resolved in
                    "$prefix_resolved") ;;
                    "$prefix_resolved"/*) ;;
                    *) errors+=("runtime parent resolved outside approved prefix: $rp_resolved (approved=$prefix_resolved)") ;;
                esac
            else
                errors+=("runtime parent: failed to resolve approved prefix")
            fi
        fi
    fi
    if (( ${#errors[@]} > 0 )); then
        local e
        for e in "${errors[@]}"; do
            printf 'unit identity: %s\n' "$e" >&2
        done
        return 1
    fi
    return 0
}

# Wrapper manifest must be a root-owned, group-readable 0640 file. The caller
# supplies the manifest path and the canonical expected owner/group. This is
# the owner/group/mode gate at controller creation time.
_p9c0_enforce_wrapper_manifest_owner_mode() {
    local manifest="$1" expected_gid="${2:-}"
    [[ -f $manifest ]] || {
        printf 'wrapper manifest: missing %s\n' "$manifest" >&2
        return 1
    }
    [[ -L $manifest ]] && {
        printf 'wrapper manifest: symlink not allowed %s\n' "$manifest" >&2
        return 1
    }
    local stat_line dev inode size nlink uid gid mode
    stat_line=$(_p9c0_stat_file "$manifest") || return 1
    IFS=: read -r dev inode size nlink uid gid mode <<< "$stat_line"
    [[ $uid == 0 ]] || {
        printf 'wrapper manifest: not root-owned uid=%s\n' "$uid" >&2
        return 1
    }
    [[ $gid =~ ^[0-9]+$ && $gid -ne 0 ]] || {
        printf 'wrapper manifest: group must be non-root gid=%s\n' "$gid" >&2
        return 1
    }
    if [[ -n $expected_gid ]]; then
        [[ $gid == "$expected_gid" ]] || {
            printf 'wrapper manifest: gid=%s does not match unit gid=%s\n' "$gid" "$expected_gid" >&2
            return 1
        }
    fi
    [[ $mode == 640 ]] || {
        printf 'wrapper manifest: mode must be 0640 got=%s\n' "$mode" >&2
        return 1
    }
    [[ $nlink == 1 ]] || {
        printf 'wrapper manifest: hard-link count must be 1 got=%s\n' "$nlink" >&2
        return 1
    }
}

# Wrapper file itself must be root-owned, exact unit-group, mode 0750.
_p9c0_enforce_wrapper_owner_mode() {
    local wrapper="$1"
    local stat_line uid gid mode nlink
    stat_line=$(_p9c0_stat_file "$wrapper") || return 1
    IFS=: read -r dev inode size nlink uid gid mode <<< "$stat_line"
    [[ $uid == 0 ]] || {
        printf 'wrapper: not root-owned uid=%s\n' "$uid" >&2
        return 1
    }
    [[ $gid =~ ^[0-9]+$ && $gid -ne 0 ]] || {
        printf 'wrapper: group must be non-root gid=%s\n' "$gid" >&2
        return 1
    }
    [[ $mode == 750 ]] || {
        printf 'wrapper: mode must be 0750 got=%s\n' "$mode" >&2
        return 1
    }
    [[ $nlink == 1 ]] || {
        printf 'wrapper: hard-link count must be 1 got=%s\n' "$nlink" >&2
        return 1
    }
}

# ---------------------------------------------------------------------------
# Preexisting manifest verify (Package 3 unit-helper slice)
# ---------------------------------------------------------------------------

# Verify the controller-pre-created manifest at $manifest_path before render
# seals it. The helper must not create, overwrite, chmod, or chown the
# manifest; it only reads and checks the bytes the controller placed there.
# On success prints the verified single-line record to stdout so the caller
# can seal it into the values file verbatim.
_p9c0_verify_preexisting_manifest() {
    local manifest="$1" wrapper="$2" unit_gid="$3"
    [[ -n $manifest ]] || { printf 'manifest verify: path empty\n' >&2; return 1; }
    [[ -n $wrapper ]] || { printf 'manifest verify: wrapper empty\n' >&2; return 1; }
    [[ -n $unit_gid ]] || { printf 'manifest verify: unit_gid empty\n' >&2; return 1; }
    [[ -f $manifest ]] || { printf 'manifest verify: missing %s\n' "$manifest" >&2; return 1; }
    [[ -L $manifest ]] && { printf 'manifest verify: symlink not allowed %s\n' "$manifest" >&2; return 1; }
    local content line_count
    content=$(cat "$manifest" 2>/dev/null) || { printf 'manifest verify: read failed %s\n' "$manifest" >&2; return 1; }
    line_count=$(printf '%s\n' "$content" | wc -l | tr -d ' ')
    [[ $line_count == 1 ]] || { printf 'manifest verify: not single line (%s lines) %s\n' "$line_count" "$manifest" >&2; return 1; }
    local live
    live=$(_p9c0_wrapper_manifest_record "$wrapper") || {
        printf 'manifest verify: wrapper record failed %s\n' "$wrapper" >&2
        return 1
    }
    [[ $content == "$live" ]] || {
        printf 'manifest verify: content drift approved=%s current=%s\n' "$content" "$live" >&2
        return 1
    }
    _p9c0_enforce_wrapper_manifest_owner_mode "$manifest" "$unit_gid" || return 1
    printf '%s\n' "$content"
}

# Recheck manifest + wrapper authority before every controller invocation
# (preflight / start). Re-reads the manifest bytes, verifies them against the
# approved record sealed at render time, re-enforces owner/mode/nlink/uid/
# gid, then validates the live wrapper against the same approved record.
# Returns 0 only if every gate passes.
_p9c0_recheck_manifest_authority() {
    local manifest="$1" approved_line="$2" wrapper="$3" expected_gid="$4"
    [[ -n $manifest ]] || { printf 'manifest recheck: path empty\n' >&2; return 1; }
    [[ -n $approved_line ]] || { printf 'manifest recheck: approved_line empty\n' >&2; return 1; }
    [[ -n $wrapper ]] || { printf 'manifest recheck: wrapper empty\n' >&2; return 1; }
    [[ -f $manifest ]] || { printf 'manifest recheck: missing %s\n' "$manifest" >&2; return 1; }
    [[ -L $manifest ]] && { printf 'manifest recheck: symlink not allowed %s\n' "$manifest" >&2; return 1; }
    local content line_count
    content=$(cat "$manifest" 2>/dev/null) || { printf 'manifest recheck: read failed %s\n' "$manifest" >&2; return 1; }
    line_count=$(printf '%s\n' "$content" | wc -l | tr -d ' ')
    [[ $line_count == 1 ]] || { printf 'manifest recheck: not single line (%s lines) %s\n' "$line_count" "$manifest" >&2; return 1; }
    [[ $content == "$approved_line" ]] || {
        printf 'manifest recheck: content drift approved=%s current=%s\n' "$approved_line" "$content" >&2
        return 1
    }
    _p9c0_enforce_wrapper_manifest_owner_mode "$manifest" "$expected_gid" || return 1
    _p9c0_validate_wrapper_manifest_match "$wrapper" "$approved_line" || return 1
}

# ---------------------------------------------------------------------------
# systemd-analyze verify static gate (Package 3)
# ---------------------------------------------------------------------------
# Compose the unit definition file at a fixed state-rooted path
# ($state_dir/systemd.verify.service) that enforces every reviewed
# property the runtime launch uses plus a harmless inert
# ``ExecStart=/bin/true`` so ``systemd-analyze verify`` exercises
# the full parser. The renderer is invoked once at render time;
# preflight/start inspect the retained bytes without rewriting them.
# Mode 0600, root-owned, regular file, never a symlink, never
# ``mktemp``-then-``rm``. Has a fixed name (no mktemp) so cleanup
# can target the exact sealed path, and never escapes the run
# directory.
_p9c0_render_unit_definition() {
    local out="$1" user="$2" group="$3" work_dir="$4" state_root="$5"
    [[ ! -e $out && ! -L $out ]] || return 1
    local rendered_unit="$out"
    local old_umask
    old_umask=$(umask)
    umask 077
    set -o noclobber
    {
        printf '[Unit]\n'
        printf 'Description=P9-3C0 fixture static-verify definition\n'
        printf '[Service]\n'
        printf 'Type=simple\n'
        printf 'ExecStart=/bin/true\n'
        printf 'User=%s\n' "$user"
        printf 'Group=%s\n' "$group"
        printf 'WorkingDirectory=%s\n' "$work_dir"
        printf 'RuntimeMaxSec=300\n'
        printf 'TimeoutStopSec=30\n'
        printf 'KillMode=control-group\n'
        printf 'IPAddressDeny=any\n'
        printf 'RestrictAddressFamilies=AF_UNIX\n'
        printf 'NoNewPrivileges=yes\n'
        printf 'PrivateTmp=yes\n'
        printf 'ProtectSystem=strict\n'
        printf 'ProtectHome=yes\n'
        printf 'ReadWritePaths=%s\n' "$state_root"
        printf 'UnsetEnvironment=%s\n' "${P9C0_UNSET_ENVIRONMENT_NAMES//,/ }"
        printf 'UMask=0077\n'
    } > "$rendered_unit" || {
        set +o noclobber
        umask "$old_umask"
        return 1
    }
    set +o noclobber
    umask "$old_umask"
    chmod 600 "$rendered_unit" || return 1
}

# Invoke systemd-analyze verify on the rendered definition file. The
# function captures stderr verbatim and fails closed on any non-zero
# exit or stderr containing parse warnings/errors. The capture file is
# derived from a deterministic state-rooted path so the verify seam
# never leaves a stray mktemp /tmp artifact that could leak content
# or be confused with the real definition file.
_p9c0_verify_unit_definition() {
    local def_file="$1" state_root="$2"
    local stderr_file
    stderr_file="$state_root/.p9c0_verify.stderr.$$"
    : > "$stderr_file"
    chmod 600 "$stderr_file" 2>/dev/null || true
    if ! _p9c0_systemd_analyze verify "$def_file" 2>"$stderr_file"; then
        printf 'systemd-analyze verify failed:\n%s\n' "$(cat "$stderr_file")" >&2
        rm -f "$stderr_file"
        return 1
    fi
    # Fail closed on any emitted warning or error even with exit 0.
    if [[ -s $stderr_file ]] && grep -qiE 'warning|error|fail|invalid' "$stderr_file" 2>/dev/null; then
        printf 'systemd-analyze verify emitted a warning/error:\n%s\n' "$(cat "$stderr_file")" >&2
        rm -f "$stderr_file"
        return 1
    fi
    rm -f "$stderr_file"
    return 0
}

# Canonical per-run path the inert unit definition file is written to.
# Lives under the per-run state directory so it inherits state-root
# containment, has a fixed name (no mktemp) so cleanup can target the
# exact sealed path, and never escapes the run directory.
_p9c0_unit_definition_path() {
    local state_root="$1" run_id="$2"
    printf '%s/%s/systemd.verify.service\n' "$state_root" "$run_id"
}

# At render, create the unit definition and seal its SHA-256. At later
# gates, inspect the retained file without rewriting it. Returns 0 only when
# the file exists at the fixed path, mode 0600 / root-owned /
# non-symlink, the SHA matches ``$6`` when supplied, and the exact
# verify call exits clean with no stderr warning/error.
_p9c0_authorize_unit_definition() {
    local def_path="$1" state_root="$2" user="$3" group="$4" work_dir="$5"
    local expected_sha="$6"

    # Containment: raw and resolved paths must live under state_root.
    local raw resolved state_root_resolved
    raw="$def_path"
    case $raw in "$state_root"/*) ;; *) return 1 ;; esac
    _p9c0_is_under_root "$def_path" "$state_root" || return 1

    # Creation is render-only. Preflight/start always pass the sealed SHA
    # and must inspect the retained bytes without rewriting them; otherwise
    # an attacker-induced drift could be silently repaired before comparison.
    if [[ -z $expected_sha ]]; then
        _p9c0_render_unit_definition \
            "$def_path" "$user" "$group" "$work_dir" "$state_root" || return 1
    fi

    [[ -e $def_path && -f $def_path && ! -L $def_path ]] || return 1
    resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$def_path" 2>/dev/null) || return 1
    state_root_resolved=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$state_root" 2>/dev/null) || return 1
    case $resolved in "$state_root_resolved"/*) ;; *) return 1 ;; esac

    # Type / mode / owner / hard-link gates via the existing stat seam.
    local stat_line
    stat_line=$(_p9c0_stat_file "$def_path") || return 1
    IFS=: read -r _ _ _ nlink uid gid mode <<< "$stat_line"
    [[ $nlink == 1 ]] || return 1
    [[ $uid == 0 ]] || return 1
    [[ $gid == 0 ]] || return 1
    [[ $mode == "600" ]] || return 1

    # SHA-256 must match the sealed value when supplied; otherwise echo
    # the freshly captured SHA on stdout so the caller can seal it.
    local sha
    sha=$(_p9c0_sha256_file "$def_path") || return 1
    [[ -z $sha ]] && return 1
    if [[ -n $expected_sha ]]; then
        [[ $sha == "$expected_sha" ]] || return 1
    fi

    # Run exact verify on the sealed file. Captures stderr verbatim.
    if ! _p9c0_verify_unit_definition "$def_path" "$state_root"; then
        return 1
    fi

    if [[ -z $expected_sha ]]; then
        printf '%s' "$sha"
    fi
    return 0
}

_p9c0_static_definition_ledger_record() {
    local run_id="$1" def_path="$2" def_sha="$3"
    printf 'static-definition run=%s def_path=%s def_sha256=%s def_mode=0600 def_owner=root\n' \
        "$run_id" "$def_path" "$def_sha"
}

_p9c0_require_static_definition_ledger() {
    local run_id="$1" def_path="$2" def_sha="$3"
    local ledger="$P9C0_STATE_ROOT/$run_id/ledger/events.jsonl" expected
    [[ -f $ledger ]] || return 1
    expected=$(_p9c0_static_definition_ledger_record "$run_id" "$def_path" "$def_sha")
    grep -Fqx -- "$expected" "$ledger" 2>/dev/null
}

# Semantic post-start comparison. Each property is read via systemctl show and
_p9c0_post_start_verify() {
    local unit="$1" user="$2" group="$3" work_dir="$4" state_root="$5"
    local -a failures=()

    local key actual
    while IFS= read -r key; do
        actual=$(_p9c0_systemctl show -p "$key" --value "$unit" 2>/dev/null || true)
        case $key in
            User)
                [[ $actual == "$user" ]] || failures+=("$key=$actual expected=$user")
                ;;
            Group)
                [[ $actual == "$group" ]] || failures+=("$key=$actual expected=$group")
                ;;
            WorkingDirectory)
                [[ $actual == "$work_dir" ]] || failures+=("$key=$actual expected=$work_dir")
                ;;
            RuntimeMaxUSec)
                _p9c0_python_normalize runtime-max-usec "$actual" 300000000 || failures+=("RuntimeMaxUSec=$actual")
                ;;
            TimeoutStopUSec)
                _p9c0_python_normalize timeout-stop-usec "$actual" 30000000 || failures+=("TimeoutStopUSec=$actual")
                ;;
            KillMode)
                _p9c0_python_normalize kill-mode "$actual" control-group || failures+=("KillMode=$actual")
                ;;
            UMask)
                _p9c0_python_normalize umask "$actual" 0077 || failures+=("UMask=$actual")
                ;;
            NoNewPrivileges)
                _p9c0_python_normalize bool "$actual" yes || failures+=("NoNewPrivileges=$actual")
                ;;
            PrivateTmp)
                _p9c0_python_normalize bool "$actual" yes || failures+=("PrivateTmp=$actual")
                ;;
            ProtectSystem)
                _p9c0_python_normalize protect-system "$actual" strict || failures+=("ProtectSystem=$actual")
                ;;
            ProtectHome)
                _p9c0_python_normalize bool "$actual" yes || failures+=("ProtectHome=$actual")
                ;;
            ReadWritePaths)
                _p9c0_python_normalize read-write-paths "$actual" "$state_root" || failures+=("ReadWritePaths=$actual")
                ;;
            UnsetEnvironment)
                _p9c0_python_normalize unset-environment "$actual" "$P9C0_UNSET_ENVIRONMENT_NAMES" || failures+=("UnsetEnvironment=$actual")
                ;;
            RestrictAddressFamilies)
                _p9c0_python_normalize restrict-address-families "$actual" "" || failures+=("RestrictAddressFamilies=$actual")
                ;;
            IPAddressDeny)
                _p9c0_python_normalize ip-address-deny "$actual" "" || failures+=("IPAddressDeny=$actual")
                ;;
            *)
                failures+=("unknown post-start key=$key")
                ;;
        esac
    done < <(printf '%s\n' User Group WorkingDirectory RuntimeMaxUSec TimeoutStopUSec KillMode UMask NoNewPrivileges PrivateTmp ProtectSystem ProtectHome ReadWritePaths UnsetEnvironment RestrictAddressFamilies IPAddressDeny)

    if (( ${#failures[@]} > 0 )); then
        local f
        for f in "${failures[@]}"; do
            printf 'post-start verify: %s\n' "$f" >&2
        done
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# Recovery flag parsing (Package 3 §4.2)
# ---------------------------------------------------------------------------

# Parse --recoverable / --recovery-reason / --prior-process-stopped into the
# named result variables. The three flags must be all-or-none. Recovery mode
# returns 0 on success and sets the vars to either empty (normal) or filled
# (recovery); missing/malformed recovery evidence returns 1.
P9C0_RECOVERABLE=""
P9C0_RECOVERY_REASON=""
P9C0_PRIOR_PROCESS_STOPPED=""
P9C0_RECOVERY_MODE="normal"
P9C0_RECOVERY_REASON_SHA256="none"

# Parse recovery evidence into fixed globals. This deliberately avoids Bash
# variable-name indirection so the helper remains Bash 3.2-safe.
_p9c0_parse_recovery_flags() {
    P9C0_RECOVERABLE=""
    P9C0_RECOVERY_REASON=""
    P9C0_PRIOR_PROCESS_STOPPED=""
    P9C0_RECOVERY_MODE="normal"
    P9C0_RECOVERY_REASON_SHA256="none"

    local pf_recoverable="" pf_reason="" pf_prior=""
    local pf_recoverable_present="" pf_reason_present="" pf_prior_present=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --recoverable)
                [[ -z $pf_recoverable_present ]] || { printf 'recovery: duplicate --recoverable\n' >&2; return 1; }
                pf_recoverable=1
                pf_recoverable_present=1
                ;;
            --recovery-reason)
                [[ $# -ge 2 ]] || { printf 'recovery-reason: missing value\n' >&2; return 1; }
                [[ -z $pf_reason_present ]] || { printf 'recovery: duplicate --recovery-reason\n' >&2; return 1; }
                pf_reason="$2"
                pf_reason_present=1
                shift
                ;;
            --prior-process-stopped)
                [[ -z $pf_prior_present ]] || { printf 'recovery: duplicate --prior-process-stopped\n' >&2; return 1; }
                pf_prior=1
                pf_prior_present=1
                ;;
            *)
                # Normal start flags are parsed by _p9c0_cmd_start. Keeping
                # them ignorable here lets the fixed parser be reused there.
                ;;
        esac
        shift
    done

    if [[ -n $pf_recoverable_present || -n $pf_reason_present || -n $pf_prior_present ]]; then
        [[ -n $pf_recoverable_present ]] || { printf 'recovery: --recoverable required with recovery flags\n' >&2; return 1; }
        [[ -n $pf_reason_present ]] || { printf 'recovery: --recovery-reason required\n' >&2; return 1; }
        [[ -n $pf_prior_present ]] || { printf 'recovery: --prior-process-stopped required\n' >&2; return 1; }
        local reason_check
        reason_check=$(${P9C0_PYTHON:-python3} - "$pf_reason" <<'PYEOF'
import sys
reason = sys.argv[1]
if not reason:
    print('blank')
    raise SystemExit(1)
if len(reason.encode('utf-8')) > 512:
    print('too-long')
    raise SystemExit(1)
if any(ord(ch) < 32 or ord(ch) == 127 for ch in reason):
    print('control')
    raise SystemExit(1)
print('ok')
PYEOF
        ) || {
            case $reason_check in
                blank) printf 'recovery: reason must be non-empty\n' >&2 ;;
                too-long) printf 'recovery: reason too long (more than 512 bytes)\n' >&2 ;;
                control) printf 'recovery: reason contains control characters\n' >&2 ;;
                *) printf 'recovery: invalid reason\n' >&2 ;;
            esac
            return 1
        }
        P9C0_RECOVERABLE=1
        P9C0_RECOVERY_REASON="$pf_reason"
        P9C0_PRIOR_PROCESS_STOPPED=1
        P9C0_RECOVERY_MODE="recovery"
        P9C0_RECOVERY_REASON_SHA256=$(_p9c0_recovery_reason_digest "$pf_reason") || return 1
    fi
    return 0
}

# Normalize the recovery reason for ledger storage: bounded length and SHA-256
# digest. The ledger never receives the raw reason.
_p9c0_recovery_reason_digest() {
    local reason="$1"
    "${P9C0_PYTHON:-python3}" - "$reason" <<'PYEOF'
import hashlib, sys
reason = sys.argv[1]
digest = hashlib.sha256(reason.encode('utf-8')).hexdigest()
sys.stdout.write(digest)
PYEOF
}


_p9c0_ledger_file() {
    printf '%s/%s/ledger/events.jsonl\n' "$P9C0_STATE_ROOT" "$P9C0_RUN_ID"
}

_p9c0_ledger_append() {
    local line="$1"
    local ledger
    ledger=$(_p9c0_ledger_file)
    [[ -d $(dirname "$ledger") && ! -L $(dirname "$ledger") ]] \
        || _p9c0_die "ledger parent missing or unsafe"
    [[ -f $ledger && ! -L $ledger ]] || _p9c0_die "ledger missing or unsafe"
    printf '%s\n' "$line" >> "$ledger" || _p9c0_die "ledger append failed"
}

# ---------------------------------------------------------------------------
# Render subcommand
# ---------------------------------------------------------------------------

_p9c0_cmd_render() {
    local state_root="" run_id="" fixture_bin="" wrapper="" coord_db="" work_dir="" python="" repo_root=""
    local user="" group="" runtime_parent=""
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
            --user) user="$2"; shift 2 ;;
            --group) group="$2"; shift 2 ;;
            --runtime-parent) runtime_parent="$2"; shift 2 ;;
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
    [[ -n $user ]] || _p9c0_die "render: --user required"
    [[ -n $group ]] || _p9c0_die "render: --group required"

    _p9c0_validate_run_id "$run_id"

    _p9c0_is_absolute_path "$state_root" || _p9c0_die "state-root must be absolute"
    _p9c0_is_absolute_path "$fixture_bin" || _p9c0_die "fixture-bin must be absolute"
    _p9c0_is_absolute_path "$wrapper" || _p9c0_die "wrapper must be absolute"
    _p9c0_is_absolute_path "$coord_db" || _p9c0_die "coord-db must be absolute"
    _p9c0_is_absolute_path "$work_dir" || _p9c0_die "work-dir must be absolute"
    _p9c0_is_absolute_path "$python" || _p9c0_die "python must be absolute"
    _p9c0_is_absolute_path "$repo_root" || _p9c0_die "repo-root must be absolute"

    # Production DB/wrapper rejection (no bypass). Symlink/traversal/alias
    # wrappers also fail closed via _p9c0_enforce_wrapper_authority in the
    # locked section so every failure mode is exercised before the manifest
    # is created.
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
    _p9c0_with_lock "$state_root" "$run_id" _p9c0_render_locked "$state_root" "$run_id" "$fixture_bin" "$wrapper" "$coord_db" "$work_dir" "$python" "$repo_root" "$template" "$user" "$group" "$runtime_parent"
}

_p9c0_render_locked() {
    local state_root="$1" run_id="$2" fixture_bin="$3" wrapper="$4" coord_db="$5" work_dir="$6" python="$7" repo_root="$8" template="$9"
    local user="${10}" group="${11}" runtime_parent="${12}"
    P9C0_STATE_ROOT="$state_root"
    P9C0_RUN_ID="$run_id"

    local state_dir manifest_path
    state_dir="$state_root/$run_id"
    [[ -d $state_dir && ! -L $state_dir ]] \
        || _p9c0_die "render: controller-precreated run root missing or unsafe"
    manifest_path="$state_dir/$P9C0_WRAPPER_MANIFEST_FILENAME"

    # Enforce wrapper authority before anything else: production alias,
    # symlink/traversal, missing/non-regular wrapper, coord-db outside the
    # state root all fail closed here. Authority runs first so any later
    # wrapper invocation is provably bound to a non-bypassable gate.
    _p9c0_enforce_wrapper_authority "$wrapper" "$coord_db" "$state_root" \
        || _p9c0_die "render: wrapper authority rejected"

    # Static containment gate: raw path is under the state root, realpath
    # also resolves under the state root, and the wrapper has exactly one
    # hard link (no alias, no inode sharing).
    _p9c0_wrapper_is_safe_under_prefix "$wrapper" "$state_root" \
        || _p9c0_die "render: wrapper containment rejected"

    # Wrapper file must be root-owned, exact unit-group, mode 0750. The
    # owner-mode gate runs before identity so a wrapper owned by the wrong
    # group is rejected before any group-id comparison.
    _p9c0_enforce_wrapper_owner_mode "$wrapper" \
        || _p9c0_die "render: wrapper owner/mode rejected"

    # Compute wrapper gid so the identity check can enforce equality
    # without a second pass through the filesystem.
    local wrapper_stat wrapper_gid
    wrapper_stat=$(_p9c0_stat_file "$wrapper") || _p9c0_die "render: wrapper stat failed"
    IFS=: read -r _ _ _ _ _ wrapper_gid _ <<< "$wrapper_stat"

    # Derive runtime_parent from state_dir if the caller did not pass one;
    # the state_dir is always under state_root so this is safe by
    # construction.
    if [[ -z $runtime_parent ]]; then
        runtime_parent="$state_dir"
    fi
    # First identity check covers user/group existence, numeric ids, gid
    # equality with the wrapper, runtime_parent containment (raw + resolved
    # against the approved_prefix exactly). It runs before the unit_uid /
    # unit_gid lookup so missing-user / missing-group failures surface as
    # ``unit identity rejected`` rather than as a generic lookup failure.
    _p9c0_enforce_unit_identity "$user" "$group" "$runtime_parent" "$wrapper" "" "$state_root" \
        || _p9c0_die "render: unit identity rejected"

    # Compute numeric uid/gid for the user/group now that identity has
    # confirmed they exist; the values are needed for the manifest verify
    # gate (exact unit gid) and for sealing into the values file.
    local unit_uid unit_gid
    unit_uid=$(_p9c0_identity_lookup_user "$user") || _p9c0_die "render: user lookup failed"
    unit_gid=$(_p9c0_identity_lookup_group "$group") || _p9c0_die "render: group lookup failed"

    # Verify the controller-pre-created manifest. The helper must NOT
    # create, overwrite, chmod, or chown the manifest here; it only
    # reads and validates that the bytes the controller placed there
    # still equal the live wrapper's dev/inode/size/nlink/uid/gid/mode/
    # SHA record. On success the verified record is printed to stdout
    # so we can seal it into the values file verbatim.
    local manifest_line
    manifest_line=$(_p9c0_verify_preexisting_manifest "$manifest_path" "$wrapper" "$unit_gid") \
        || _p9c0_die "render: preexisting manifest rejected"

    # Re-enforce identity now that the manifest has been verified so its
    # gid is pinned to the requested group via the manifest_path argument.
    _p9c0_enforce_unit_identity "$user" "$group" "$runtime_parent" "$wrapper" "$manifest_path" "$state_root" \
        || _p9c0_die "render: unit identity rejected after manifest"

    # values.rendered is written in a single pass after the static
    # definition authority runs so the sealed SHA-256 / path fields are
    # recorded verbatim and re-loaded by every later stage.
    local rendered
    rendered="$state_dir/agents.rendered.toml"

    # Replace each placeholder exactly once; detect leftovers.
    local tmp
    tmp=$(mktemp "$state_dir/.agents.rendered.XXXXXX.toml")
    cp "$template" "$tmp"

    local e1_db="$state_dir/context/e1.sqlite3"
    local e2_db="$state_dir/context/e2.sqlite3"

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
    _p9c0_set_owner_group_mode "$rendered" 0 "$unit_gid" 640 \
        || _p9c0_die "render: rendered config owner/mode rejected"

    P9C0_UNSET_ENVIRONMENT_NAMES="$(_p9c0_join_unset_environment_names)" \
        || _p9c0_die "render: exact UnsetEnvironment authority failed"

    # Static-definition authority: write the inert unit definition to a
    # fixed per-run path (state_dir/systemd.verify.service, never
    # mktemp-then-rm), chmod 0600, require root-owned regular non-symlink
    # file, capture the SHA-256 into the sealed values file, and run
    # ``systemd-analyze verify`` on the exact same path. Any warning,
    # nonzero exit, missing seam, or drift fails closed. The definition
    # is retained until exact cleanup so preflight and start can re-run
    # the same verify on the same bytes.
    local def_path def_sha
    def_path=$(_p9c0_unit_definition_path "$state_root" "$run_id")
    def_sha=$(_p9c0_authorize_unit_definition \
        "$def_path" "$state_root" "$user" "$group" "$work_dir" "") \
        || _p9c0_die "render: unit definition authority rejected"
    [[ -n $def_sha ]] || _p9c0_die "render: unit definition SHA missing"

    # Rewrite values.rendered to include the sealed definition path +
    # SHA so every later stage targets the exact same bytes.
    cat > "$state_dir/values.rendered" <<EOF
state_root=$state_root
run_id=$run_id
fixture_bin=$fixture_bin
wrapper=$wrapper
coord_db=$coord_db
work_dir=$work_dir
python=$python
repo_root=$repo_root
unit_user=$user
unit_group=$group
unit_uid=$unit_uid
unit_gid=$unit_gid
runtime_parent=$runtime_parent
state_path=$state_dir
manifest_path=$manifest_path
manifest_record=$manifest_line
unit_definition_path=$def_path
unit_definition_sha256=$def_sha
unset_environment_names=$P9C0_UNSET_ENVIRONMENT_NAMES
EOF
    chmod 600 "$state_dir/values.rendered"

    # Non-sensitive authority ledger line. Path, SHA, owner/mode, never
    # the definition body.
    _p9c0_ledger_append "$(_p9c0_static_definition_ledger_record "$run_id" "$def_path" "$def_sha")"


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
    _p9c0_ledger_append "render run=$run_id fixture_bin=$fixture_bin wrapper=$wrapper coord_db=$coord_db work_dir=$work_dir manifest_path=$manifest_path"

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

    # Manifest recheck runs BEFORE any wrapper invocation. The manifest
    # file is re-read, its content drift / owner / mode / nlink / uid / gid
    # are checked, and the live wrapper is re-validated against the same
    # approved record. Any drift here aborts before the wrapper is
    # contacted.
    [[ -n $P9C0_MANIFEST_PATH ]] || _p9c0_die "preflight: manifest path missing from values"
    [[ -n $P9C0_MANIFEST_RECORD ]] || _p9c0_die "preflight: manifest record missing from values"
    [[ -n $P9C0_UNIT_GID ]] || _p9c0_die "preflight: unit gid missing from values"
    _p9c0_recheck_manifest_authority "$P9C0_MANIFEST_PATH" "$P9C0_MANIFEST_RECORD" \
        "$P9C0_WRAPPER" "$P9C0_UNIT_GID" \
        || _p9c0_die "preflight: manifest authority drift detected"

    # Identity recheck runs BEFORE any wrapper invocation.
    _p9c0_enforce_unit_identity \
        "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" "$P9C0_RUNTIME_PARENT" \
        "$P9C0_WRAPPER" "$P9C0_MANIFEST_PATH" "$P9C0_STATE_ROOT" \
        || _p9c0_die "preflight: unit identity drift detected"

    # Static-definition authority recheck runs BEFORE any wrapper /
    # systemd-run invocation. Re-validates the exact sealed
    # definition file (raw + realpath containment, regular /
    # non-symlink / root-owned / mode 0600), confirms the live SHA
    # matches the value sealed at render time, and re-runs
    # ``systemd-analyze verify`` on the exact sealed path. Any drift
    # fails closed before the wrapper is invoked.
    [[ -n ${P9C0_UNIT_DEFINITION_PATH:-} ]] \
        || _p9c0_die "preflight: unit_definition_path missing from values"
    [[ -n ${P9C0_UNIT_DEFINITION_SHA256:-} ]] \
        || _p9c0_die "preflight: unit_definition_sha256 missing from values"
    _p9c0_require_static_definition_ledger \
        "$run_id" "$P9C0_UNIT_DEFINITION_PATH" "$P9C0_UNIT_DEFINITION_SHA256" \
        || _p9c0_die "preflight: static definition ledger authority drift detected"
    _p9c0_authorize_unit_definition \
        "$P9C0_UNIT_DEFINITION_PATH" "$P9C0_STATE_ROOT" \
        "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" "$P9C0_WORK_DIR" \
        "$P9C0_UNIT_DEFINITION_SHA256" \
        || _p9c0_die "preflight: unit definition authority drift detected"

    # Isolated wrapper health/list evidence (read-only). Only reached
    # when the wrapper authority and identity rechecks pass.
    local wrapper_out
    wrapper_out=$("$P9C0_WRAPPER" --version 2>&1) || {
        printf 'preflight: wrapper health output: %s\n' "$wrapper_out" >&2
        _p9c0_die "preflight: wrapper health check failed"
    }
    [[ -n $wrapper_out ]] || _p9c0_die "preflight: wrapper health output empty"
    # No active/running fixture unit may already occupy the exact namespace.
    local unit
    unit=$(_p9c0_unit_name "$agent_id" "$run_id")
    if _p9c0_systemctl list-units --type=service --state=running,activating --no-legend "$unit" 2>/dev/null | grep -q "$unit"; then
        _p9c0_die "preflight: unit $unit already active"
    fi

    # No more than two units per run.
    local ledger
    ledger="$P9C0_STATE_ROOT/$run_id/ledger/events.jsonl"
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
    local recoverable="" recovery_reason="" prior_process_stopped=""
    local recoverable_present="" recovery_reason_present="" prior_process_stopped_present=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --state-root) state_root="$2"; shift 2 ;;
            --run-id) run_id="$2"; shift 2 ;;
            --agent-id) agent_id="$2"; shift 2 ;;
            --mode) mode="$2"; shift 2 ;;
            --user) user="$2"; shift 2 ;;
            --group) group="$2"; shift 2 ;;
            --recoverable)
                recoverable=1
                recoverable_present=1
                shift
                ;;
            --recovery-reason)
                [[ $# -ge 2 ]] || _p9c0_die "start: --recovery-reason requires a value"
                recovery_reason="$2"
                recovery_reason_present=1
                shift 2
                ;;
            --prior-process-stopped)
                prior_process_stopped=1
                prior_process_stopped_present=1
                shift
                ;;
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

    # Identity equality gate. The --user / --group passed to start must
    # equal the user / group sealed at render time (P9C0_UNIT_USER /
    # P9C0_UNIT_GROUP). A mismatch here would change the launching unit's
    # ownership and the recorded manifest gid, so it must fail closed
    # before any wrapper / static-verify / systemd-run call below.
    [[ -n $P9C0_UNIT_USER ]] || _p9c0_die "start: unit_user missing from values"
    [[ -n $P9C0_UNIT_GROUP ]] || _p9c0_die "start: unit_group missing from values"
    [[ $user == "$P9C0_UNIT_USER" ]] || _p9c0_die "start: --user ($user) does not match sealed unit_user ($P9C0_UNIT_USER)"
    [[ $group == "$P9C0_UNIT_GROUP" ]] || _p9c0_die "start: --group ($group) does not match sealed unit_group ($P9C0_UNIT_GROUP)"

    # Parse recovery evidence into fixed globals BEFORE static verify or
    # any wrapper/systemd call. Pass each flag's original presence so
    # the parser can reject partial sets (1/2-item, reason-only,
    # prior-only, recoverable-only) at the all-or-none gate. Blank,
    # control-character, and >512-byte reasons fail closed inside the
    # parser's own validator.
    local recovery_argv=()
    [[ -n $recoverable_present ]] && recovery_argv+=(--recoverable)
    [[ -n $recovery_reason_present ]] && recovery_argv+=(--recovery-reason "$recovery_reason")
    [[ -n $prior_process_stopped_present ]] && recovery_argv+=(--prior-process-stopped)
    _p9c0_parse_recovery_flags ${recovery_argv[@]+"${recovery_argv[@]}"} || _p9c0_die "start: recovery evidence rejected"

    local unit
    unit=$(_p9c0_unit_name "$agent_id" "$run_id")

    _p9c0_with_lock "$state_root" "$run_id" _p9c0_start_locked "$agent_id" "$run_id" "$unit" "$mode" "$user" "$group"
}

_p9c0_start_locked() {
    local agent_id="$1" run_id="$2" unit="$3" mode="$4" user="$5" group="$6"

    local state_dir
    state_dir="$P9C0_STATE_ROOT/$run_id"
    [[ -x $P9C0_PYTHON && ! -d $P9C0_PYTHON ]] \
        || _p9c0_die "start: sealed Python executable missing"
    [[ -d $P9C0_REPO_ROOT && ! -L $P9C0_REPO_ROOT ]] \
        || _p9c0_die "start: sealed repo root missing or unsafe"
    [[ -f $P9C0_REPO_ROOT/multinexus/__init__.py && \
       -f $P9C0_REPO_ROOT/multinexus/agentd/__main__.py ]] \
        || _p9c0_die "start: sealed agentd module missing"

    # Verify preflight gates still hold under lock.
    if _p9c0_systemctl list-units --type=service --state=running,activating --no-legend "$unit" 2>/dev/null | grep -q "$unit"; then
        _p9c0_die "start: unit $unit already active"
    fi

    local ledger
    ledger="$state_dir/ledger/events.jsonl"
    local unit_count=0
    if [[ -f $ledger ]]; then
        unit_count=$(grep -cE "^unit " "$ledger" 2>/dev/null || true)
    fi
    [[ $unit_count -lt $P9C0_MAX_UNITS ]] || _p9c0_die "start: run already has $P9C0_MAX_UNITS units"

    local rendered
    rendered="$state_dir/agents.rendered.toml"
    [[ -f $rendered ]] || _p9c0_die "start: rendered config missing"

    # Manifest recheck runs BEFORE static verify and systemd-run. The
    # manifest file is re-read, its content drift / owner / mode / nlink /
    # uid / gid are checked, and the live wrapper is re-validated against
    # the same approved record. Any drift here aborts before either gate
    # is invoked.
    [[ -n $P9C0_MANIFEST_PATH ]] || _p9c0_die "start: manifest path missing from values"
    [[ -n $P9C0_MANIFEST_RECORD ]] || _p9c0_die "start: manifest record missing from values"
    [[ -n $P9C0_UNIT_GID ]] || _p9c0_die "start: unit gid missing from values"
    _p9c0_recheck_manifest_authority "$P9C0_MANIFEST_PATH" "$P9C0_MANIFEST_RECORD" \
        "$P9C0_WRAPPER" "$P9C0_UNIT_GID" \
        || _p9c0_die "start: manifest authority drift detected"

    # Identity recheck runs BEFORE static verify and systemd-run.
    _p9c0_enforce_unit_identity \
        "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" "$P9C0_RUNTIME_PARENT" \
        "$P9C0_WRAPPER" "$P9C0_MANIFEST_PATH" "$P9C0_STATE_ROOT" \
        || _p9c0_die "start: unit identity drift detected"

    # Static-definition authority recheck. The definition file was
    # written + verified at render time and is sealed in
    # values.rendered; ``_p9c0_authorize_unit_definition`` never rewrites
    # it here. It re-validates containment /
    # regular / non-symlink / root-owned / mode 0600, confirms the
    # SHA matches the sealed value, and re-runs
    # ``systemd-analyze verify`` on the exact same bytes. Any drift
    # or verify failure logs to the ledger and aborts before
    # systemd-run is invoked; the definition file is intentionally
    # retained so cleanup is the sole path that can remove it.
    [[ -n ${P9C0_UNIT_DEFINITION_PATH:-} ]] \
        || _p9c0_die "start: unit_definition_path missing from values"
    [[ -n ${P9C0_UNIT_DEFINITION_SHA256:-} ]] \
        || _p9c0_die "start: unit_definition_sha256 missing from values"
    _p9c0_require_static_definition_ledger \
        "$run_id" "$P9C0_UNIT_DEFINITION_PATH" "$P9C0_UNIT_DEFINITION_SHA256" \
        || _p9c0_die "start: static definition ledger authority drift detected"
    if ! _p9c0_authorize_unit_definition \
            "$P9C0_UNIT_DEFINITION_PATH" "$P9C0_STATE_ROOT" \
            "$P9C0_UNIT_USER" "$P9C0_UNIT_GROUP" "$P9C0_WORK_DIR" \
            "$P9C0_UNIT_DEFINITION_SHA256"; then
        _p9c0_ledger_append "static-verify-failed unit=$unit"
        _p9c0_die "start: static unit definition verification failed"
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
    properties+=(--property="UnsetEnvironment=${P9C0_UNSET_ENVIRONMENT_NAMES//,/ }")
    properties+=(--property="UMask=0077")

    local env_list=("PATH=/usr/local/bin:/usr/bin:/bin")

    # Compose agentd argv. Recovery mode passes the three flags through to
    # agentd so the captured argv reflects the all-or-none intent; normal
    # mode passes none of them.
    local agentd_argv=()
    agentd_argv+=(--config "$rendered")
    agentd_argv+=(--agent "$agent_id")
    agentd_argv+=(--log-level DEBUG)
    if [[ $P9C0_RECOVERY_MODE == recovery ]]; then
        agentd_argv+=(--recoverable)
        agentd_argv+=(--recovery-reason "$P9C0_RECOVERY_REASON")
        agentd_argv+=(--prior-process-stopped)
    fi

    _p9c0_run_systemd_run \
        --unit="$unit" \
        --service-type=simple \
        --collect \
        --remain-after-exit \
        "${properties[@]}" \
        --setenv="${env_list[0]}" \
        env -i -C "$P9C0_REPO_ROOT" "${env_list[@]}" \
        "$P9C0_PYTHON" -m multinexus.agentd \
            "${agentd_argv[@]}" || {
        _p9c0_ledger_append "start-failed unit=$unit"
        _p9c0_die "start: systemd-run failed for $unit"
    }

    # Digest-only recovery evidence ledger line; the raw reason is never
    # recorded.
    _p9c0_ledger_append "recovery mode=$P9C0_RECOVERY_MODE reason_sha256=$P9C0_RECOVERY_REASON_SHA256 unit=$unit"

    # Capture post-start properties.
    local main_pid cgroup state result
    main_pid=$(_p9c0_systemctl show -p MainPID --value "$unit" 2>/dev/null || true)
    cgroup=$(_p9c0_systemctl show -p ControlGroup --value "$unit" 2>/dev/null || true)
    state=$(_p9c0_systemctl show -p ActiveState --value "$unit" 2>/dev/null || true)
    result=$(_p9c0_systemctl show -p Result --value "$unit" 2>/dev/null || true)

    # Validate mandatory properties with normalizers.
    if ! _p9c0_post_start_verify "$unit" "$user" "$group" "$P9C0_WORK_DIR" "$P9C0_STATE_ROOT"; then
        _p9c0_ledger_append "post-start-mismatch unit=$unit"
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
    if ! grep -qE "^cgroup-empty unit=$unit( |$)" "$state_dir/ledger/events.jsonl" 2>/dev/null; then
        _p9c0_die "cleanup: stop/cgroup proof missing for $unit"
    fi

    # Record this exact unit's cleanup idempotently. Shared controller
    # evidence (values, rendered config, context DBs, wrapper, manifest,
    # ledgers, and journals) is retained for Package 3 closeout review.
    # Only the inert static-definition file may be removed, and only after
    # every exact unit recorded in this run has its own cleanup proof.
    local ledger
    ledger="$state_dir/ledger/events.jsonl"
    if ! grep -Fqx -- "cleanup unit=$unit" "$ledger" 2>/dev/null; then
        _p9c0_ledger_append "cleanup unit=$unit"
    fi

    local line recorded_unit all_clean=1 unit_count=0
    while IFS= read -r line; do
        [[ $line == "unit "* ]] || continue
        recorded_unit="${line#unit }"
        recorded_unit="${recorded_unit%% *}"
        unit_count=$((unit_count + 1))
        if ! grep -Fqx -- "cleanup unit=$recorded_unit" "$ledger" 2>/dev/null; then
            all_clean=0
        fi
    done < "$ledger"
    [[ $unit_count -gt 0 ]] || _p9c0_die "cleanup: no exact unit records"

    if [[ $all_clean -ne 1 ]]; then
        printf 'cleaned up %s; shared static definition retained until all units are clean\n' "$unit"
        return 0
    fi

    # Static-definition deletion targets the exact sealed path only — never
    # a glob or sibling .service. Re-entry after deletion is a no-op.
    [[ -n ${P9C0_UNIT_DEFINITION_PATH:-} ]] \
        || _p9c0_die "cleanup: sealed unit_definition_path missing"
    local def_path="$P9C0_UNIT_DEFINITION_PATH"
    local expected_def_path
    expected_def_path=$(_p9c0_unit_definition_path "$P9C0_STATE_ROOT" "$P9C0_RUN_ID")
    [[ $def_path == "$expected_def_path" ]] \
        || _p9c0_die "cleanup: definition path is not the fixed per-run path"
    _p9c0_require_static_definition_ledger \
        "$P9C0_RUN_ID" "$def_path" "$P9C0_UNIT_DEFINITION_SHA256" \
        || _p9c0_die "cleanup: static definition ledger authority missing"
    _p9c0_is_under_root "$def_path" "$P9C0_STATE_ROOT" \
        || _p9c0_die "cleanup: definition escapes state root: $def_path"
    if [[ -e $def_path ]]; then
        rm -f "$def_path"
    fi

    printf 'cleaned up %s\n' "$unit"
}

# ---------------------------------------------------------------------------
# Ledger helpers
# ---------------------------------------------------------------------------

_p9c0_require_ledger_unit() {
    local unit="$1"
    local ledger
    ledger="$P9C0_STATE_ROOT/$P9C0_RUN_ID/ledger/events.jsonl"
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
    ledger="$P9C0_STATE_ROOT/$P9C0_RUN_ID/ledger/events.jsonl"
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
            unit_user) P9C0_UNIT_USER="$value" ;;
            unit_group) P9C0_UNIT_GROUP="$value" ;;
            unit_uid) P9C0_UNIT_UID="$value" ;;
            unit_gid) P9C0_UNIT_GID="$value" ;;
            runtime_parent) P9C0_RUNTIME_PARENT="$value" ;;
            state_path) P9C0_STATE_PATH="$value" ;;
            manifest_path) P9C0_MANIFEST_PATH="$value" ;;
            manifest_record) P9C0_MANIFEST_RECORD="$value" ;;
            unit_definition_path) P9C0_UNIT_DEFINITION_PATH="$value" ;;
            unit_definition_sha256) P9C0_UNIT_DEFINITION_SHA256="$value" ;;
            unset_environment_names) P9C0_UNSET_ENVIRONMENT_NAMES="$value" ;;
        esac
    done < "$values_file"

    # Static-definition authority is required for preflight / start /
    # cleanup. A missing or empty sealed path / SHA is a hard failure;
    # the helper cannot silently proceed without durable evidence of the
    # unit-definition file identity.
    [[ -n ${P9C0_UNIT_DEFINITION_PATH:-} ]] \
        || _p9c0_die "values.rendered missing unit_definition_path"
    [[ -n ${P9C0_UNIT_DEFINITION_SHA256:-} ]] \
        || _p9c0_die "values.rendered missing unit_definition_sha256"
    [[ -n ${P9C0_UNSET_ENVIRONMENT_NAMES:-} ]] \
        || _p9c0_die "values.rendered missing unset_environment_names"
    local unset_name
    local unset_names=()
    IFS=, read -r -a unset_names <<< "$P9C0_UNSET_ENVIRONMENT_NAMES"
    for unset_name in "${unset_names[@]}"; do
        [[ "$unset_name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ && "$unset_name" != *"*"* ]] \
            || _p9c0_die "values.rendered contains invalid UnsetEnvironment name"
    done

    local expected_definition_path
    expected_definition_path=$(_p9c0_unit_definition_path "$state_root" "$run_id")
    [[ $P9C0_UNIT_DEFINITION_PATH == "$expected_definition_path" ]] \
        || _p9c0_die "unit_definition_path is not the fixed per-run path"

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
    lock_file="$state_root/$run_id/lock/unit-helper.lock"
    [[ -d $(dirname "$lock_file") && ! -L $(dirname "$lock_file") ]] \
        || _p9c0_die "lock parent missing or unsafe"
    _p9c0_lock_file_authority "$lock_file" || _p9c0_die "lock file authority rejected"
    (
        _p9c0_flock -x 9 || _p9c0_die "cannot acquire lock"
        "$@"
    ) 9>>"$lock_file" || _p9c0_die "lock operation failed"
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
