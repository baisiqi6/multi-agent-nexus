# Slice 4B1 Plan Review — Round 1

## Verdict

`CHANGES_REQUESTED`

- Reviewed plan SHA:
  `aea4baf2e880c48e278fb4cbbc29a97897761d72e6f3f18ea206ebe554722f61`.
- Coordinate start: `5986cc38d8fa7a46c1cdd1dcb195fcc7043314d9`.
- Provider/model: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- Session: `019f578e-4ec9-7000-8f9a-ebdd329c4c77`.
- JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-s4b1-plan-review/2026-07-12T18-19-31-913Z_019f578e-4ec9-7000-8f9a-ebdd329c4c77.jsonl`.

The reviewer accepted the normalized authority model, source-version conflict rules,
transaction boundary, compatibility-projection boundary, S4-B1/B2 split, allowed paths,
291 focused baseline, 1,574 full baseline and fixture SHA.

## Must-fix

1. Specify exact canonical roster JSON structure, entry order, field normalization and
   UTF-8 hashing.
2. Define v9 legacy backfill for NULL, invalid JSON, duplicate names, missing Discord
   ids and unknown fields.
3. Define strict UTC expiry format, boundary operator, parse failures and read-time
   evaluation.
4. Define daemon refresh before `is_agent`, pre-v10 migration behavior and how natural
   expiry invalidates cached authorization even when revision does not change.

The revised plan must bind a new SHA and receive a fresh verdict.
