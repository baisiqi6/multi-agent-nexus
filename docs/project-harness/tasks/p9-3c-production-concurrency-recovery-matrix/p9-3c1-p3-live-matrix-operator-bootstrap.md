# P9-3C1 P3 Live Production Matrix — Operator Bootstrap

状态：`DRAFT_FOR_INDEPENDENT_BOOTSTRAP_REVIEW_LIVE_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Role and exact authority

本文件是 Codex operator 的 bounded production runbook，not a Coding worker prompt。Expected P3 path
contains zero code change and no Coding worker。If any code/test/config/script change becomes necessary，
stop this route and open a new implementation/result-review/deploy package；the first Coding worker
candidate is OMP `KAT-Coder-Pro V2.5`，with actual provider/model proved by native JSONL。

Bootstrap reviewer and operator must read completely：

1. `p9-3c1-p3-live-matrix-measurement.md`；
2. `p9-3c1-p3-live-matrix-plan.md`；
3. `p9-3c1-p3-live-matrix-plan-review.md`；
4. P2 deployment dogfood/result review；
5. `scripts/p9_3c1_controller.py` and `scripts/p9-3c1-production-verify.sh`。

Exact input authority：

- plan base：`33773c16fe7a12174b55e8e1731dbb2705e9e56b`；
- plan disposition HEAD：`cce85c522bb99d88c4e26ab43f47938e66cbfbc8`；
- plan-review commit：`460dc62cefd424e10803adc3b83088d90bfb3a7b`；
- approved plan SHA-256：
  `7e8d8846f56d4d62870c63f30705855586adcf34caf2d593f80839952d175fe2`；
- measurement SHA-256：
  `7b84344dccf02d0164565f4a1bc127cb9f5860663cea697e4f64712b6639cf13`；
- plan-review SHA-256：
  `df73e862c580a562348260719dd1cf693183f68f472331ed8c1f5c9e3b148426`；
- final plan review：`APPROVE`，`P0/P1/P2: none`；
- review JSONL SHA-256：
  `681a341e09045daa61b0d23e8f85206c417bb74fce1cf23bd4bb1dac3f4a8055`；
- runtime implementation：`17d0bcc1d0aeb56a821b88f096379e6dcb547fc9`；
- currently deployed MultiNexus：`06f98f25f3ef5f51b6bc191c66fbe041c0e006a6`；
- deployed Coordinate：`a8fc3178806c5d4c7bfbf1cafa41567499d5cfd7`。

This bootstrap has no self-SHA。After it is committed，independent bootstrap review must bind exact
bootstrap bytes/SHA and the authorities above。Until that fresh review returns `APPROVE`，do not merge、
push、deploy、prepare、create/install authorization、run or cleanup。

## 2. Fixed identities and local evidence boundary

```text
HOST=kook-hermes-admin
REMOTE_HOSTNAME=VM-0-15-ubuntu
REMOTE_DB=/var/lib/coordinate/coord.sqlite3
REMOTE_CLI=/usr/local/bin/coord-local
REMOTE_ROOT=/var/tmp/multinexus-p9-3c1
ENTRYPOINT=/opt/multinexus/scripts/p9-3c1-production-verify.sh
LOCK_HELPER=/usr/local/sbin/coordinate-production-mutation-lock
AUTH_ROOT=/var/tmp/multinexus-p9-3c1-authorizations
UNIT_USER=coord
UNIT_GROUP=coord
```

Local evidence goes only under a fresh run-specific directory inside the user-owned untracked
`/Users/yinxin/projects/multinexus/sessions/`。Never delete、move、stage or rewrite existing session
directories。Never print or collect prompts、results、environment values、raw P0 token、credentials or
service secrets。

Retained production roots are immutable：

```text
p9-3c1-prod-20260716t062904z-90d00e16
p9-3c1-prod-20260716t064920z-c2bee4d4
p9-3c1-prod-20260716t071325z-06f98f25
```

The argv failure `p9-3c1-prod-20260716t061838z-37721127` has no root。Do not create、repair、rename、
reuse or cleanup any of these identities。

## 3. Permanent prohibitions

This runbook never authorizes：

- `--allow-dirty`、`--no-smoke`、service restart or manual process kill；
- direct production SQLite write、schema/migration change、whole-DB restore or ad-hoc cancel；
- global/batch lease reap、manual/age-based lock release or speculative `cleanup`；
- external platform delivery、paid provider/network request or real Discord fixture destination；
- a second controller、same-root retry、same nonce reuse or concurrent deploy/mutation；
- reading/printing prompt/result/env、raw P0 token、live-auth bytes or credential fields；
- cleanup or deletion of any audit/forensic root、backup、ledger、auth or reviewer JSONL。

Every command below is gated by the preceding durable artifact。A later section does not retroactively
authorize an earlier blocked stage。

## 4. Bootstrap review gate

Independent reviewer receives this exact file、approved plan/review、controller/entrypoint/tests and may
run local read-only commands/tests only。It must verify：

- every mutation is sequenced behind an exact gate；
- shell commands preserve one controller、fresh root and exact revision authority；
- read-only probes never select sensitive columns；
- auth construction is canonical、one-time and reviewable；
- lock-race/preactivation/cleanup-blocked incident routes match code；
- final success accepts dormant history but rejects executable residue。

Required verdict is `APPROVE` with `P0/P1/P2: none` against exact bootstrap SHA。Any edit requires a
fresh session/review。Approval opens only section 5 merge/push and the separately revalidated section 6
alignment gate；it does not directly authorize P3 `prepare/run/cleanup`。

## 5. Docs merge/push and exact revision derivation

After bootstrap approval，Codex inspects the already committed planning/review/bootstrap diff，adds only
the independent bootstrap-review artifact，then fast-forwards current `main` and pushes `origin/main`。
Derive one exact integrated SHA：

```bash
git -C /Users/yinxin/projects/multinexus fetch origin
git -C /Users/yinxin/projects/multinexus rev-parse main
git -C /Users/yinxin/projects/multinexus rev-parse origin/main
git -C /Users/yinxin/projects/multinexus status --short --untracked-files=no
```

Requirements：local `main == origin/main == MERGED_SHA`；tracked status empty；the only untracked
top-level state may remain the user-owned `sessions/`。Prove no runtime byte changed since
`17d0bcc`：

```bash
export MERGED_SHA='<exact identical local/main/origin SHA>'
git -C /Users/yinxin/projects/multinexus diff --quiet \
  17d0bcc1d0aeb56a821b88f096379e6dcb547fc9.."$MERGED_SHA" -- \
  multinexus scripts config agents.toml tests
