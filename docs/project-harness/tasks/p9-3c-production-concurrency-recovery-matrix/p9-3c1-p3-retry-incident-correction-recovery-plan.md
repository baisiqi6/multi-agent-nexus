# P9-3C1 P3 Retry Incident — Correction and Recovery Plan

状态：`DETAILED_PLAN_READY_FOR_INDEPENDENT_REVIEW_ALL_MUTATION_BLOCKED`

日期：2026-07-16 Asia/Shanghai

## 1. Outcome and authority boundary

Reach a reviewed terminal cleanup state for
`p9-3c1-prod-20260716t140135z-dde26886` without deleting audit truth，then make later P3 attempts repeatable
under monotonic Coordinate catalog authority。

This plan authorizes only independent plan review。It does not authorize code changes、lock recovery、token
retirement、deploy、cleanup、fresh prepare/auth/run、DB writes、service changes or P0 recover。

## 2. Non-negotiable invariants

- Preserve all five earlier forensic/success/incident roots and every auth、backup、ledger、reviewer JSONL。
- Never launch a second controller for the incident run。
- Never print/read raw token or live-auth bytes outside the exact root process that consumes them。
- No manual lock-directory/token deletion、direct DB edit、whole-DB restore、service restart or speculative
  cleanup。
- Lock remains held until an independently reviewed recovery sidecar proves the stale-owner incident exact。
- Any live drift、unit/process authority、job/lease residue、DB failure or canonical service drift blocks recovery。
- P0 recover remains forbidden until the IR implementation and its recovery bootstrap are independently
  approved。

## 3. Package and gate sequence

### Package IR — incident recovery primitives

1. this measurement + detailed plan；
2. fresh independent plan review；
3. exact IR worker bootstrap；
4. fresh independent bootstrap review；
5. non-Codex Coding worker in an isolated branch/worktree；
6. Codex line review + focused/full tests；
7. fresh independent implementation result review；
8. exact incident unlock-to-deploy bootstrap + fresh independent review；
9. one reviewed source-streamed P0 recovery，then normal no-restart deploy of exact IR commit；
10. fresh incident-cleanup authorization proposal + fresh exact-auth review；
11. one incident `resume-cleanup` invocation and read-only monitoring；
12. fresh independent terminal incident review and durable dogfood record。

### Package EP — repeatable monotonic catalog protocol

Only after IR terminal approval：measurement/detailed plan → plan review → bootstrap/review → non-Codex
worker → Codex/result review → merge/push → no-restart deploy → completely fresh P3 prepare/basis/auth/final
review/run/post-run review。

No adjacent review gates may be combined。A reviewer is never the worker whose bytes it approves。

## 4. IR implementation scope

Allowed runtime files：

- `scripts/production-mutation-lock.py`；
- `scripts/p9_3c1_controller.py`；
- `scripts/p9-3c1-production-verify.sh` only if needed to expose one exact incident command；
- the narrow relevant tests。

### 4.1 P0 unit/process proof

Correct the systemd probe to reject any active/reloading/activating/deactivating fixture service matching the
real exact families：

```text
p9-3c-fixture-e1-*.service
p9-3c-fixture-e2-*.service
```

Replace the over-broad `pgrep -f p9-3c1` with an exact controller/fixture-process probe executed directly by
the Python helper，so the recovery command、token-file path and its parent shell cannot self-match while a real
`p9_3c1_controller.py` or `p9-3c-fixture-e1/e2` process still blocks。Probe errors remain fail closed。

Add a recover-only `--token-file` authority path：open with `O_RDONLY|O_NOFOLLOW`，require root:root、0600、
single-link regular file，read exactly one canonical 64-hex token and never place raw token bytes in argv、
stdout/stderr or audit。Keep direct `--token` behavior backward compatible for existing reviewed callers；
the incident sidecar must use only `--token-file`。

Add regression tests where real unit/process names block recover，the recovery invocation cannot match itself，
unrelated services/processes do not，bad token-file authority fails closed and audit/release ordering remains
unchanged。

The result-reviewed source may be executed once as a source-streamed recovery sidecar before normal deploy。
The bootstrap must bind its exact SHA and invoke it without installing/replacing the current helper。

### 4.2 Legacy terminal cleanup idempotence

For the exact legacy fixed-version incident only，cleanup must first read bounded source state：

- executor v4 with zero definitions/bindings is already terminal；
- capacity v2 with zero policies is already terminal。

When both are exact，skip lower v3/v2 mutations and proceed to agent deactivation/canonical/DB/final gates。
Any other higher version、non-empty terminal source、unexpected source id/hash or partial executable state
fails closed and retains the newly owned lock。

Do not change Coordinate downgrade semantics and do not treat arbitrary `version <= current` as success。

### 4.3 Incident-authorized stale-token re-acquisition

Add a distinct command such as `resume-cleanup`；do not broaden ordinary `cleanup`。It must require a fresh
root-owned canonical incident authorization with exact：

- contract/action/run id；phase `agents-online`；ledger count/tail SHA/event `cleanup.initiated`；
- stale state-root token digest but never raw token；P0 recovery receipt digest；
- live-auth SHA、manifest SHA、current deployed revisions/hashes；
- incident bootstrap SHA、basis reviewer JSONL SHA、APPROVE verdict、expiry and fresh nonce。

