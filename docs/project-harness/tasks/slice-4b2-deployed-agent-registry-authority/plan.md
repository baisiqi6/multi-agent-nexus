# Slice 4B2 Deployed Agent Registry Authority

> Detailed implementation plan. Implementation remains unauthorized until an
> independent non-Codex reviewer approves this exact revision, Coordinate records the
> approval, and a fresh worker bootstrap binds the approved SHA.

## Identity

- Package: `slice-4b2-deployed-agent-registry-authority`.
- Stage: Slice 4B, second and final package.
- Required MultiNexus start:
  `2725b108c0d668db3fcba52679ae609d16e0e202`.
- Required Coordinate start:
  `ff6b8bf585e4d1e71827e2150ef33c05a82cac1f`.
- Plan reviewer and coding worker: Kimi Code Highspeed through Oh-My-Pi; GLM is fallback
  only after documented Kimi quota/auth/provider failure.
- Operator and result reviewer: Codex.

## Goal

Make the deployed MultiNexus Discord roster a source-controlled, secret-free,
versioned authority and make normal deployment fail closed unless the private runtime
configuration represents exactly that authority. A successful MultiNexus deployment
must perform Coordinate's S4-B1 authoritative replace-sync, verify the committed
source identity/version/hash/revision/effective roster, and expose enough evidence for
an operator to distinguish a deployed authority from stale legacy projection.

This package closes the deployment half of S4-B. It does not change Coordinate's v10
schema or resolver contract, and it does not turn host-specific private runtime
configuration into a second canonical roster.

## Reviewed current state

At the required starts:

- Coordinate v10 supports versioned authoritative replace-sync, auditable overrides,
  effective resolution, compatibility projection and per-message daemon refresh.
- Production is on schema v10 but still has nine `legacy` entries and no authoritative
  source row because B1 intentionally preserved authorization before B2.
- local and server-private `agents.toml` now contain the same ten normalized identities
  and Discord IDs, including `pad-jarvis`; neither file contains `[registry]` metadata.
- `scripts/deploy-server.sh` deliberately preserves `/opt/multinexus/agents.toml`, copies
  no canonical roster artifact, and never invokes `workspace agent sync`.
- `scripts/server-smoke.sh` lists the unrelated runtime `agents` table but does not
  inspect authoritative source metadata, entry kinds, compatibility projection or
  effective-roster parity.
- `agents.toml.example` describes private host runtime configuration and is not an
  exact deployed roster authority.
- `docs/project-harness/runbook.md` still demonstrates workspace `multinexus`, optional
  merge-sync and private `agents.toml`; the active workspace id is `discord-nexus` and
  B1 requires `--replace` plus valid `[registry]` identity/version.

## Authority model

### 1. One canonical, secret-free roster artifact

Add tracked `config/agent-registry.toml` containing only:

```toml
[registry]
id = "multinexus.discord"
version = 1

[[agents]]
id = "..."
display_name = "..."
discord_user_id = 123
```

and corresponding `[[external_agents]]` entries. The committed v1 roster is exactly
the ten normalized identities currently shared by local and server runtime configs.
It must contain no token, token environment name, system prompt, executable path,
working directory, channel, webhook, service-manager setting or other host detail.

The authority file is canonical for authorization identity, display name, managed vs
external kind and Discord user id. Private local/server `agents.toml` files remain
runtime configuration consumers and may contain additional host-specific fields, but
their registry projection must equal the committed authority before deployment.
`agents.toml.example` remains an example, not the authority.

Changing any canonical roster field requires incrementing the integer authority
version in the same reviewed commit. Reformatting, comments and unrelated unknown
fields do not change Coordinate's canonical hash and therefore do not require a
version bump. Reusing one version with a different canonical hash, decreasing the
version, or changing source id is forbidden and must fail before service restart.

### 2. Reusable parity verifier

Add one small MultiNexus module with a CLI surface that reads the authority and a
private runtime TOML, projects only Coordinate's canonical registry fields, and exits:

- zero with safe JSON evidence when source metadata is valid, both projections are
  exact, and neither projection has parse/duplicate/missing-ID errors;
- non-zero with redacted field-level diagnostics when an identity is added, removed or
  changed, an entry lacks `discord_user_id`, source metadata is invalid, or duplicates
  exist.

The verifier must not import Coordinate as a runtime dependency and must not print raw
TOML entries or inspect/emit token values. Its normalization and canonical SHA-256
must match the B1 contract exactly: trimmed non-empty ids/display names, ASCII decimal
positive Discord IDs, fixed `managed`/`external` kinds, id-sorted canonical JSON.

