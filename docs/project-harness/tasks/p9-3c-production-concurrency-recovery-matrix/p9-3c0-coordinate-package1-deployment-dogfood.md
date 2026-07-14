# P9-3C0 Package 1 Coordinate Deployment and Dogfood

Execution date: 2026-07-15 Asia/Shanghai

## Deployed revisions

- Coordinate source, `origin/main`, and production:
  `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`.
- MultiNexus result-review documentation initially deployed at:
  `777412603053d30480663d120a010b7eaaef4e8f`.
- The deployment introduced no fixture agent, executor source, capacity source, unit,
  job, or lease.

## Pre-deploy gate

The production database reported:

- `PRAGMA integrity_check`: `ok`;
- foreign-key violations: `0`;
- schema: `13`;
- active/total execution leases: `0/0`;
- pending/running jobs: `0`;
- exactly one capacity source: `multinexus.discord.capacity` v1;
- exactly eight policies owned by that source;
- no `p9-3c-fixture-*` agents, bindings, profiles, jobs, or units;
- no `p9-3c0-fixture-*` executor or capacity source.

Both `coordinate.service` and `multinexus-discord-bridge.service` were
`active/running` with `NRestarts=0`.

## Durable recovery evidence

Before deployment, the operator created an online full-database backup and a
capacity-only snapshot:

- `/var/lib/coordinate/backups/coord.sqlite3.p9-3c0-package1.20260714T223204Z`
  - mode: `0600`;
  - SHA-256: `8afab30d7d71b06a499a8f5ba19f25bb91b57abb5b64a7a3c610f1ae313d812e`;
  - integrity/schema/FK violations: `ok` / `13` / `0`;
  - active leases: `0`;
  - captured source set: only `multinexus.discord.capacity` v1.
- `/var/lib/coordinate/backups/capacity.p9-3c0-package1.20260714T223204Z.json`
  - mode: `0600`;
  - file SHA-256:
    `b276d1b9eb5174ad0c0b6bb8633aa16681c7773dc482363511bdf9127f2f99d7`;
  - envelope SHA-256:
    `b9338ef0bbf5308e624b3fe7b0f0efc7b0b5aafe5fccbeaa3c4558b05069315f`;
  - target/source: `multinexus.discord.capacity`;
  - policy count: `8`.

This is a valid single-source recovery artifact. It is not evidence that the current
snapshot/restore contract supports multiple capacity sources.

## Deployment and exact-retry proof

`scripts/deploy-server.sh coordinate --allow-dirty` deployed Coordinate from local
`main`. The only local dirty entry was the user-owned `.qoder/` directory, which the
deploy script explicitly excludes; it was not read, staged, copied, or modified.

The SHA-256 of `src/coordinate/executor_capacity.py` matched across all three locations:

- local source: `465a13fd574594448ec5bc548f3fe4140faedec20478bfc16b14e3c4a7203889`;
- production `/opt/coordinate/src`: the same digest;
- installed production site-packages: the same digest.

The subsequent MultiNexus deployment exercised the canonical source through the new
Coordinate code. Roster and executor syncs were exact retries. Capacity sync returned:

- `source_id`: `multinexus.discord.capacity`;
- `source_version`: `1`;
- `catalog_hash`:
  `3c5b31d17424f3dc12b56d5e0d545f5a46b7d212193465d79c874cb82a9a918d`;
- `changed`: `false`;
- added/updated/removed policy ids: empty;
- unchanged policy ids: the eight canonical executor agents.

This proves the deployed exact-retry path revalidated the production global invariants
without changing the accepted projection. The deployment script also captured and
cleaned its transient capacity snapshot, authority backup, and staging directory.

## Post-deploy state

- Coordinate deployed version: `a7397b9fd2e5bc7101ce9dcc7c9c42ebc6526de5`.
- MultiNexus deployed review-document version: `777412603053d30480663d120a010b7eaaef4e8f`.
- Server smoke: pass.
- Database integrity/schema/FK violations: `ok` / `13` / `0`.
- Capacity sources/policies: one canonical source / eight canonical policies.
- Active/total leases: `0/0`.
- Pending/running jobs: `0`.
- Fixture agent/binding/source/job/unit residue: none.
- Both services: `active/running`, `NRestarts=0`.
- Deployment staging/snapshot/authority-backup residue in `/tmp`: none.
- Bounded post-deploy journal breaker scan: empty.

## Closeout decision

P9-3C0 Package 1 is merged, pushed, backed up, deployed, and accepted. Package 2 may
proceed only through its own detailed bootstrap and independent review. Activating a
second capacity source remains blocked until the snapshot/restore multi-source
compatibility package is independently planned, reviewed, implemented, tested, and
deployed.