```

Nonzero exit blocks deployment。Do not edit docs to bake `MERGED_SHA` back into this already reviewed
bootstrap；record it in the deployment evidence packet and next review artifacts。Because the main
checkout intentionally retains user-owned untracked `sessions/`，create a separate exact detached clean
deploy worktree and never delete/move those sessions：

```bash
export DEPLOY_WORKTREE="/Users/yinxin/Documents/Codex/2026-07-10/ni/work/multinexus-p9-3c1-p3-deploy-${MERGED_SHA:0:8}"
test ! -e "$DEPLOY_WORKTREE"
git -C /Users/yinxin/projects/multinexus worktree add --detach "$DEPLOY_WORKTREE" "$MERGED_SHA"
git -C "$DEPLOY_WORKTREE" status --short
git -C "$DEPLOY_WORKTREE" rev-parse HEAD
```

Require empty status and exact `MERGED_SHA`。

## 6. Read-only pre-alignment snapshot

Before deploy，capture in a fresh local evidence directory：

```bash
export HOST=kook-hermes-admin
export MERGED_SHA='<exact local/main/origin SHA>'
export LOCK_HELPER=/usr/local/sbin/coordinate-production-mutation-lock
export EVIDENCE_DIR="/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-operator-${MERGED_SHA:0:8}"
mkdir -p "$EVIDENCE_DIR"

