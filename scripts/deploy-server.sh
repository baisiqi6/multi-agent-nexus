#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MULTINEXUS_SRC_DEFAULT="$(cd "$SCRIPT_DIR/.." && pwd)"

HOST="${DEPLOY_HOST:-kook-hermes-admin}"
COMPONENT="all"
COORDINATE_SRC="${COORDINATE_SRC:-/Users/yinxin/projects/coordinate}"
MULTINEXUS_SRC="${MULTINEXUS_SRC:-$MULTINEXUS_SRC_DEFAULT}"
ALLOW_DIRTY=0
NO_RESTART=0
NO_SMOKE=0
SKIP_INSTALL=0

usage() {
  cat <<'USAGE'
Usage:
  scripts/deploy-server.sh [status|all|coordinate|multinexus] [options]

Options:
  --host HOST              SSH host alias. Default: kook-hermes-admin
  --coordinate-src PATH    Local coordinate checkout. Default: /Users/yinxin/projects/coordinate
  --multinexus-src PATH    Local multinexus checkout. Default: this repo
  --allow-dirty           Allow deploying from a dirty local working tree
  --skip-install          Sync code but skip pip install
  --no-restart            Do not restart systemd services
  --no-smoke              Do not run scripts/server-smoke.sh after deploy
  -h, --help              Show this help

This is the manual one-key deploy path for Tencent Cloud A0. It intentionally
preserves remote-only runtime files such as agents.toml, env files, SQLite DB,
logs, and virtualenvs.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    status|all|coordinate|multinexus)
      COMPONENT="$1"
      shift
      ;;
    --host)
      HOST="${2:?missing value for --host}"
      shift 2
      ;;
    --coordinate-src)
      COORDINATE_SRC="${2:?missing value for --coordinate-src}"
      shift 2
      ;;
    --multinexus-src)
      MULTINEXUS_SRC="${2:?missing value for --multinexus-src}"
      shift 2
      ;;
    --allow-dirty)
      ALLOW_DIRTY=1
      shift
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --no-restart)
      NO_RESTART=1
      shift
      ;;
    --no-smoke)
      NO_SMOKE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "error: required command not found: $1" >&2
    exit 1
  }
}

timestamp_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

repo_meta() {
  local repo="$1"
  git -C "$repo" rev-parse --is-inside-work-tree >/dev/null
  local dirty
  dirty="$(git -C "$repo" status --short)"
  if [[ "$ALLOW_DIRTY" -ne 1 && -n "$dirty" ]]; then
    echo "error: refusing to deploy dirty repo: $repo" >&2
    echo "$dirty" >&2
    echo "Use --allow-dirty only for an intentional emergency deploy." >&2
    exit 1
  fi
}

git_sha() {
  git -C "$1" rev-parse HEAD
}

git_branch() {
  git -C "$1" branch --show-current
}

remote_sudo_script() {
  ssh "$HOST" "sudo bash -s" "$@"
}

tar_supports_flag() {
  tar "$1" -cf /dev/null -T /dev/null >/dev/null 2>&1
}

sync_to_remote_staging() {
  local src="$1"
  local staging="$2"
  shift 2
  ssh "$HOST" "rm -rf '$staging' && mkdir -p '$staging'"
  # tar+ssh instead of rsync — works on Win where rsync is unavailable.
  # $@ carries --exclude PATTERN pairs (same syntax tar accepts).
  # --delete semantics come from `rm -rf '$staging'` before extract.
  # -z compresses during transfer (ssh doesn't compress by default).
  local tar_flags=()
  tar_supports_flag --no-xattrs && tar_flags+=(--no-xattrs)
  tar_supports_flag --no-fflags && tar_flags+=(--no-fflags)
  COPYFILE_DISABLE=1 tar "${tar_flags[@]}" -czf - "$@" -C "$src" . | ssh "$HOST" "tar -xzf - -C '$staging'"
}

