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

deploy_multinexus() {
  repo_meta "$MULTINEXUS_SRC"
  local sha branch deployed_at staging
  sha="$(git_sha "$MULTINEXUS_SRC")"
  branch="$(git_branch "$MULTINEXUS_SRC")"
  deployed_at="$(timestamp_utc)"
  staging="/tmp/deploy-multinexus-$sha"

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

  remote_sudo_script <<EOF
set -euo pipefail
mkdir -p /opt/multinexus
rsync -a --delete \
  --exclude .venv \
  --exclude agents.toml \
  --exclude agents.toml.bak \
  --exclude .env \
  --exclude logs \
  --exclude data \
  --exclude ':memory:' \
  --exclude ':memory:-shm' \
  --exclude ':memory:-wal' \
  --exclude docs/project-harness/current \
  --exclude docs/project-harness/harness-state.json \
  --exclude docs/project-harness/events.jsonl \
  --exclude .qoder \
  --exclude .DS_Store \
  --exclude VERSION_DEPLOYED \
  '$staging'/ /opt/multinexus/
chown -R multinexus:multinexus /opt/multinexus
if [[ -d /opt/multinexus/docs/project-harness ]]; then
  chgrp -R coord /opt/multinexus/docs/project-harness
  find /opt/multinexus/docs/project-harness -type d -exec chmod 2775 {} +
  find /opt/multinexus/docs/project-harness -type f -exec chmod 0664 {} +
fi
test -f /opt/multinexus/agents.toml
rm -rf '$staging'
EOF

  if [[ "$SKIP_INSTALL" -ne 1 ]]; then
    ssh "$HOST" "sudo -u multinexus python3 -m venv /opt/multinexus/.venv && sudo -u multinexus env HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 ALL_PROXY=http://127.0.0.1:7890 /opt/multinexus/.venv/bin/python -m pip install --upgrade pip setuptools wheel && sudo -u multinexus env HTTPS_PROXY=http://127.0.0.1:7890 HTTP_PROXY=http://127.0.0.1:7890 ALL_PROXY=http://127.0.0.1:7890 /opt/multinexus/.venv/bin/pip install -r /opt/multinexus/requirements.txt"
  fi

  write_remote_version "/opt/multinexus/VERSION_DEPLOYED" "multinexus" "multinexus" "multinexus" "$MULTINEXUS_SRC" "$branch" "$sha" "$deployed_at"

  if [[ "$NO_RESTART" -ne 1 ]]; then
    ssh "$HOST" "sudo systemctl daemon-reload && sudo systemctl restart multinexus-discord-bridge"
  fi
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