ssh "$HOST" 'hostname; cat /opt/multinexus/VERSION_DEPLOYED; cat /opt/coordinate/VERSION_DEPLOYED'
ssh "$HOST" "sudo $LOCK_HELPER status"
ssh "$HOST" 'systemctl show coordinate.service multinexus-discord-bridge.service \
  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts --no-pager'
```

The lock status must be exact free/phase free；service identities active/running；Coordinate revision
exact `a8fc317...`；MultiNexus revision exact `06f98f2...` before alignment。The pre-alignment snapshot
must also reprove DB `ok/13/0`、zero pending/running/recoverable timed-out job、zero active/due lease and
zero P9-3C1 namespace。Use the read-only query in section 10 with `RUN_ID` unset；it selects only ids、
statuses、attempt counts、lease timing/resource ids and public source versions。

Any held/invalid lock、nonterminal job、active lease、DB failure、fixture state、service PID/restart drift
or concurrent production task blocks alignment。

## 7. No-restart revision-alignment deploy

Only a tracked-clean worktree at exact `MERGED_SHA` may be supplied：

```bash
"$DEPLOY_WORKTREE/scripts/deploy-server.sh" multinexus \
  --host "$HOST" \
  --multinexus-src "$DEPLOY_WORKTREE" \
  --no-restart
```

Deploy must finish install/hash/parity/VERSION gates and bounded smoke。If smoke fails on a transient
Discord reconnect，record the nonzero result as failure；wait for an exact later bridge ready boundary and
run only bounded `"$DEPLOY_WORKTREE/scripts/server-smoke.sh" --host "$HOST" --since '<exact boundary>'`。
Do not redeploy or
hide the first failure unless installed authority itself is wrong。

Post-deploy requirements：

- `/opt/multinexus/VERSION_DEPLOYED` commit exact `MERGED_SHA`；
- installed controller/entrypoint/helper/fixture/agentd bytes equal the P2 reviewed hashes；
- canonical roster/executor/capacity parity is zero delta；
- service PID/NRestarts unchanged；lock free；DB `ok/13/0`；zero executable fixture state；
- no restart、catalog activation、workspace/job/lease/delivery mutation。

Capture exact stdout/stderr/exit code、installed hashes、VERSION、PIDs/NRestarts and smoke boundary。Any
runtime hash delta or non-doc changed file returns to implementation review and blocks P3。

## 8. Fresh run id and prepare-only mutation gate

Only after alignment evidence is reviewed by Codex，derive one fresh id from deployed SHA：

```bash
export DEPLOYED_SHA="$MERGED_SHA"
export RUN_ID="p9-3c1-prod-$(date -u +%Y%m%dt%H%M%Sz)-${DEPLOYED_SHA:0:8}"
export STATE_ROOT="/var/tmp/multinexus-p9-3c1/$RUN_ID"
export EVIDENCE_DIR="/Users/yinxin/projects/multinexus/sessions/p9-3c1-p3-operator-$RUN_ID"
mkdir -p "$EVIDENCE_DIR"
```

Before prepare：prove `RUN_ID` matches exact regex、remote `STATE_ROOT` absent、lock free and section 6
gates unchanged。Then call exactly once：

```bash
ssh "$HOST" "sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh prepare \
  --run-id '$RUN_ID' --unit-user coord --unit-group coord" \
  | tee "$EVIDENCE_DIR/prepare.stdout"
