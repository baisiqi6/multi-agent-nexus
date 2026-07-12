#!/usr/bin/env bash
set -euo pipefail

HOST="${DEPLOY_HOST:-kook-hermes-admin}"
SINCE="${SMOKE_SINCE:-10 min ago}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/server-smoke.sh [--host HOST] [--since JOURNALCTL_TIME]

Checks the Tencent Cloud A0 runtime:
  - coordinate.service and multinexus-discord-bridge.service are active
  - deployed version files are present
  - coord-local can run workspace list
  - Discord API is reachable through mihomo proxy
  - recent logs do not contain known deployment-breaker errors
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:?missing value for --host}"
      shift 2
      ;;
    --since)
      SINCE="${2:?missing value for --since}"
      shift 2
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

ssh "$HOST" "SMOKE_SINCE='$SINCE' bash -s" <<'REMOTE'
set -euo pipefail

echo "==> systemd"
systemctl is-active coordinate
systemctl is-active multinexus-discord-bridge

echo "==> deployed versions"
for file in /opt/coordinate/VERSION_DEPLOYED /opt/multinexus/VERSION_DEPLOYED; do
  if [[ -f "$file" ]]; then
    echo "--- $file"
    cat "$file"
  else
    echo "missing deployed version file: $file" >&2
    exit 1
  fi
done

echo "==> coordinate CLI"
/usr/local/bin/coord-local --version
/usr/local/bin/coord-local workspace list >/tmp/coordinate-workspace-list.json
python3 -m json.tool /tmp/coordinate-workspace-list.json >/dev/null
rm -f /tmp/coordinate-workspace-list.json

echo "==> proxy reachability"
if command -v curl >/dev/null 2>&1; then
  curl -fsS --max-time 10 -x http://127.0.0.1:7890 https://discord.com/api/v10/gateway >/dev/null
fi

echo "==> registry authority"
if ! sudo -u coord env PYTHONPATH=/opt/multinexus /opt/coordinate/.venv/bin/python \
    /opt/multinexus/scripts/agent_registry_deploy_verify.py \
    --db /var/lib/coordinate/coord.sqlite3 \
    --workspace-id discord-nexus \
    --authority /opt/multinexus/config/agent-registry.toml \
    --strict-effective >/tmp/registry-smoke.json 2>/tmp/registry-smoke.err; then
  echo "error: registry authority smoke failed" >&2
  cat /tmp/registry-smoke.err >&2
  exit 1
fi
# Emit redacted evidence for operators.
python3 -c "import json; d=json.load(open('/tmp/registry-smoke.json')); print(json.dumps({k:d[k] for k in ('source_id','source_version','source_hash','revision','workspace_id')}, sort_keys=True))"

echo "==> runtime DB agents"
sudo sqlite3 -header -column /var/lib/coordinate/coord.sqlite3 \
  "select id, online_state, coalesce(host_id, '') as host_id, coalesce(last_seen_at, '') as last_seen_at from agents order by id;"

echo "==> recent log breaker scan"
LOGS="$(mktemp)"
journalctl -u coordinate -u multinexus-discord-bridge --since "$SMOKE_SINCE" --no-pager >"$LOGS" || true
if grep -E "Cannot connect to host discord\\.com|ModuleNotFoundError|invalid choice: 'runtime'|Traceback" "$LOGS" >/dev/null; then
  cat "$LOGS" >&2
  rm -f "$LOGS"
  exit 1
fi
rm -f "$LOGS"

echo "server smoke OK"
REMOTE