After the sidecar has made the global lock free，`resume-cleanup` must：

1. revalidate all bound authority and no unit/process/job/lease drift；
2. acquire a **new** P0 global token even though the stale token file exists；
3. while the new global lock is held，atomically archive the consumed stale token as root-only forensic
   evidence and install the new token at the standard path，fsyncing files/directories；
4. ledger only token digests/receipt ids，never raw bytes；
5. run the fixed idempotent cleanup suffix；
6. release only the exact new token after `cleanup.completed`/phase `done`。

If acquisition or token swap fails before production mutation，release the new in-memory token and preserve
the original incident authority。If cleanup becomes uncertain after mutation，retain the new lock and stop。
There is no universal `finally: release` rule。

Tests must cover stale digest mismatch、receipt mismatch、global lock not free、race on acquire、token-swap
failure、new-token release on safe preactivation failure、terminal v4/v2 success、non-empty/higher-source
refusal and cleanup failure retaining the new lock。

### 4.4 Shell-explicit receipt capture

Recovery/run bootstraps must execute the pipeline under explicit Bash and capture both stdout/stderr plus the
SSH status without relying on the caller's login shell。Use a tested `bash` wrapper and Bash
`${PIPESTATUS[0]}` only inside that wrapper。Do not propose a mixed Bash/zsh fallback expression。

## 5. IR unlock-to-deploy bootstrap

Because canonical deploy is blocked by the stale global lock，IR needs a separately authored/reviewed one-shot
bootstrap after result review。Immediately before source-streamed recover it must prove：

- exact incident phase/ledger/tail/token-digest and absent owner PID/controller process；
- both exact fixture units not-found/inactive/MainPID 0 and no P9 cgroup/process；
- zero P9 jobs/leases/definitions/bindings/policies；E1/E2 online load 0；terminal empty v4/v2；
- DB `ok/13/0`；canonical services/revisions/hashes unchanged；
- streamed IR helper SHA equals the result-reviewed source；
- root token is read only through the reviewed helper's exact `--token-file` fd authority and never appears in
  argv、stdout/stderr or audit；
- recovery audit parent/file authority and durable receipt exact。

The sidecar may release only the global stale-owner lock。It may not remove the state-root token、deactivate
agents、run cleanup or edit DB。After its success，immediately verify lock free and incident state otherwise
unchanged，then perform one canonical `multinexus --no-restart` deploy of exact reviewed IR main SHA。

## 6. IR incident cleanup gate

After deploy，create a fresh incident basis review and canonical resume-cleanup auth。A second fresh reviewer
must approve exact bytes。Install with root-owned `0600`/`O_EXCL|O_NOFOLLOW` and require at least 50 minutes
TTL before install and invocation。

Run exactly one foreground `resume-cleanup` under explicit Bash receipt capture。Monitor every 30-60 seconds
with bounded status/lock/unit/DB probes。Success requires phase done、tail `cleanup.completed`、standard token
absent、global lock free、E1/E2 offline、zero executable state、terminal empty v4/v2、DB `ok/13/0` and canonical
services unchanged。Never call ordinary cleanup or P0 recover again for this run。

## 7. EP monotonic epoch design

The fresh-run protocol must keep the stable source ids but allocate versions from the currently retained
terminal versions：

- executor stages：`base+1 disabled`、`base+2 enabled`、`base+3 disabled`、`base+4 empty`；
- capacity stages：`base+1 active`、`base+2 empty`。

Prepare uses read-only DB authority to require absent or exact empty terminal sources，captures the bases，
renders deterministic root-owned run-local TOML files from immutable shape templates and seals exact stage
versions、paths、hashes and source-state baseline in the manifest。It must double-read the DB/source authority
around rendering and abandon the root on drift。

Run/preflight/readback/cleanup/success use only manifest-pinned rendered files and expected versions。Cleanup
checks the current version/state before each step：exact already-applied stages are idempotent；a higher or
same-version hash/state mismatch fails closed。Terminal success expects the run's manifest-pinned `base+4`
and `base+2`，not literal v4/v2。

Tests must cover absent sources、retained v4/v2 → v5-v8/v3-v4、another later epoch、partial handler mutation
before readback failure、cleanup from every phase、manifest/render tamper、version overflow/type errors、
concurrent drift and full existing matrix semantics。

Run-scoped source ids are rejected for this package because they multiply durable source identities and widen
query/cleanup authority。Coordinate accepting downgrades/no-op is rejected because it weakens monotonic
authority globally。

## 8. Acceptance and closeout

Each implementation package requires focused tests plus the canonical full suite、`git diff --check`、exact
file allowlist and native non-Codex JSONL evidence。Only `APPROVE` with no unresolved findings opens the next
named gate。

P3 closes only after IR terminal review and a later EP-backed fresh run reaches the existing five-job success
matrix with a fresh post-run `APPROVE`。Then update dogfood、progress、roadmap and Phase 9 status with both
cleanup-completed failures and this cleanup-blocked incident。

P9_3C1_P3_RETRY_INCIDENT_CORRECTION_RECOVERY_PLAN_READY_FOR_INDEPENDENT_REVIEW_ALL_MUTATION_BLOCKED
