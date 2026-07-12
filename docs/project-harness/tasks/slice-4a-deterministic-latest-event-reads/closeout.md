# Slice 4A Durable Closeout

Slice 4A is done/closed. Coordinate `main`/`origin/main` are
`5986cc38d8fa7a46c1cdd1dcb195fcc7043314d9`; MultiNexus completion state is deployed
from `0b37b06`.

## Delivered behavior

- Daemon task status uses `created_at DESC, rowid DESC` for its five-event window.
- Policy lifecycle owner fallback uses the same deterministic tie-breaker for its
  twenty-event window.
- Same-second behavioral tests prove later-rowid window/order and later assignment
  owner selection through the real lifecycle delivery path.
- Exactly four paths changed; no schema, helper, precedence, allowlist or limit changed.

## Review and validation

- Approved plan SHA:
  `dd4f8e5fde556ebd5fac9156230fd3bd05e555863dff1b3a4aacb8f87f051360`.
- Round 1 Kimi session: `019f5776-8b26-7000-9dc1-42e888c72f5f` — rejected the
  non-portable test-package invocation.
- Round 2 Kimi session: `019f577c-a6a3-7000-973e-a08d4070d4cb` — approved revised
  Python 3.14 discovery commands.
- Worker Kimi session: `019f577f-6121-7000-a0d3-d949c25202a9`.
- Worker commit: `5986cc3`; Codex verdict: `APPROVE` with no correction.
- Validation: 39 daemon, 152 policy, 191 focused and 1,574 full tests pass.

## Lifecycle and receipt

- Plan approval: `c470c50e-0d28-43bd-af6e-8b4f03f69c84`.
- Assignment requested/accepted: `56ec2909-2018-41bd-a182-95c107f39242` /
  `4d9cdda3-4a5e-451a-addf-e3c1cfab6576`.
- Worker handoff: `8a9794ec-066b-4558-8d3b-587bf8e83f6c`.
- Closeout/review: `a358acbc-ba1d-40ab-aa42-903c3949ff6f` /
  `5c168fc2-89df-427b-baff-9209bd68ac03`.
- Receipt: `f779f41b-a487-42d4-8f07-981058ec2404`.
- Authorized/claimed/applied: `6a3224ed-f228-482f-9203-ad76966f4ad3` /
  `c180b8df-fd05-4073-9d71-0d4e0abe67fe` /
  `dcefd4dc-2549-497f-9de3-b77af7a358b5`.
- `task.done`/consumed: `44307d1a-2a20-45b3-9830-8ad2560fd8a8` /
  `133b5414-9a44-4cc3-bd16-be56be6ca193`.
- Fingerprint: `01e9b0e3...` -> `c151bdea...`.

## Dogfood evidence

The first revised `plan.ready` payload carried the new full SHA while its server-side
`plan_content_hash` still reflected undeployed old bytes. Codex refused that gate,
deployed the revised docs, and emitted `fa38a7db-c07f-401a-bb0e-55632861c549`, where
both hashes agree. This is direct evidence for Slice 4C/D projection-freshness checks.

Deploy breakers again saw concurrent delivery `sending` state despite successful
VERSION updates and active services. Source/deployed lifecycle replay and receipt
completion required no direct JSON/DB repair. Kimi remained available; GLM fallback did
not trigger.

## Next gate

Slice 4B versioned replace-sync agent registry is next. It requires refreshed authority
measurement across Coordinate and MultiNexus, migration/recovery matrices, a detailed
plan and independent review before implementation.