```

No `run` or `cleanup`。Nonzero prepare retains its forensic root；do not repair/reuse/cleanup it。Diagnose
read-only，correct through a newly reviewed revision if necessary，and later create a fresh id。

## 9. Double read-only packet and tree stability

For a successful `status=sealed` prepare，capture two rounds：

```bash
for round in 1 2; do
  ssh "$HOST" "sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh preflight \
    --run-id '$RUN_ID'" | tee "$EVIDENCE_DIR/preflight-$round.stdout"
  ssh "$HOST" "sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh status \
    --run-id '$RUN_ID'" | tee "$EVIDENCE_DIR/status-$round.stdout"
  ssh "$HOST" "(sudo find '$STATE_ROOT' -xdev \
    -printf '%P|%y|%m|%U|%G|%s|%T@|%n\\n'; \
    sudo find '$STATE_ROOT' -xdev -type f -exec sha256sum {} +) \
    | LC_ALL=C sort | sha256sum" \
    | tee "$EVIDENCE_DIR/tree-$round.sha256"
done
```

The two preflight outputs、two status outputs and tree aggregate must be byte-identical by category。
Required：phase sealed；ledger one valid `prepare.completed` record；lock free；token absent；live auth
absent；root/mode/nlink matrix exact；manifest/backup/config/install/revisions exact；DB `ok/13/0`；
canonical projection stable；zero P9 workspace/profile/agent/catalog/job/lease/unit/process。

Copy only non-sensitive controller authority to local evidence：

```bash
ssh "$HOST" "sudo cat '$STATE_ROOT/control/manifest.json'" > "$EVIDENCE_DIR/manifest.json"
ssh "$HOST" "sudo cat '$STATE_ROOT/control/manifest.sha256'" > "$EVIDENCE_DIR/manifest.sha256"
ssh "$HOST" "sudo stat -c '%n|%F|%a|%u|%g|%h|%s' \
  '$STATE_ROOT' '$STATE_ROOT/control' '$STATE_ROOT/control/manifest.json' \
  '$STATE_ROOT/backup/coord.sqlite3'" > "$EVIDENCE_DIR/state-stat.txt"
```

Do not copy the DB backup or any prompt/result field。Hash the packet files and freeze them。Any later
source/install/manifest/bootstrap/preflight/status/tree/baseline drift invalidates this root。

## 10. Exact read-only state query

Use this query before alignment、before run、during monitoring and after terminal state。It opens SQLite
with `mode=ro`、`PRAGMA query_only=ON`，selects bounded non-sensitive columns only and never begins a
transaction：

```bash
ssh "$HOST" 'sudo /usr/bin/python3.12 -' <<'PY'
import datetime, json, sqlite3

db = "file:/var/lib/coordinate/coord.sqlite3?mode=ro"
conn = sqlite3.connect(db, uri=True)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA query_only=ON")

def rows(sql, params=()):
    return [dict(row) for row in conn.execute(sql, params).fetchall()]

