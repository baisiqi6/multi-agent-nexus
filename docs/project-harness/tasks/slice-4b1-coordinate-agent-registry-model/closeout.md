# Slice 4B1 Durable Closeout

## Final state

- Status: done / closed.
- Approved plan SHA-256:
  `f23210ee9986e4e8d737a43d3abe155f900a59aec7fde117e1bb5b7e63f97fb8`.
- Kimi worker session:
  `019f579b-9317-7000-879a-acfa73577120`.
- Worker commit: `6c340d41e3889088d5b6dbd68ce8956db302ba20`.
- Codex correction commit: `2bf835ff65767e25f3fb3211c0cf46dad0c0f52e`.
- Integrated/deployed Coordinate:
  `ff6b8bf585e4d1e71827e2150ef33c05a82cac1f`.
- Terminal deployed MultiNexus harness:
  `c055382676d6fe2bac304e031620700652228673`.
- Result review: `result-review.md`.

Kimi remained available throughout the implementation; GLM fallback was not used.
Provider-native JSONL was the primary activity record, correlated with the OMP process,
worktree diff, test output and final commit.

## Delivered contract

- schema v10 with normalized source and entry tables plus registry revision;
- atomic v9 `agents_json` legacy backfill and idempotent v10 reopen;
- canonical normalized roster SHA-256 and source id/version conflict rules;
- authoritative replace-sync that deletes absent authoritative/legacy identities while
  preserving explicit overrides;
- mandatory actor/reason override set and explicit remove-override with optional strict
  UTC expiry;
- effective resolution `active override > authoritative > pre-sync legacy`, duplicate
  effective Discord-id rejection and ASCII decimal validation;
- transaction-bound source/entry/revision/projection/audit updates with injected audit
  failure rollback proofs;
- authoritative delta lists plus separately durable `shadowed` evidence;
- per-message daemon refresh before classification, including fail-closed migration or
  resolver errors and read-time expiry; and
- generated `agents_json` compatibility projection plus CLI fixture delta/rewind proof.

## Validation and deployment

Final local evidence under `/opt/homebrew/bin/python3.14`:

- agent registry `40`;
- DB `21`;
- workspace CLI `19`;
- daemon `43`;
- CLI contract `33`;
- root CLI `169`;
- full discovery `1608`;
- `git diff --check` clean;
- old fixture SHA `43e181046d3baa174199e3c02bcbc1ab1fedf83177d5c3725516a839bbb1f9e1`;
- new fixture SHA `0c54732cfd0d7c013ebd0bd9b235d002159e1eac45dd7d6d13f81344ec105d18`;
- permanent S4-B1 rewind restores the old fixture SHA.

Before deployment, production DB schema was v9 and a SQLite backup was written to:

`/var/lib/coordinate/coord.sqlite3.before-s4b1-20260712T190727Z.bak`

After deployment:

- `/opt/coordinate/VERSION_DEPLOYED` = `ff6b8bf...`;
- schema version = 10;
- registry sources = 0, as expected before S4-B2;
- authoritative entries = 0;
- legacy entries = 9;
- compatibility projection = 9 identities;
- registry revision = 0;
- daemon loaded the same nine workspace identities;
- Coordinate and MultiNexus services were active; and
- smoke completed. Historical Discord connection-reset logs recovered before this
  deployment and were not a migration or registry breaker.

## Receipt chain

Receipt: `dca68d10-f805-4cbf-af35-1ac73a8f86d4`.

- authorized: `da4daaa3-88f0-44ed-9c3c-f6cb44c267da`;
- claimed: `5f2ddd92-e14d-4d53-8984-23b0cd5b7d5b`;
- applied: `2d1c899a-9853-42b8-b2ea-7f3fcbd0afb9`;
- task.done: `1284a47e-f551-4abc-b634-62f8485a2037`;
- consumed: `43193273-7a13-4882-b120-832f697ee5da`;
- fingerprint: `3d5112f4...` -> `95f1e399...`.

## Dogfood findings

1. The first local worker handoff correctly failed closed because the local control DB
   had a legacy plan approval without `plan_ready_event_id`. Re-emitting exact-SHA
   `plan.ready` and binding a fresh approval restored the gate; no bypass was used.
2. The first local mark-done-files attempt passed a relative harness root from the
   Coordinate cwd and failed before claim with `harness_fingerprint_unavailable`.
   Replaying with the absolute MultiNexus harness root succeeded on the same receipt.
3. `assignment review-result --decision approve` produced an auditable
   `harness.mutation_failed`; the accepted vocabulary is `approved`. The corrected
   event succeeded. CLI argument choices should eventually expose this earlier.
4. Host-side completion still reports `workspace_id=local` while the control workspace
   is `discord-nexus`. This known split identity remains routed to Slice 4C/D rather
   than being repaired inside B1.
5. The server receipt reported no remote `review.completed` evidence because the
   review event existed in the local control DB, while the deployed harness itself
   carried `review_approved`. Future control-plane convergence should remove this
   redundant evidence split.

## Next boundary

S4-B2 is next. It must receive a fresh detailed plan and independent non-Codex plan
review before implementation. Its scope is the real deployed MultiNexus roster
authority, version metadata, operational sync/deploy wiring, live removal/reload smoke
and cross-repository runbooks; it must not absorb S4-C operation identities or S4-D
doctor/repair behavior.