The authority side must require `[registry]`; the private runtime side must not require
or trust `[registry]`. Runtime-only extra fields are ignored. Tests must prove parity
with secrets present in the private fixture without allowing those values into stdout,
stderr or exception text.

Avoid a new general configuration framework: the module owns only the registry
projection/parity seam. Existing bridge/agentd config loading remains unchanged.

### 3. Fail-closed deployment sequence

For a MultiNexus deployment, `scripts/deploy-server.sh` must:

1. validate the local clean checkout and local private `agents.toml` against the
   tracked authority before copying or mutating remote state;
2. copy the tracked authority with normal source files while continuing to preserve
   the server-private `agents.toml`;
3. validate the deployed authority against `/opt/multinexus/agents.toml` before writing
   `VERSION_DEPLOYED` or restarting `multinexus-discord-bridge`;
4. invoke production `/usr/local/bin/coord-local workspace agent sync discord-nexus
   --source /opt/multinexus/config/agent-registry.toml --replace`;
5. treat the sync result only as mutation acknowledgement, then open a new production
   DB connection through the installed Coordinate package and independently read back
   the committed source row, workspace revision, authoritative/legacy/override rows,
   compatibility projection and effective resolver output; compare every canonical
   field and hash to the deployed authority; and
6. only then write the version marker and restart the bridge when restart is enabled.

Local preflight uses the effective `MULTINEXUS_SRC/agents.toml`; a missing private file
is a deployment error. Remote validation and sync run with the minimum account/command
needed to read the private config and production Coordinate DB. The read-after-write
gate must use the deployed Coordinate venv and public resolver functions where
available; a focused read-only SQL query may retrieve source/revision/entry-kind
metadata that has no existing API. It must not call sync twice as a substitute for
committed-state proof. Output must contain only safe registry evidence.

B1 refresh is synchronous at the next inbound message: the daemon opens/resolves the
committed DB state before classifying that message. There is no asynchronous cache
propagation interval for the deploy script to poll. Therefore the deployment gate
proves committed state, while closeout separately proves unchanged service PID and a
post-sync same-process refresh. Neither the sync response nor a timed sleep may be
reported as daemon acknowledgement.

`--no-restart` still performs parity validation and authoritative sync because registry
correctness is a data-plane deployment invariant, not a restart side effect.
`--no-smoke` skips only the post-deploy smoke. `--skip-install` does not skip parity or
sync. `status` remains read-only and never syncs.

Failure ordering is explicit:

| Failure | Remote source copied | Registry mutated | Version written | Bridge restarted |
|---|---:|---:|---:|---:|
| local authority/runtime mismatch | no | no | no | no |
| remote authority/runtime mismatch | yes | no | no | no |
| Coordinate rejects version/hash/source | yes | no | no | no |
| committed read-back mismatch | yes | possibly committed | no | no |
| version write fails | yes | committed | no | no |
| restart fails | yes | committed | yes | attempted |

The last three cases must emit an actionable stage name and must never claim a complete
deployment. S4-D will diagnose/repair broader partial-operation state; B2 must not add
an automatic rollback that invents or downgrades authority.

Deploying `coordinate` alone does not sync the MultiNexus roster. Deploying `all`
deploys Coordinate first, then follows the MultiNexus sequence above.

### 4. Production smoke and evidence

Extend `scripts/server-smoke.sh` with read-only v10 registry checks for workspace
`discord-nexus`:

- schema is at least v10;
- source id/version/hash and workspace revision read from a fresh connection exist and
  match the deployed tracked authority;
- authoritative entry count and normalized roster/hash equal the tracked authority;
- there are no remaining `legacy` entries after the first B2 deployment;
- compatibility `agents_json` and effective resolver output equal the authority when
  no active override shadows it;
- active overrides, if any, are reported safely and cause the strict parity smoke to
  fail rather than being silently ignored;
- existing service/version/CLI/proxy/log/runtime-agent checks remain.

The smoke must derive expected values from the deployed tracked authority, not embed a
second list or hash in shell code. SQL/JSON output must never include secret-bearing
private config fields.

Add a dedicated safe status command or verifier mode only if it materially reduces
duplicate shell parsing. Do not create a second write path.

### 5. Live removal/reload proof without production authorization risk

Production closeout must prove the first authoritative sync converts the nine legacy
rows to ten authoritative identities and that the running Coordinate service was not
restarted for registry visibility. Record service PID/start timestamp before and after
the MultiNexus-only deploy and verify they are unchanged. Correlate at least one normal
post-sync inbound agent message with a Coordinate event/log after the committed sync;
do not generate a privileged synthetic production identity or claim that PID stability
alone proves message classification.

Do not temporarily remove or remap a real production identity. Instead, on the server:

