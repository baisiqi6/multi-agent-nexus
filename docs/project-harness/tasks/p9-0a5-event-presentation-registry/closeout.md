# P9-0A5 Durable Closeout

P9-0A5 is done and durably closed. Coordinate `main` and `origin/main` are
`084419c`; MultiNexus canonical/deployed completion state is `b562533`.

## Delivered boundary

- `src/coordinate/event_presentation.py` owns 44 pure presentation functions and the
  34-key `_EVENT_BASE_PAYLOAD_RENDERERS` registry.
- `policy.py` re-exports those identities and retains `SUPPORTED_EVENT_TYPES`,
  `PolicyError`, JSON/embed/message-key behavior, DB, delivery, skip, and pump authority.
- `EXPLICITLY_UNSTYLED_EVENT_TYPES` contains only `issue.materialized`,
  `issue.triaged`, and `review.rejected`; it is partition evidence, not styling
  authority.
- Permanent tests use pre-edit `ast.iter_fields` canonical projections for 44 function
  nodes plus the registry and prove three cold import orders.
- Exact production/test paths: `src/coordinate/policy.py`,
  `src/coordinate/event_presentation.py`, `tests/test_event_presentation.py`.

## Review and validation

- Round 2 Kimi plan review session: `019f5756-1931-7000-8b91-1c65ca183565`.
- Approved plan SHA-256:
  `f8507735838a22b3d7c69982f9fed9493e09caf4ab1b8b709f4085d12fc3c1c2`.
- Plan approval event: `9c58080d-bf46-4a2b-97ae-1dd15a747071`.
- Kimi worker session: `019f5760-6411-7000-8b40-45d5cd2e7ec7`.
- Worker commit: `fa79fa6`; Codex correction: `084419c`.
- Codex removed two untracked shell-redirection artifacts and closed the new test's
  in-memory SQLite connection before approval.
- Python 3.14 known-good validation: 264 focused and 1,572 full tests pass; the full
  count is the reviewed 1,555 baseline plus 17 new boundary tests.
- Result review: `result-review.md`.

## Lifecycle and receipt

- Assignment requested: `fe7dd17a-2a0f-4f48-a2d5-a0942aefd248`.
- Assignment accepted: `16041a93-8dd2-49ee-8221-7de347668149`.
- Worker handoff prepared: `c920e626-393c-457c-9e77-e9c7801dfc3b`.
- Closeout requested: `354f6d5d-e868-4a11-a2f2-ef1ae4169639`.
- Review approved: `be53bdc5-8fdd-471d-bc76-668853505cb1`.
- Completion receipt: `8529a3be-3226-4723-a7e5-584eea24d6ea`.
- Authorized: `3e9f0034-e6a1-47f3-9c8d-a3f812ddf2be`.
- Claimed: `0ca9228b-d630-4e7b-9161-6150abef1010`.
- Applied: `43a84928-a8cc-4cdb-9d6a-2cfded56419d`.
- `task.done`: `d85dc7f5-3922-4aea-b28a-30e53b2a6ec9`.
- Consumed: `0aa093bf-d91f-4a6c-85a1-e4746332e11c`.
- Fingerprint: `214282df...` -> `9ec79aec...`.

Receipt `98ecaa84-f87e-435e-987c-20a01515e1c2` was issued before source/deployed
lifecycle replay and rejected before claim because its fingerprint did not match the
source item. It was abandoned without mutation; the successful receipt above was
issued after both projections matched.

## Dogfood findings routed forward

1. The generic Coordinate worker handoff still projected `/opt/multinexus` and the
   historical workspace branch instead of the isolated Coordinate worktree. The
   source-controlled bootstrap prevented a wrong-repository edit.
2. Running host-side `mark-done-files` through `coord-ssh` executes on the server and
   cannot consume Mac paths; the correct split is local files half with remote
   preflight/claim/apply.
3. The host result again reported harness project `workspace_id=local` while the
   control workspace is `discord-nexus`.
4. The deployment breaker again exited nonzero on a recovered concurrent-pump race and
   historical Discord connectivity logs even though VERSION was updated and services
   were active. Delivery `124750ce-28ce-4aac-8edc-7501fe1a6002` is authoritatively
   `sent`, with a platform message id and no last error.
5. The direct assignment delivery `394df085-83a3-45d6-a8ed-0e25f5d94331` remains
   `pending`; two earlier A5 review deliveries `dc914163...` and `4c3b2a8b...` are
   `sent` with no last error.

These are Slice 4 projection/split-operation and runtime-delivery hardening evidence;
none was hidden inside the movement-only P9-0A5 code package.

## Next gate

Slice 4 is next. Refresh its existing overview against Coordinate `084419c` and the
current receipt/delivery evidence, write the package-level detailed plan, obtain an
independent non-Codex plan review, record Coordinate approval, and only then generate a
fresh implementation bootstrap.