write_remote_version() {
  local path="$1"
  local owner="$2"
  local group="$3"
  local component="$4"
  local source="$5"
  local branch="$6"
  local sha="$7"
  local deployed_at="$8"
  local deployed_by
  deployed_by="$(id -un)@$(hostname)"

  ssh "$HOST" "sudo tee '$path' >/dev/null && sudo chown '$owner:$group' '$path' && sudo chmod 0644 '$path'" <<EOF
component=$component
source=$source
branch=$branch
commit=$sha
deployed_at=$deployed_at
deployed_by=$deployed_by
EOF
}

deploy_coordinate() {
  repo_meta "$COORDINATE_SRC"
  local sha branch deployed_at staging
  sha="$(git_sha "$COORDINATE_SRC")"
  branch="$(git_branch "$COORDINATE_SRC")"
  deployed_at="$(timestamp_utc)"
  staging="/tmp/deploy-coordinate-$sha"

  echo "==> Deploy coordinate $branch@$sha to $HOST"
  sync_to_remote_staging "$COORDINATE_SRC" "$staging" \
    --exclude .git \
    --exclude .venv \
    --exclude .env \
    --exclude .coordinator \
    --exclude data \
    --exclude logs \
    --exclude events.jsonl \
    --exclude __pycache__ \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude .qoder \
    --exclude .DS_Store \
    --exclude VERSION_DEPLOYED

  remote_sudo_script <<EOF
set -euo pipefail
mkdir -p /opt/coordinate
rsync -a --delete \
  --exclude .venv \
  --exclude .coordinator \
  --exclude data \
  --exclude logs \
  --exclude events.jsonl \
  --exclude .qoder \
  --exclude .DS_Store \
  --exclude VERSION_DEPLOYED \
  '$staging'/ /opt/coordinate/
chown -R coord:coord /opt/coordinate
rm -rf '$staging'
EOF

  if [[ "$SKIP_INSTALL" -ne 1 ]]; then
    ssh "$HOST" "sudo -u coord python3 -m venv /opt/coordinate/.venv && sudo -u coord env HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 ALL_PROXY=http://127.0.0.1:7890 /opt/coordinate/.venv/bin/python -m pip install --upgrade pip setuptools wheel && sudo -u coord env HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 ALL_PROXY=http://127.0.0.1:7890 /opt/coordinate/.venv/bin/pip install '/opt/coordinate[daemon]'"
  fi

  write_remote_version "/opt/coordinate/VERSION_DEPLOYED" "coord" "coord" "coordinate" "$COORDINATE_SRC" "$branch" "$sha" "$deployed_at"

  if [[ "$NO_RESTART" -ne 1 ]]; then
    ssh "$HOST" "sudo systemctl daemon-reload && sudo systemctl restart coordinate"
  fi
}

verify_local_registry_parity() {
  local authority="$MULTINEXUS_SRC/config/agent-registry.toml"
  local runtime="$MULTINEXUS_SRC/agents.toml"
  if [[ ! -f "$authority" ]]; then
    echo "error: missing canonical authority: $authority (stage: local-parity)" >&2
    return 1
  fi
  if [[ ! -f "$runtime" ]]; then
    echo "error: missing local runtime config: $runtime (stage: local-parity)" >&2
    return 1
  fi
  if ! env PYTHONPATH="$MULTINEXUS_SRC" python3 -m multinexus.registry_authority verify \
      --authority "$authority" --runtime "$runtime" >/dev/null; then
    echo "error: local authority/runtime mismatch (stage: local-parity)" >&2
    return 1
  fi
}

verify_remote_registry_parity() {
  if ! ssh "$HOST" "env PYTHONPATH=/opt/multinexus python3 -m multinexus.registry_authority verify \
      --authority /opt/multinexus/config/agent-registry.toml --runtime /opt/multinexus/agents.toml" >/dev/null; then
    echo "error: remote authority/runtime mismatch (stage: remote-parity)" >&2
    return 1
  fi
}