now = datetime.datetime.now(datetime.timezone.utc).isoformat()
out = {
    "integrity": rows("PRAGMA integrity_check"),
    "schema": rows("PRAGMA user_version"),
    "fk": rows("PRAGMA foreign_key_check"),
    "nonterminal_jobs": rows(
        "SELECT id, status, assigned_agent, attempt_count, recoverable FROM jobs "
        "WHERE status IN ('pending','running') ORDER BY id"
    ),
    "recoverable_timed_out": rows(
        "SELECT id, status, assigned_agent, attempt_count, recoverable FROM jobs "
        "WHERE status='timed_out' AND recoverable=1 ORDER BY id"
    ),
    "active_leases": rows(
        "SELECT lease_id, job_id, agent_id, resource_key, status, renewed_at, expires_at, "
        "CASE WHEN expires_at <= ? THEN 1 ELSE 0 END AS due FROM execution_attempt_leases "
        "WHERE status='active' ORDER BY lease_id", (now,)
    ),
    "p9_jobs": rows(
        "SELECT id, status, assigned_agent, attempt_count, recoverable FROM jobs "
        "WHERE workspace_id='p9-3c1-production' ORDER BY id"
    ),
    "p9_leases": rows(
        "SELECT l.lease_id, l.job_id, l.agent_id, l.resource_key, l.status, l.renewed_at, l.expires_at "
        "FROM execution_attempt_leases l JOIN jobs j ON j.id=l.job_id "
        "WHERE j.workspace_id='p9-3c1-production' ORDER BY l.job_id, l.attempt_token"
    ),
    "p9_agents": rows(
        "SELECT id, online_state, current_load, host_id FROM agents "
        "WHERE id IN ('p9-3c-fixture-e1','p9-3c-fixture-e2') ORDER BY id"
    ),
    "p9_executor_sources": rows(
        "SELECT source_id, source_version FROM executor_catalog_sources "
        "WHERE source_id='p9-3c1-fixture-executors' ORDER BY source_id"
    ),
    "p9_executor_definitions": rows(
        "SELECT id, source_id FROM executor_definitions "
        "WHERE source_id='p9-3c1-fixture-executors' ORDER BY id"
    ),
    "p9_executor_bindings": rows(
        "SELECT agent_id, source_id, enabled FROM executor_instance_bindings "
        "WHERE source_id='p9-3c1-fixture-executors' ORDER BY agent_id"
    ),
    "p9_capacity_sources": rows(
        "SELECT source_id, source_version FROM executor_capacity_sources "
        "WHERE source_id='p9-3c1-fixture-capacity' ORDER BY source_id"
    ),
    "p9_capacity_policies": rows(
        "SELECT agent_id, source_id, max_concurrent_jobs FROM executor_capacity_policies "
        "WHERE source_id='p9-3c1-fixture-capacity' ORDER BY agent_id"
    ),
    "p9_workspace": rows(
        "SELECT id, path FROM workspaces WHERE id='p9-3c1-production' ORDER BY id"
    ),
    "p9_host_profile": rows(
        "SELECT workspace_id, host_id, workspace_path FROM workspace_host_profiles "
        "WHERE workspace_id='p9-3c1-production' ORDER BY host_id"
    ),
}
print(json.dumps(out, sort_keys=True, separators=(",", ":")))
conn.close()
PY
```

Before P3 activation，all `p9_*` arrays must be empty。During/after run，compare only the exact
namespaced rows and expected fields；never widen queries to `prompt`、`result_json`、event payload、env、
token or credentials。Delivery readback must select only id/event_id/platform/destination/status/
attempt_count for events already bound to the five exact job ids in controller evidence。

## 11. Basis live-preflight independent review

Create a fresh non-Codex reviewer session only after the immutable packet is complete。Reviewer is
read-only and receives exact：run id、manifest/packet SHAs、approved plan/bootstrap SHAs、merged/deployed
revision、installed hashes、PIDs/NRestarts、tree formula and retained-root list。It independently reruns
`preflight/status` and section 10/state/unit/lock/version/hash probes，without creating remote files。

The valid result must：

- start with `APPROVE` and contain `P0/P1/P2: none`；
- prove actual provider/model from native JSONL；
- bind exact run/manifest/bootstrap/plan/deployed/install/tree state；
- state that it does not authorize mutation beyond canonical auth proposal drafting。

After session termination，compute the final immutable native JSONL SHA-256。Any same-session addendum
changes the digest and must be fully finished before auth creation。This SHA is
`review_artifact_sha256`。

## 12. Canonical authorization proposal

Compute exact committed bootstrap SHA locally and remotely；both must match the SHA approved by the
bootstrap reviewer。Then create a fresh local proposal with this reviewed script。It creates a new file
with mode 0600 and refuses overwrite；the `installed_revisions` and `installed_hashes` objects come
directly from the sealed manifest：

```bash
export BOOTSTRAP_SHA='<exact approved bootstrap SHA-256>'
export BASIS_JSONL_SHA='<exact completed basis reviewer JSONL SHA-256>'
export AUTH_LOCAL="$EVIDENCE_DIR/$RUN_ID.authorization.json"
export MANIFEST_LOCAL="$EVIDENCE_DIR/manifest.json"

/usr/bin/python3 - <<'PY'
import datetime, hashlib, json, os, re, secrets
from pathlib import Path

