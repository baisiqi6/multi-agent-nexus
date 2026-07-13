# Slice 4D Durable Closeout

Slice 4D is implemented, adversarially reviewed, deployed, production-dogfooded, and
closed through a consumed completion receipt. The default workspace doctor now treats
registry, split-operation, task-mirror, receipt, lifecycle evolution, and approved plan
supersession evidence as one read-only diagnostic surface without inventing repair
authority.

## Reviewed implementation

- Approved post-deploy correction plan SHA-256:
  `635b54c74e7705aaa469e06e6bf1609027251b75ffa7319e4b9ceba0ef39be94`.
- Kimi implementation/review JSONL sessions:
  - `019f58d3-32b0-7000-b2a9-30d961820700`;
  - `019f5913-74da-7000-a599-522e8db880ec`;
  - `019f591a-df49-7000-a7c3-716686aa32ba`;
  - `019f5924-d9fd-7000-9537-0cf3a099e558`.
- Final reviewed/integrated Coordinate head:
  `15020c2204e8e05c6304f6ed83a5fed83ad12eae`.
- Post-deploy result approval event:
  `141943ca-392a-42ac-9714-68eed23f4543`.
- Review artifacts: `post-deploy-result-review-round1.md` through
  `post-deploy-result-review-round5.md`.
- Provider stayed `kimi-code/kimi-for-coding-highspeed`; no Kimi quota/auth/provider
  failure occurred, so GLM fallback was not used.

Five post-deploy result-review rounds closed forged supersedes acceptance, unknown
top-level-field acceptance, `artifacts.plan` drift, legitimate `lease` false positives,
and non-split null/double-read plan SHA evidence.

## Verification

- Focused onboarding/projection/split gate:
  `241 passed, 43 subtests passed`.
- Full suite: `1864 passed, 449 subtests passed, 9 failed`; all nine are the known
  historical eight CLI-contract fixture hashes plus one issue-CLI AST hash.
- Changed-path ruff, compileall, `git diff --check`, `cli.py` byte identity, and
  repository `events.jsonl` boundary checks passed.
- Independent probes proved:
  - lifecycle `lease` remains clean;
  - arbitrary unknown top-level fields fail closed;
  - `artifacts.plan` drift fails closed;
  - forged split retry provenance conflicts;
  - missing non-split plan produces stable `ValueError` before any DB write.

## Production deployment and doctor

- Predeploy DB backup:
  `/var/backups/coordinate/coord-20260713T020019Z.sqlite3`.
- Source and backup integrity: `ok` / `ok`.
- Coordinate deployed/installed: `15020c2`.
- Runtime import:
  `/opt/coordinate/.venv/lib/python3.12/site-packages/coordinate/__init__.py`.
- Code schema / production DB user version: `11` / `11`.
- MultiNexus completion projection deployed at `9281f84` before record consume.
- Services active; repeated `server smoke OK`.
- Full production doctor before closeout:
  `rc=0`, `projection_ok=true`, `errors=0`, 2 legitimate warnings, 12 infos.
- Full production doctor after closeout:
  `rc=0`, `projection_ok=true`, `errors=0`, 2 legitimate warnings, 13 infos.
- Expected approved supersession info:
  operation `7b393f8a-7d27-4a4e-8a68-44cd5a8923fd` for this task.
- Raw server evidence:
  - `/tmp/s4d-production-doctor-after-15020c2.json`;
  - `/tmp/s4d-production-doctor-after-closeout.json`.
- Durable summary: `post-deploy-production-evidence.md`.

The old S4-C2 lifecycle false positive is absent. No `--no-projections`, whitelist,
repair mode, direct checklist edit, or production DB edit was used.

## Completion receipt

- Receipt: `ee38b348-b2fb-4ad1-b9af-dc01f4d6c144`.
- Authorized event: `a685f448-c233-49fd-93a4-b13c06598792`.
- Claimed event: `1f18e2df-e5fa-43a9-bccf-14389c2346bc`.
- Applied event: `b9b6ff2d-04e1-4c4e-b4dc-6ce40282046a`.
- Fingerprint:
  `8447cf7a70386b598a39ffc6659d86be5fe83efe11d10df8b20962f74e37cf7c`
  -> `86bdeac6397f24d301feb87a989dff43d5fb7d5882a578286a901b568a87181e`.
- Terminal `task.done`: `a27c7d71-e45a-4c8f-8079-d8bab5404a01`.
- `completion.consumed`: `e084f1e0-f74f-4c26-8e48-1516a5604e1d`.

Source and deployed checklist bytes were aligned by replaying the approved lifecycle
transition through canonical `harnessctl`, committing, and deploying before receipt
issuance. The receipt then completed without a fingerprint mismatch.

## Dogfood result

Remote Coordinate lifecycle mutations remain vulnerable to being overwritten by a
later canonical source deployment when the source harness has not replayed the same
transition. S4-D diagnosed operation history correctly, but this source/control/deploy
projection ordering remains an Operator UX gap for Phase 9/P9-0A6 boundary planning.