sync_capacity_to_coordinate() {
  if ! ssh "$HOST" "sudo /usr/local/bin/coord-local runtime capacity sync \\
      --source /opt/multinexus/config/agent-registry.toml"; then
    echo "error: Coordinate capacity sync failed (stage: capacity-sync)" >&2
    return 1
  fi
}

list_capacity_to_coordinate() {
  if ! ssh "$HOST" "sudo /usr/local/bin/coord-local runtime capacity list >/dev/null"; then
    echo "error: Coordinate capacity list failed (stage: capacity-list)" >&2
    return 1
  fi
}

verify_capacity_absent() {
  if ! ssh "$HOST" "sudo -u coord env PYTHONPATH=/opt/multinexus /opt/coordinate/.venv/bin/python - <<'PY'
import sqlite3, sys
conn = sqlite3.connect('/var/lib/coordinate/coord.sqlite3')
n = conn.execute('SELECT COUNT(*) FROM executor_capacity_sources').fetchone()[0]
sys.exit(0 if n == 0 else 1)
PY"; then
    echo "error: expected no accepted capacity projection, but capacity rows remain (stage: capacity-absent)" >&2
    return 1
  fi
}

capture_capacity_snapshot() {
  local staging="$1"
  local snapshot_path="$2"
  if ! ssh "$HOST" "sudo -u coord env PYTHONPATH=/opt/coordinate/src /opt/coordinate/.venv/bin/python '$staging/scripts/capacity_snapshot_helper.py' --db /var/lib/coordinate/coord.sqlite3 --target-source-id multinexus.discord.capacity --capture '$snapshot_path' && sudo chmod 0600 '$snapshot_path'"; then
    echo "error: failed to capture capacity snapshot (stage: snapshot-capture)" >&2
    return 1
  fi
}

cleanup_capacity_snapshot() {
  local snapshot_path="$1"
  # Must use sudo: snapshot is owned by coord with mode 0600. In sticky-bit
  # /tmp, the SSH user cannot unlink it. Do not swallow failure with || true.
  ssh "$HOST" "sudo rm -f '$snapshot_path'"
}

restore_capacity_snapshot() {
  local snapshot_path="$1"
  local staging="$2"
  # Use the same staged reviewed helper as capture — do not depend on the
  # just-written /opt/multinexus/scripts/ which may be partially overwritten.
  if ! ssh "$HOST" "sudo -u coord env PYTHONPATH=/opt/coordinate/src /opt/coordinate/.venv/bin/python '$staging/scripts/capacity_snapshot_helper.py' --db /var/lib/coordinate/coord.sqlite3 --target-source-id multinexus.discord.capacity --restore '$snapshot_path'"; then
    echo "error: failed to restore capacity snapshot (stage: restore-capacity-snapshot)" >&2
    return 1
  fi
}

restore_previous_accepted_state() {
  # Restore the previously accepted authority and the exact capacity snapshot captured
  # before this deploy. Then re-run all three projection syncs and the committed verifier.
  local backup_path="$1"
  local snapshot_path="$2"
  local staging="$3"
  if ! ssh "$HOST" "test -f '$backup_path' || exit 0; sudo cp -f '$backup_path' /opt/multinexus/config/agent-registry.toml"; then
    echo "error: failed to restore previous accepted authority (stage: restore-source)" >&2
    return 1
  fi
  if ! verify_remote_registry_parity; then
    echo "error: restored authority/runtime parity failed (stage: restore-remote-parity)" >&2
    return 1
  fi
  if ! sync_roster_to_coordinate; then
    echo "error: restored roster sync failed (stage: restore-roster-sync)" >&2
    return 1
  fi
  if ! sync_executor_to_coordinate; then
    echo "error: restored executor sync failed (stage: restore-executor-sync)" >&2
    return 1
  fi
  if ! restore_capacity_snapshot "$snapshot_path" "$staging"; then
    echo "error: restored capacity snapshot failed (stage: restore-capacity-snapshot)" >&2
    return 1
  fi
  if ! verify_committed_registry; then
    echo "error: restored committed parity failed (stage: restore-committed)" >&2
    return 1
  fi
  return 0
}