run_id = os.environ["RUN_ID"]
manifest_path = Path(os.environ["MANIFEST_LOCAL"])
out_path = Path(os.environ["AUTH_LOCAL"])
bootstrap_sha = os.environ["BOOTSTRAP_SHA"]
review_sha = os.environ["BASIS_JSONL_SHA"]
sha_re = re.compile(r"[0-9a-f]{64}")
if not sha_re.fullmatch(bootstrap_sha) or not sha_re.fullmatch(review_sha):
    raise SystemExit("invalid reviewed SHA input")
raw_manifest = manifest_path.read_bytes()
manifest = json.loads(raw_manifest)
canonical_manifest = json.dumps(
    manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")
).encode("utf-8") + b"\n"
if raw_manifest != canonical_manifest or manifest.get("run_id") != run_id:
    raise SystemExit("manifest bytes/run authority mismatch")
manifest_sha = hashlib.sha256(raw_manifest).hexdigest()
now = datetime.datetime.now(datetime.timezone.utc)
auth = {
    "contract_version": 1,
    "run_id": run_id,
    "manifest_sha256": manifest_sha,
    "installed_revisions": manifest["installed_revisions"],
    "installed_hashes": manifest["installed_hashes"],
    "p3_bootstrap_sha256": bootstrap_sha,
    "review_artifact_sha256": review_sha,
    "reviewer_verdict": "APPROVE",
    "budgets": {
        "total_requests": 5,
        "max_active_units": 2,
        "provider_network": 0,
        "external_delivery": 0,
    },
    "expiry_utc": (now + datetime.timedelta(minutes=60)).isoformat().replace("+00:00", "Z"),
    "nonce": "p9-3c1-p3-" + now.strftime("%Y%m%dt%H%M%Sz-") + secrets.token_hex(16),
}
raw = json.dumps(auth, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "wb") as fh:
    fh.write(raw)
    fh.flush()
    os.fsync(fh.fileno())
print(json.dumps({
    "path": str(out_path),
    "sha256": hashlib.sha256(raw).hexdigest(),
    "expiry_utc": auth["expiry_utc"],
}, sort_keys=True))
PY
```

Record exact auth SHA、stat and expiry。Do not print the full object in operator chat/logs。If creation
fails or any input drifts，do not edit/overwrite；use a new path/nonce only after the cause is reviewed。

## 13. Fresh final exact-auth review

A second fresh non-Codex reviewer receives exact auth bytes/SHA、basis JSONL+SHA、manifest、approved
bootstrap/plan、installed/live authority and current time。It must recompute all hashes、canonical bytes、
exact keys/types/budgets、expiry/nonce and return `APPROVE` with `P0/P1/P2: none`。

Its native JSONL SHA is closeout evidence only and is not inserted into auth。If auth bytes change、the
review session is incomplete/modified or less than 50 minutes would remain at run time，discard that
proposal without installing it；create a fresh nonce/file and repeat final auth review。

## 14. Root-owned remote auth install

Only after final auth approval，copy through a unique non-root staging name and install the exact reviewed
bytes：

```bash
export AUTH_SHA='<exact final reviewed auth SHA-256>'
export AUTH_REMOTE="/var/tmp/multinexus-p9-3c1-authorizations/$RUN_ID.json"
export AUTH_UPLOAD=".p9-3c1-auth-upload-$RUN_ID.json"

scp -p "$AUTH_LOCAL" "$HOST:$AUTH_UPLOAD"
ssh "$HOST" 'sudo /usr/bin/python3.12 - /var/tmp/multinexus-p9-3c1-authorizations' <<'PY'
import os, stat, sys
from pathlib import Path

root = Path(sys.argv[1])
try:
    root.mkdir(mode=0o700)
except FileExistsError:
    pass
st = root.stat(follow_symlinks=False)
if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o700:
    raise SystemExit("authorization directory authority mismatch")
