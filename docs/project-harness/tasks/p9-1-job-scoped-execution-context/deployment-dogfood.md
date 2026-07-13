# P9-1 Deployment and Managed-Runtime Dogfood

Date: 2026-07-13  
Operator/reviewer: Codex  
Status: deployed and runtime-verified; terminal receipt pending

## Integrated commits

- Coordinate `main == origin/main`:
  `b732159c4a1bbced39dc6ab9cde8841e7959a8cb`.
- MultiNexus `main == origin/main`:
  `066ca74980132ce7d98a9cd315bfeab56574c526`.
- Accepted Coding worker sessions:
  - implementation/corrections:
    `019f5991-928c-7000-bb18-b8395db4e9d9`,
    `019f59b2-0f0e-7000-80a6-433c4a379627`,
    `019f59d3-3363-7000-8e18-914aba5f4b76`,
    `019f59e3-f934-7000-8566-92c858d99453`,
    `019f59ed-25fe-7000-9b99-7ec15882c76c`.

## Deployment evidence

- Pre-deploy Coordinate DB backup:
  `/var/lib/coordinate/backups/coord.sqlite3.p9-1.20260713T053258Z`
  (`coord:coord`, mode `0660`, 3,977,216 bytes).
- Ordered rollout:
  1. Coordinate full reinstall/restart;
  2. installed package import/identity verification;
  3. MultiNexus full dependency install/restart;
  4. four local agentd launchd services restarted.
- Deployed versions:
  - `/opt/coordinate/VERSION_DEPLOYED` = `b732159...`;
  - `/opt/multinexus/VERSION_DEPLOYED` = `066ca74...`.
- Coordinate installed package loads
  `/opt/coordinate/.venv/lib/python3.12/site-packages/coordinate/execution_context.py`,
  reports contract v1, and preserves
  `coordinate.db.create_job is coordinate.job_repository.create_job`.
- MultiNexus runtime loads
  `/opt/multinexus/multinexus/agentd/execution_context.py`, contract v1.
- Post-restart server smoke passed with a deployment-bounded log window.
- Local agentd PID changes:
  - `mac-claude`: `762 -> 90907`;
  - `mac-codex`: `765 -> 90910`;
  - `mac-opencode`: `769 -> 90913`;
  - `mac-omp`: `72041 -> 90916`.

The deploy helper's default ten-minute breaker scan initially reported historical
Discord TLS/reconnect traces from before the rollout. Re-running with the actual
service restart boundaries (`13:33:14` Coordinate, `13:33:51` MultiNexus) passed.
This is the already documented smoke-window limitation, not a P9-1 regression.

## Real managed job

- Request event: `ced328ec-4a97-4052-817e-bb4ab5adb4fc`.
- Job: `request:ced328ec-4a97-4052-817e-bb4ab5adb4fc`.
- Agent: `mac-omp`; attempt token/count `1`.
- Context:
  - `contract_version=1`;
  - `context_id=sha256:bf7f6096230afa8f524c8e9ed4e44666dd8b8b9ca2076002247d443a10575bb9`;
  - `host_id=macbook-local`;
  - `workspace_path=/Users/yinxin/projects/multinexus`;
  - `worktree_path=/Users/yinxin/projects/multinexus`;
  - `harness_root=/Users/yinxin/projects/multinexus/docs/project-harness`;
  - `session_scope_id=request:p9-1-prod-smoke:20260713T053531Z`.
- `job.claimed`: `c9a7f35c-9917-4c15-85f4-e6472566da33` records the same
  context id, host, worktree, scope, and branch.
- Local agentd log proves provider invocation used
  `cwd=/Users/yinxin/projects/multinexus`.
- Job completed in 3,877 ms with exact response
  `P9-1_EXECUTION_CONTEXT_OK`; result JSON repeats the same context id, worktree,
  and scope.
- Terminal events:
  - `job.completed`: `3c91efd3-1356-4475-8713-a28c73b12112`;
  - `agent.reported`: `3c8a0343-6803-48a7-9df7-01fca7b9b493`.
- Reply delivery `5f0bae5f-0d67-48f2-9f2a-5b8b40c86671` was sent once through
  `discord_webhook`, with no error and the exact sentinel payload.
- Both source repositories remained clean after provider execution, except the
  pre-existing user-owned Coordinate `.qoder/` directory.

## Closeout gate

- Result review approval: `223d2f55-ffec-477a-a7ab-b0e294bc0949`.
- Closeout requested: `8b1f410c-8ff1-4d47-8861-16877018e4ae`.
- Final closeout review approval: `c0d82102-66a3-441d-8c2e-f5a3e8516734`.
- Source and deployed checklist SHA before receipt:
  `a023b96fd714467e73afe63e63fc84b91f926d73321d7e1bd61e3ae1716b915b`.

The next operator action is to commit/deploy this exact lifecycle projection, issue
the one-time completion receipt, apply the canonical mark-done files, deploy them,
and consume the receipt.
