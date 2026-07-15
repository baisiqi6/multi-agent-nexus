# P9-3C0 Snapshot/Restore Compatibility — Coordinate C1 Deployment and Dogfood

Execution date: 2026-07-15 Asia/Shanghai

## Exact revisions

- Coordinate local `main`, `origin/main`, and production:
  `1e36d9b6ccd26a331ed655806f1c9ef735453685`.
- MultiNexus result-review documentation on local `main` and `origin/main`:
  `8dba5c376ca822c37b8f302c552b1e016bc89a41`.
- Production MultiNexus runtime remains at
  `aec171f22180cc8b7405762ff79cf93c155cc243`; C1 intentionally deploys only
  Coordinate. MultiNexus runtime synchronization is the separately reviewed C2 gate.

## Pre-deploy gate

The production database and services reported:

- `PRAGMA integrity_check`: `ok`;
- schema: `13`;
- foreign-key violations: `0`;
- exactly one capacity source: `multinexus.discord.capacity` v1;
- exactly eight policies owned by the canonical source;
- active/total leases: `0/0`;
- pending/running jobs: `0`;
- fixture agents, runner profiles, executor sources, capacity sources, jobs, and
  `p9-3c-fixture-*.service` units: all `0`;
- `coordinate.service` and `multinexus-discord-bridge.service`: `active/running`,
  both with `NRestarts=0`.

The pre-deploy server smoke passed, including deployed version files, Coordinate CLI,
Discord gateway reachability, strict registry authority verification, and bounded
journal breaker scan.

## Durable full-database backup

Before deployment, the operator created an online SQLite backup:

- path:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-3c0-snapshot-c1.20260715T001826Z`;
- mode: `0600`;
- SHA-256:
  `8afab30d7d71b06a499a8f5ba19f25bb91b57abb5b64a7a3c610f1ae313d812e`;
- integrity/schema/FK violations: `ok` / `13` / `0`.

## Deployment

`scripts/deploy-server.sh coordinate --allow-dirty` deployed the exact reviewed
Coordinate revision. The only known local untracked entry was the user-owned
`.qoder/` directory; the deploy script excludes it, and it was not read, staged,
copied, or modified.

Production `/opt/coordinate/VERSION_DEPLOYED` records:

- branch: `main`;
- commit: `1e36d9b6ccd26a331ed655806f1c9ef735453685`;
- deployed at: `2026-07-15T00:18:34Z`.

The SHA-256 of `executor_capacity.py` matched across all three locations:

- local reviewed source:
  `ce8ad4dd4546265f3dbc7a4854b9bb9fd3d3e3537942a20f5ac11d443ac862fe`;
- production `/opt/coordinate/src` source: same digest;
- installed production site-packages: same digest.

## Inert v2 capture proof

The deployed MultiNexus helper called the new Coordinate capture implementation against
the live production DB. No restore was invoked.

Artifact:

- path:
  `/var/lib/coordinate/backups/capacity.p9-3c0-snapshot-c1.20260715T001940Z.json`;
- mode: `0600`;
- file SHA-256:
  `384b9a18a815d460addd59488786a891264ed2d7b811433b2d0e728214ca5f53`;
- inner `snapshot_sha256`:
  `8511517c92d02c494e181a4e813eed7b088aea3a660f49274af18b8344b19e79`;
- `contract_version`: `2`;
- target: `multinexus.discord.capacity`;
- captured target policy count: `8`;
- preserved source/policy count: `0/0`.

The operator independently verified that the artifact bytes were canonical JSON, the
inner digest matched, the exact top-level and inner semantics were v2, and the capacity
source/policy projection was field-for-field identical before and after capture.

This is production evidence for single-source v2 capture/readback only. It is not a
live restore proof and does not authorize a second source.

## Post-deploy state

- Coordinate source, remote branch, deployed version, production source file, and
  installed module all identify the reviewed C1 revision.
- Server smoke: pass.
- Database integrity/schema/FK violations: `ok` / `13` / `0`.
- Capacity sources/policies: one canonical source / eight canonical policies.
- Active/total leases: `0/0`.
- Pending/running jobs: `0`.
- Fixture agents, profiles, sources, jobs, and units: none.
- Both services: `active/running`, `NRestarts=0`.
- Coordinate deployment staging residue: none.
- Bounded post-deploy journal breaker scan: empty.

## Closeout decision

Coordinate C1 is reviewed, merged, pushed, backed up, deployed, and accepted. The
production restore prohibition was preserved.

The next compatibility step is C2: update MultiNexus deploy-contract fixtures and add
the reviewed multi-source capture/rollback/fail-closed matrix. A second production
capacity source and P9-3C1 remain blocked until C2 and the isolated two-source proof
close independently.