PY
ssh "$HOST" "sudo /usr/bin/python3.12 - '$AUTH_UPLOAD' '$AUTH_REMOTE' '$AUTH_SHA'" <<'PY'
import hashlib, os, re, stat, sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
expected_sha = sys.argv[3]
if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
    raise SystemExit("authorization expected SHA malformed")
src_fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW)
try:
    src_stat = os.fstat(src_fd)
    if not stat.S_ISREG(src_stat.st_mode) or src_stat.st_nlink != 1 or stat.S_IMODE(src_stat.st_mode) != 0o600:
        raise SystemExit("authorization upload authority mismatch")
    chunks = []
    while True:
        chunk = os.read(src_fd, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    raw = b"".join(chunks)
finally:
    os.close(src_fd)
if hashlib.sha256(raw).hexdigest() != expected_sha:
    raise SystemExit("authorization upload SHA mismatch")
fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
try:
    with os.fdopen(fd, "wb", closefd=False) as fh:
        fh.write(raw)
        fh.flush()
    os.fchown(fd, 0, 0)
    os.fchmod(fd, 0o600)
    os.fsync(fd)
finally:
    os.close(fd)
dfd = os.open(dst.parent, os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(dfd)
finally:
    os.close(dfd)
PY
ssh "$HOST" "sudo stat -c '%n|%F|%a|%u|%g|%h|%s' '$AUTH_REMOTE'"
ssh "$HOST" "printf '%s  %s\\n' '$AUTH_SHA' '$AUTH_REMOTE' | sudo sha256sum -c -"
ssh "$HOST" "rm -f '$AUTH_UPLOAD'"
```

Require ordinary file、root:root、0600、nlink 1 and exact `AUTH_SHA`。Do not cat it。If final path exists
or any mismatch occurs，do not replace/edit/reuse it；stop and create a fresh reviewed root/auth chain。

## 15. Last pre-run gate

Immediately before run，recompute all exact hashes and require at least 50 minutes before expiry：

- local/main/origin/deployed `MERGED_SHA` exact and runtime install hashes unchanged；
- manifest/bootstrap/auth/basis/final review SHAs exact；
- phase sealed；ledger/preflight/status/tree exact；live auth and token absent；
- lock free/path absent；no other deploy/production mutation/controller active；
- section 10 pre-run state is `ok/13/0` with zero nonterminal/recoverable/active/due/P9 arrays；
- P9 units/process/cgroups absent；canonical services active/running with sealed PID/NRestarts；
- canonical projection equals manifest；provider/network/external-delivery counters zero；
- auth source stat/hash exact and expiry remaining >= 50 minutes。

Any drift invalidates the authorization and run root。Do not repair and continue。

## 16. One-shot live run

Open one persistent local operator terminal with SSH keepalives。Run exactly once in foreground；do not
use a timeout that kills the controller、do not background it and do not start a second controller：

```bash
set -o pipefail
ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=4 "$HOST" \
  "sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh run \
    --run-id '$RUN_ID' \
    --authorization-file '$AUTH_REMOTE' \
    --authorization-sha256 '$AUTH_SHA'" \
  | tee "$EVIDENCE_DIR/run.stdout"
RUN_EXIT=$?
printf '%s\n' "$RUN_EXIT" | tee "$EVIDENCE_DIR/run.exit"
```

Controller stdout may be quiet until terminal JSON。Silence is not a hang signal。Record exact SSH/
controller exit code。Operator wall deadline is 30 minutes，but expiry is not permission to kill：if the
command is still nonterminal at the deadline，enter incident observation and do not launch another
controller or speculative cleanup。

## 17. Read-only monitoring

Every 30-60 seconds from a separate terminal：

```bash
ssh "$HOST" "sudo /opt/multinexus/scripts/p9-3c1-production-verify.sh status \
  --run-id '$RUN_ID'"
ssh "$HOST" "sudo /usr/local/sbin/coordinate-production-mutation-lock status"
ssh "$HOST" 'systemctl show coordinate.service multinexus-discord-bridge.service \
  -p Id -p ActiveState -p SubState -p MainPID -p NRestarts --no-pager'
ssh "$HOST" "systemctl show 'p9-3c-fixture-e1-$RUN_ID.service' \
  'p9-3c-fixture-e2-$RUN_ID.service' \
  -p Id -p LoadState -p ActiveState -p SubState -p MainPID -p NRestarts -p ControlGroup --no-pager"
```

Also run section 10 and record only bounded non-sensitive output。Do not read the lock token file、
`live-authorization.json` bytes、prompt/result/event payload/env/service environment。Monitoring decides
liveness only；implementation correctness comes from terminal controller evidence and independent review。

## 18. Success gate

Success requires controller stdout exact `status=done` and independent read-only proof：

- phase done；ledger chain/tail exact；live authorization preserved root 0600；token absent；lock free；
- five exact jobs terminal done；J3 N/N+1、exact reap and stale-N rejection evidence exact；
- zero active lease and zero pending/running/recoverable fixture job；
- exactly four sent local/stdout deliveries for J1/J2/J4/J5 and no J3 delivery；
- E1/E2 offline、profiles dormant、units/process/cgroups absent；
- executor v4/capacity v2 sources retained empty，zero definition/binding/policy executable state；
- workspace/host profile and terminal audit rows retained；
- canonical projection equals baseline；DB `ok/13/0`；canonical PIDs/NRestarts unchanged；
- total requests 5、max units 2、provider/network/external delivery 0；
- state root、backup、ledger/evidence、remote auth source and all reviewer JSONL preserved。

Do not call cleanup on a done run。Do not demand zero P9 rows。

## 19. Failure and incident stops

- **Auth rejected before copy**：no DB mutation；retain auth/root；review exact error。
- **Lock race after auth copy**：`_acquire_lock` is before `cmd_run`'s `try`；no
  `preactivation-failed` is written。The live auth consumes the root。Wait for the other owner，then start a
  completely fresh prepare/review/auth chain；never retry this root/nonce。
- **Owned lock，phase sealed/preflight-ok/lock-held failure**：controller writes
  `preactivation-failed` and releases only its exact token。Verify zero namespace mutation。
- **baseline-captured+ failure**：controller attempts fixed cleanup under the same token。Read status/
  ledger/units/section 10 only。
- **phase done + lock free after nonzero**：classify cleanup-completed failure；preserve and review。
- **cleanup-blocked/held lock/uncertain process authority**：stop automation。No second controller、no
  `cleanup`、no manual release。P0 recover requires a separately reviewed exact no-unit/no-process proof
  and operator reason；`cmd_cleanup` itself has no external auth validator and therefore remains behind a
  new procedural incident authorization。
- **real user/canonical drift、DB failure、accepted stale mutation、duplicate resource lease、provider or
  external send**：immediate halt，forensic preservation and human escalation。

No direct DB repair、global reap、service restart or whole-DB restore is authorized by this bootstrap。

## 20. Post-run independent review and closeout

After terminal state，freeze run stdout/exit、tree/stat、manifest/auth/reviewer hashes、ledger/evidence、
section 10 output、unit/process/cgroup state、lock and canonical service identities。Launch a fresh
non-Codex result reviewer with read-only SSH only。It must independently reproduce the success/failure
classification and return `APPROVE` before closeout。

Only after approval，Codex writes deployment dogfood/closeout plus progress、dogfood feedback、roadmap and
Phase 9 status，commits/pushes docs and leaves production state untouched。Closeout-only docs are not
redeployed unless a later package requires revision alignment。

## 21. Bootstrap acceptance boundary

Independent `APPROVE` of this exact bootstrap authorizes the ordered operations above only after each
preceding gate is freshly satisfied。It never authorizes speculative cleanup、manual recovery、repair or
scope expansion。Before merge/push，all production mutation remains blocked。

P9_3C1_P3_OPERATOR_BOOTSTRAP_DRAFT_FOR_INDEPENDENT_REVIEW_LIVE_MUTATION_BLOCKED