sync_roster_to_coordinate() {
  if ! ssh "$HOST" "sudo /usr/local/bin/coord-local workspace agent sync discord-nexus \\
      --source /opt/multinexus/config/agent-registry.toml --replace"; then
    echo "error: Coordinate roster sync failed (stage: roster-sync)" >&2
    return 1
  fi
}

sync_executor_to_coordinate() {
  if ! ssh "$HOST" "sudo /usr/local/bin/coord-local runtime executor sync \\
      --source /opt/multinexus/config/agent-registry.toml"; then
    echo "error: Coordinate executor catalog sync failed (stage: executor-sync)" >&2
    return 1
  fi
}

sync_registry_to_coordinate() {
  sync_roster_to_coordinate && sync_executor_to_coordinate
}

verify_committed_registry() {
  if ! ssh "$HOST" "sudo -u coord env PYTHONPATH=/opt/multinexus /opt/coordinate/.venv/bin/python \\
      /opt/multinexus/scripts/agent_registry_deploy_verify.py \\
      --db /var/lib/coordinate/coord.sqlite3 \\
      --workspace-id discord-nexus \\
      --authority /opt/multinexus/config/agent-registry.toml \\
      --strict-effective" >/dev/null; then
    echo "error: committed registry does not match deployed authority (stage: committed-state)" >&2
    return 1
  fi
}