1. create a new empty isolated v10 DB and workspace under a root-owned smoke directory;
   never copy production rows, credentials, event payloads or workspace state;
2. use the deployed Coordinate binary with temporary v1 and v2 authority fixtures;
3. keep one sidecar daemon/resolver process alive across both syncs;
4. prove v1 authorizes two synthetic identities, v2 removes one, and the same process
   observes the removal without restart/manual cache reset;
5. prove same-version/different-hash and lower-version attempts fail without mutation;
6. remove the isolated directory/process after preserving redacted evidence.

The sidecar must not connect to Discord, use production tokens, mutate the production
workspace or leave a registered smoke workspace in the production DB. Tests may
implement the same-process probe through a purpose-built test helper; production code
must not gain a hidden repair/debug mutation command.

## Documentation

Update:

- `agents.toml.example` to point operators to the separate authority and explain that
  every deployed runtime roster entry needs a Discord user id and exact parity;
- `docs/deploy-runbook.md` with source-of-truth, version-bump, deploy ordering, failure
  and recovery rules;
- `docs/project-harness/runbook.md` to use workspace `discord-nexus`, the tracked
  authority path and required `--replace`;
- `docs/project-harness/dogfood-feedback.md` and package closeout with actual plan SHA,
  provider/session JSONL, commits, deployed versions, source metadata, PID evidence,
  registry transition and sidecar cleanup;
- Slice 4 overview/progress/checklist only through normal reviewed lifecycle changes.

Do not commit or print either real private `agents.toml`, `.env`, token values or raw
service environment.

## Allowed paths

MultiNexus production/configuration:

- `config/agent-registry.toml`;
- one new focused module under `multinexus/` for registry projection/parity;
- `scripts/deploy-server.sh`;
- `scripts/server-smoke.sh`;
- `agents.toml.example`.

Tests:

- one focused Python test module for parity/canonicalization;
- focused deploy/smoke contract tests that execute scripts with fake `ssh`, `git`,
  `tar` and safe fixtures, or an equally deterministic shell contract harness;
- existing MultiNexus suites affected by config/import boundaries.

Documentation/harness:

- `docs/deploy-runbook.md`;
- `docs/project-harness/runbook.md`;
- `docs/project-harness/dogfood-feedback.md`;
- `docs/project-harness/progress.md`;
- `docs/project-harness/tasks/slice-4-projection-hardening/plan.md`;
- this package directory and normal generated harness/checklist/current artifacts.

Coordinate changes are not expected. A newly discovered B1 defect requires stopping,
documenting the exact blocker and opening a separately reviewed correction; do not
silently expand B2 into schema/resolver work.

## Tests and acceptance

Before worker closeout:

1. focused parity tests cover normalization, exact parity, managed/external kind,
   missing/invalid/duplicate ids, missing source metadata, version typing, roster drift,
   and redaction of secret-bearing runtime fixtures;
2. deploy contract tests prove local mismatch performs no SSH mutation, remote mismatch
   performs no sync/restart/version write, and success orders remote parity → sync →
   evidence → version → restart → smoke;
3. contract tests prove `--no-restart`, `--no-smoke`, `--skip-install`, component-only
   and `all` semantics above;
4. smoke contract tests prove source/hash/count/entry-kind/projection/effective parity
   and active-override failure;
5. full MultiNexus tests pass; focused Coordinate B1 registry/daemon tests pass unchanged;
6. both repositories are clean except the known unrelated Coordinate `.qoder/`, and
   reviewed commits are pushed before deployment;
7. production MultiNexus deploy succeeds from a clean reviewed commit, production
   registry becomes source `multinexus.discord` v1 with ten authoritative and zero
   legacy entries, strict server smoke passes, and Coordinate PID/start time is stable;
8. isolated server sidecar proves same-process v1→v2 removal, conflict/rollback
   rejection and complete cleanup;
9. `harnessctl validate` and `harnessctl doctor` pass; result review, closeout and
   completion receipt record exact evidence.

## Explicit non-goals

- No Coordinate schema, resolver, daemon, CLI or migration redesign.
- No automatic source takeover, version rollback, registry repair or secret sync.
- No deployment of local private `agents.toml` over the server file.
- No GitHub Actions/CD implementation.
- No provider routing, scheduler, worktree lease or Phase 9 execution-isolation work.
- No S4-C split-operation IDs/fingerprints or S4-D doctor repair implementation.

## Review stop conditions

The plan reviewer must request changes if the design introduces another canonical
roster, trusts private runtime metadata as authority, permits deploy after parity/sync
failure, prints secret-bearing configuration, silently skips roster entries, rewrites
production authorization for a removal demo, weakens B1 version/source rules, or lacks
deterministic failure-order tests.
