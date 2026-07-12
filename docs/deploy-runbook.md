# Tencent Cloud Deploy Runbook

This runbook defines the manual one-key deploy path for the current Phase 7.2 A0 topology:

```text
Tencent Cloud:
  coordinate.service
  multinexus-discord-bridge.service
  mihomo
  hermes

Mac / Windows:
  agentd processes only
```

The goal is to stop version drift between local development checkouts and `/opt/coordinate` / `/opt/multinexus` on the server. This is intentionally a manual deploy first. GitHub Actions can later call the same scripts after the flow is stable.

## Source Of Truth

- Local development checkouts:
  - `/Users/yinxin/projects/coordinate`
  - `/Users/yinxin/projects/multinexus`
- Server runtime copies:
  - `/opt/coordinate`
  - `/opt/multinexus`
- Canonical secret-free Discord roster authority (committed, reviewed, versioned):
  - `config/agent-registry.toml` in the MultiNexus source tree
- Server secrets and runtime state stay server-local:
  - `/etc/coordinate/coord.env`
  - `/etc/multinexus/discord.env`
  - `/var/lib/coordinate/coord.sqlite3`
  - `/opt/multinexus/agents.toml`

`/opt/*` directories are deployment copies, not development source of truth.
`config/agent-registry.toml` is the only canonical roster; `agents.toml.example`
remains an example and local/server `agents.toml` files remain runtime consumers.

## Manual Deploy

Deploy both services:

```bash
cd /Users/yinxin/projects/multinexus
scripts/deploy-server.sh all
```

Deploy one service:

```bash
scripts/deploy-server.sh coordinate
scripts/deploy-server.sh multinexus
```

Run smoke only:

```bash
scripts/deploy-server.sh status
# equivalent lower-level command:
# scripts/server-smoke.sh
```

Useful options:

```bash
scripts/deploy-server.sh all --no-restart
scripts/deploy-server.sh all --no-smoke
scripts/deploy-server.sh all --allow-dirty
scripts/deploy-server.sh all --host kook-hermes-admin
```

Use `--allow-dirty` only for intentional emergency deployment. Normal deploys should come from a clean working tree.

## What The Deploy Script Preserves

The script does not overwrite:

- `.venv`
- `.env`
- `agents.toml`
- `agents.toml.bak`
- logs
- SQLite/runtime data
- `docs/project-harness/current`
- `VERSION_DEPLOYED`

For `multinexus`, it also restores the server permission model for harness files:

```text
/opt/multinexus/docs/project-harness
  owner: multinexus
  group: coord
  dirs: 2775
  files: 0664
```

This lets `coordinate` update harness/checklist files while the bridge still owns the runtime copy.

## Version Evidence

Every deploy writes:

```text
/opt/coordinate/VERSION_DEPLOYED
/opt/multinexus/VERSION_DEPLOYED
```

Each file records:

- component
- local source path
- branch
- commit
- deployment time
- deploy user and host

Use these when debugging version drift.

## Registry Authority Deploy Rules

MultiNexus deploys use `config/agent-registry.toml` as the canonical,
secret-free roster authority. The authority contains only `id`,
`display_name`, and `discord_user_id`; it never contains tokens, paths,
channels, or host settings.

Deploy ordering for `multinexus` (and for `all` after `coordinate`):

1. Local parity: verify the local runtime `agents.toml` projects exactly to
   `config/agent-registry.toml`.
2. Copy source to `/opt/multinexus` while preserving server-private
   `agents.toml`.
3. Remote parity: verify `/opt/multinexus/agents.toml` projects exactly to the
   copied authority.
4. Authoritative sync: `coord-local workspace agent sync discord-nexus --source
   /opt/multinexus/config/agent-registry.toml --replace`.
5. Committed-state proof: independently read back source metadata,
   authoritative rows, compatibility projection, and effective resolver output
   from `/var/lib/coordinate/coord.sqlite3` and compare to the authority.
6. Write `VERSION_DEPLOYED` and, unless `--no-restart` is set, restart
   `multinexus-discord-bridge`.

`--no-restart` still performs parity validation and authoritative sync.
`--no-smoke` skips only the post-deploy smoke. `--skip-install` does not skip
parity or sync. `status` remains read-only and never syncs.

Failure ordering:

| Failure | Remote source copied | Registry mutated | Version written | Bridge restarted |
|---|---:|---:|---:|---:|
| local authority/runtime mismatch | no | no | no | no |
| remote authority/runtime mismatch | yes | no | no | no |
| Coordinate rejects version/hash/source | yes | no | no | no |
| committed read-back mismatch | yes | possibly committed | no | no |
| version write fails | yes | committed | no | no |
| restart fails | yes | committed | yes | attempted |

When a canonical roster field changes, increment `[registry].version` in the
same reviewed commit. Reusing a version with a different canonical hash,
decreasing the version, or changing `source_id` is forbidden and fails before
service restart.

## Smoke Checks

`scripts/server-smoke.sh` checks:

- `coordinate.service` is active
- `multinexus-discord-bridge.service` is active
- both `VERSION_DEPLOYED` files exist
- `/usr/local/bin/coord-local workspace list` runs and returns valid JSON
- Discord gateway is reachable through the local mihomo proxy
- recent coordinate/bridge logs do not contain known deployment-breaker errors
- coordinate DB can list registered runtime agents
- schema is at least v10 and the `discord-nexus` registry source id/version/hash
  match the deployed `config/agent-registry.toml`
- authoritative entry count and roster hash equal the authority
- no `legacy` registry entries remain
- compatibility `agents_json` and effective resolver output equal the authority
- active overrides, if any, cause the strict parity smoke to fail

## Path To GitHub Actions

GitHub Actions should not invent a separate deployment process. Once manual deploys are stable, CI/CD should call the same scripts:

```text
checkout
run tests
ssh/rsync access setup
scripts/deploy-server.sh all
scripts/server-smoke.sh
```

Recommended future guardrails:

- only deploy from `main` or an explicitly allowed release branch,
- require tests before deploy,
- keep server SSH key in GitHub Secrets with limited scope,
- keep production tokens only on the server,
- record deployed commit SHA in `VERSION_DEPLOYED`,
- post smoke result back to Discord/coordinate.