deploy_multinexus() {
  repo_meta "$MULTINEXUS_SRC"
  verify_local_registry_parity

  local sha branch deployed_at staging
  sha="$(git_sha "$MULTINEXUS_SRC")"
  branch="$(git_branch "$MULTINEXUS_SRC")"
  deployed_at="$(timestamp_utc)"
  staging="/tmp/deploy-multinexus-$sha"
  local backup_path="/tmp/agent-registry.toml.capacity-backup"
  local snapshot_path="/tmp/capacity-snapshot-$sha.json"

  echo "==> Deploy multinexus $branch@$sha to $HOST"
  sync_to_remote_staging "$MULTINEXUS_SRC" "$staging" \
    --exclude .git \
    --exclude .venv \
    --exclude .env \
    --exclude agents.toml \
    --exclude agents.toml.bak \
    --exclude logs \
    --exclude data \
    --exclude ':memory:' \
    --exclude ':memory:-shm' \
    --exclude ':memory:-wal' \
    --exclude docs/project-harness/current \
    --exclude __pycache__ \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude .qoder \
    --exclude .DS_Store \
    --exclude VERSION_DEPLOYED

  # Backup the currently accepted authority and capture the exact capacity projection
  # snapshot before overwriting the authority. Any later stage failure triggers
  # restore_previous_accepted_state, which restores both the authority file and the
  # capacity snapshot. Staging is kept until the gate completes so that capture and
  # restore use the same reviewed helper. The snapshot and staging are trap-cleaned.
  ssh "$HOST" "test -f /opt/multinexus/config/agent-registry.toml || exit 0; sudo cp -f /opt/multinexus/config/agent-registry.toml '$backup_path'"
  capture_capacity_snapshot "$staging" "$snapshot_path" || return 1
  trap 'if [ -n "${snapshot_path:-}" ]; then cleanup_capacity_snapshot "$snapshot_path" || true; fi; if [ -n "${staging:-}" ]; then ssh "$HOST" "sudo rm -rf '\''$staging'\''" 2>/dev/null || true; fi' EXIT

  # Guarded source mutation: partial rsync/chown/test failure must trigger a full
  # restore of the previous accepted state before returning nonzero.
  if ! remote_sudo_script <<EOF
set -euo pipefail
mkdir -p /opt/multinexus
rsync -a --delete \\
  --exclude .venv \\
  --exclude agents.toml \\
  --exclude agents.toml.bak \\
  --exclude .env \\
  --exclude logs \\
  --exclude data \\
  --exclude ':memory:' \\
  --exclude ':memory:-shm' \\
  --exclude ':memory:-wal' \\
  --exclude docs/project-harness/current \\
  --exclude docs/project-harness/harness-state.json \\
  --exclude docs/project-harness/events.jsonl \\
  --exclude .qoder \\
  --exclude .DS_Store \\
  --exclude VERSION_DEPLOYED \\
  '$staging'/ /opt/multinexus/
chown -R multinexus:multinexus /opt/multinexus
if [[ -d /opt/multinexus/docs/project-harness ]]; then
  chgrp -R coord /opt/multinexus/docs/project-harness
  find /opt/multinexus/docs/project-harness -type d -exec chmod 2775 {} +
  find /opt/multinexus/docs/project-harness -type f -exec chmod 0664 {} +
fi
test -f /opt/multinexus/agents.toml
EOF
  then
    echo "error: source mutation failed (stage: source-mutation)" >&2
    restore_previous_accepted_state "$backup_path" "$snapshot_path" "$staging" || true
    return 1
  fi

  # Guarded deploy: do not write VERSION_DEPLOYED, restart, or run smoke until all
  # parity/sync/list/committed stages succeed. If any stage fails, restore the
  # previous accepted authority and the exact capacity snapshot before returning nonzero.
  verify_remote_registry_parity || { restore_previous_accepted_state "$backup_path" "$snapshot_path" "$staging"; return 1; }
  sync_registry_to_coordinate || { restore_previous_accepted_state "$backup_path" "$snapshot_path" "$staging"; return 1; }
  sync_capacity_to_coordinate || { restore_previous_accepted_state "$backup_path" "$snapshot_path" "$staging"; return 1; }
  list_capacity_to_coordinate || { restore_previous_accepted_state "$backup_path" "$snapshot_path" "$staging"; return 1; }
  verify_committed_registry || { restore_previous_accepted_state "$backup_path" "$snapshot_path" "$staging"; return 1; }

  if [[ "$SKIP_INSTALL" -ne 1 ]]; then
    ssh "$HOST" "sudo -u multinexus python3 -m venv /opt/multinexus/.venv && sudo -u multinexus env HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 ALL_PROXY=http://127.0.0.1:7890 /opt/multinexus/.venv/bin/python -m pip install --upgrade pip setuptools wheel && sudo -u multinexus env HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 ALL_PROXY=http://127.0.0.1:7890 /opt/multinexus/.venv/bin/pip install -r /opt/multinexus/requirements.txt"
  fi

  write_remote_version "/opt/multinexus/VERSION_DEPLOYED" "multinexus" "multinexus" "multinexus" "$MULTINEXUS_SRC" "$branch" "$sha" "$deployed_at"

  if [[ "$NO_RESTART" -ne 1 ]]; then
    ssh "$HOST" "sudo systemctl daemon-reload && sudo systemctl restart multinexus-discord-bridge"
  fi

  cleanup_capacity_snapshot "$snapshot_path"
  ssh "$HOST" "sudo rm -rf '$staging'"
  trap - EXIT
}

require_cmd git
require_cmd ssh
require_cmd tar

case "$COMPONENT" in
  status)
    "$SCRIPT_DIR/server-smoke.sh" --host "$HOST"
    exit 0
    ;;
  coordinate)
    deploy_coordinate
    ;;
  multinexus)
    deploy_multinexus
    ;;
  all)
    deploy_coordinate
    deploy_multinexus
    ;;
esac

if [[ "$NO_SMOKE" -ne 1 ]]; then
  "$SCRIPT_DIR/server-smoke.sh" --host "$HOST"
fi
