# P9-0A5 Event Presentation Registry Extraction

> **Status:** draft / not authorized
>
> This plan does not authorize implementation. A worker bootstrap may be generated only
> after an independent non-Codex reviewer approves this exact plan revision and
> Coordinate records a `plan.approved` event bound to its full SHA-256.

## Identity

- Parent stage: `phase-9-execution-isolation` / `P9-0A`.
- Package id: `p9-0a5-event-presentation-registry`.
- Plan author / architect: Codex.
- Intended plan reviewer: independent Kimi Code Highspeed through Oh-My-Pi; GLM is the
  explicit fallback only on documented Kimi quota/auth/provider failure.
- Intended coding worker: a fresh non-Codex OMP session, preferring Kimi Highspeed and
  falling back to GLM only with explicit JSONL/provider transition evidence.
- Intended code/result reviewer and Operator: Codex.
- Plan path:
  `docs/project-harness/tasks/p9-0a5-event-presentation-registry/plan.md`.

P9-0A1 through P9-0A4b are durably done/closed. This package is the last pre-Slice-4
P9-0A structural extraction. Slice 4, P9-0A6, and P9-1+ remain gated.

## Refreshed preflight

Snapshot on 2026-07-13:

- Coordinate canonical `main == origin/main`:
  `882c2a1487e4102d35c3c1f5b18b4a542be2d3bc`.
- Shared Coordinate checkout has only the pre-existing untracked `.qoder/`; named
  P9-0A3b and P9-0A4a safety stashes remain outside scope.
- MultiNexus canonical `main == origin/main`:
  `d4edd1e07879d19ef1bdc46d82f441116579a599`.
- P9-0A4b is done/closed through receipt
  `1c9269e9-e7b5-442c-b856-d0216d62bdab`.
- `src/coordinate/policy.py`: 1,282 lines.
- `src/coordinate/discord_rendering.py`: 490 lines; not an implementation path here.
- `tests/test_policy.py`: 4,324 lines / 151 tests.
- Focused baseline:
  `tests.test_policy tests.test_discord_rendering tests.test_delivery_cli
  tests.test_cli_contract` = 247 tests passed.
- Full Coordinate baseline: 1,555 tests passed.

Current event-key relationships:

- `SUPPORTED_EVENT_TYPES`: exactly 34 keys;
- `_EVENT_BASE_PAYLOAD_RENDERERS`: exactly the same 34 ordered keys;
- Discord `_STYLING`: 31 keys, all supported;
- explicitly unstyled today: exactly `issue.materialized`, `issue.triaged`, and
  `review.rejected`;
- there are no supported-but-unrendered or rendered-but-unsupported keys.

Measured pure presentation seam:

- 44 pure functions / 550 source-span / 543 nonblank lines;
- registry assignment: 66 source-span / 66 nonblank lines;
- total measured movement: 616 source-span lines plus module imports and an explicit
  unstyled-key constant;
- the 44 functions are the registry call-graph closure (43 functions) plus the existing
  pure compatibility helper `_optional_suffix`;
- `_event_payload`, `_render_event_base_payload`, `_enrich_with_embed`,
  `render_event_payload`, `_delivery_for_message_key`, all DB/delivery/pump logic,
  `PolicyError`, supported-platform policy, and message-key policy remain in
  `policy.py`.

## Problem and evidence

`policy.py` currently combines three different authorities:

1. DB/event/delivery orchestration and skip policy;
2. the public rendering facade, embed enrichment, platform validation, and
   `PolicyError` behavior; and
3. a large pure text/base-payload presentation registry.

The third boundary is already explicit and pure, but its 616 measured lines remain in
the orchestration module. Slice 4 will modify policy projections and partial-operation
visibility; leaving pure presentation in the same file would keep unrelated changes
concentrated.

The 34/34/31/3 relationships are currently implicit across `policy.py` and
`discord_rendering.py`. Adding one event can silently become supported without a base
renderer, rendered without support, or unintentionally unstyled. P9-0A5 must make that
relationship executable without merging the separate support, base rendering, and
Discord styling authorities.

## Goal

In one behavior-preserving worker session:

1. add `coordinate.event_presentation` as the owner of the pure text/base-payload
   functions and renderer registry;
2. keep `coordinate.policy` as orchestration and public rendering facade;
3. preserve private compatibility aliases used by current tests/callers;
4. declare exactly the three intentionally unstyled supported event keys;
5. lock all event-key set relationships and the registry/body structure; and
6. preserve every visible text, header, links, actor field, embed, skip rule,
   message key, error, DB, delivery, idempotency, and CLI behavior.

## Non-goals

- No change to event support, text, localization, truncation, links, headers, actor
  fields, embed styling, platform behavior, skip rules, or delivery creation.
- No modification to `discord_rendering.py`, DB, bus, delivery CLI, schema, daemon,
  harness, completion, transitions, or runtime.
- No new plugin registry, dynamic discovery, renderer classes, inheritance, DI
  container, schema, package split, or dependency.
- No Slice 4 projection behavior, P9-0A6 module review, or P9-1 execution identity.
- No deploy, restart, SSH, production DB/delivery mutation, push, merge, or lifecycle
  mutation by the worker.

## Authority and dependency boundaries

- `coordinate.policy` remains the sole owner of `SUPPORTED_EVENT_TYPES`,
  `SUPPORTED_PLATFORMS`, `PolicyError`, event JSON decoding, support/skip decisions,
  DB reads/writes, delivery creation, pump behavior, message keys, and Discord embed
  enrichment.
- `coordinate.event_presentation` may import only `sqlite3` and typing primitives from
  the standard library. It must not import policy, DB, bus, delivery, Discord rendering,
  CLI, daemon, harness, or runtime modules.
- Policy imports the presentation registry and compatibility names. Presentation never
  imports policy, so dependency direction is one-way.
- `_render_event_base_payload` remains in policy and continues to raise exact
  `PolicyError("unsupported event type: ...")` on a missing renderer.
- `_EVENT_BASE_PAYLOAD_RENDERERS` remains object-identically available through
  `coordinate.policy` for compatibility.
- All 44 moved private functions remain object-identically available through
  `coordinate.policy`; removal of private aliases requires a separate compatibility
  audit.
- `EXPLICITLY_UNSTYLED_EVENT_TYPES` is owned by presentation and is exactly the three
  current no-embed keys. It does not make presentation responsible for Discord styling.

## Proposed changes

### 1. Add `event_presentation.py`

Add `src/coordinate/event_presentation.py` and move without cleanup or semantic rewrite:

- `_base_payload`;
- all text/render helpers from `_job_completed_text` through `_agent_reported_text`,
  excluding DB-bound `_delivery_for_message_key`;
- `_standard_base_renderer` and the three dedicated base renderers;
- `_EVENT_BASE_PAYLOAD_RENDERERS` with exactly its current 34 ordered keys and values;
- `_optional_suffix` as an existing pure compatibility helper; and
- `EXPLICITLY_UNSTYLED_EVENT_TYPES = frozenset({...})` for the exact three current
  unstyled keys.

No moved function body or registry expression may be rewritten for style. Use the same
`sqlite3.Row`, `Any`, and `Callable` annotations so canonical AST projections remain
stable.

### 2. Keep policy as facade

Update `src/coordinate/policy.py` to import and re-export the registry plus all moved
private names. Remove only their original definitions and the now-unused `Callable`
typing import. Keep:

- the literal 34-key `SUPPORTED_EVENT_TYPES` set;
- `_render_event_base_payload` registry lookup and exact `PolicyError` fallback;
- event payload JSON validation;
- embed enrichment through `discord_rendering.render_embed`;
- all orchestration, DB, lifecycle delivery, skip, and pump code.

Do not derive support automatically from the renderer registry. Equality is an
acceptance invariant, not a collapse of two authorities.

### 3. Add presentation boundary tests

Add `tests/test_event_presentation.py` proving:

- all 44 moved functions and the registry are object-identical between policy facade
  and presentation owner;
- policy has no moved `FunctionDef` or registry assignment but retains orchestration,
  `_render_event_base_payload`, `_event_payload`, `_enrich_with_embed`, and
  `_delivery_for_message_key`;
- presentation imports only the approved standard-library modules and has no policy/DB/
  Discord/delivery backedge;
- fresh import orders presentation -> policy, policy -> presentation, and Discord ->
  presentation -> policy succeed in isolated interpreters;
- all 44 moved functions match canonical AST projection hashes generated once from
  reviewed start `882c2a1`;
- the registry assignment matches one canonical AST projection hash generated from the
  same start, covering ordered keys, headers, factories, lambdas, and dedicated values;
- `SUPPORTED_EVENT_TYPES == renderer keys` (34);
- Discord styled keys and explicitly unstyled keys are disjoint and their union equals
  the 34 supported keys;
- explicitly unstyled is exactly the approved three-key frozenset;
- no supported, rendered, styled, or unstyled duplicate/missing key can pass; and
- unknown rendering still raises policy's exact `PolicyError`.

Retain all existing per-event semantic tests as authorities. Modify `tests/test_policy.py`
only if one narrow ownership assertion cannot live in the new boundary file; do not
rewrite existing text snapshots.

### 4. Preserve behavior with independent structural proof

Before accepting implementation, Codex independently compares all 44 moved
`FunctionDef` ASTs and the registry assignment against start `882c2a1`, inspects exact
paths/imports, reruns relationship calculations, and runs focused/full tests. Worker
self-report or a regenerated expected snapshot is not sufficient.

## Allowed paths

Production:

- `src/coordinate/policy.py`;
- `src/coordinate/event_presentation.py` (new).

Tests:

- `tests/test_event_presentation.py` (new);
- `tests/test_policy.py` only for one narrow compatibility/ownership assertion if the
  new boundary file cannot contain it.

Any need to modify `discord_rendering.py`, delivery CLI/tests, DB, bus, service, schema,
daemon, harness, completion, transitions, runtime, packaging, or another path stops the
worker and returns the plan for review.

## Failure and recovery matrix

| Failure | Required response |
|---|---|
| Supported/rendered key sets differ | Restore exact 34-key equality; do not bless drift. |
| Styled plus explicit-unstyle union differs | Restore exact 31 + 3 partition. |
| Registry AST differs | Restore keys/order/factories/lambdas; do not regenerate proof. |
| Moved function AST differs | Restore exact body; semantic cleanup is outside scope. |
| Unknown event no longer raises PolicyError | Keep fallback in policy facade. |
| Embed/text/link/output snapshot changes | Restore movement-only implementation. |
| Presentation imports policy/DB/Discord | Stop and remove the backedge. |
| Existing private alias disappears | Restore direct compatibility re-export. |
| Test touches real DB/delivery/network | Redesign with in-memory rows/mocks. |
| Another path is required | Stop and request plan revision. |
| Kimi quota/auth/provider fails before edits | Preserve JSONL evidence and restart with GLM. |
| Provider fails after partial edits | Correlate JSONL/process/diff and attribute any fallback. |

## Acceptance matrix

| Case | Expected evidence |
|---|---|
| Scope | exactly two production paths plus approved boundary tests |
| Pure seam | 44 functions and one registry assignment moved; no DB/Discord import |
| Compatibility | policy aliases object-identical; public orchestration remains |
| Body stability | 44 canonical AST hashes match reviewed start |
| Registry stability | one canonical registry AST hash matches reviewed start |
| Key authority | 34 supported = 34 rendered = 31 styled + exact 3 unstyled |
| Error behavior | missing renderer raises exact policy `PolicyError` |
| Import direction | policy -> presentation; no backedge; cold orders pass |
| Regression | focused does not drop from 247; full does not drop from 1,555 |
| Isolation | no production DB, delivery, harness, SSH, deploy, or lifecycle side effect |

## Validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_event_presentation tests.test_policy tests.test_discord_rendering \
  tests.test_delivery_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Record exact commits/paths, 44 function hashes, registry hash, 34/34/31/3 key sets,
focused/full counts, import/alias/error evidence, provider session/JSONL, and any
Kimi-to-GLM transition.

No runtime deploy or live event smoke is required for implementation acceptance.
Receipt-aware lifecycle closeout may deploy canonical harness state after code review;
that is an Operator action, not worker authority.

## Rollout, rollback, and worker boundaries

- Fresh isolated Coordinate worktree from exact reviewed `882c2a1`.
- One local non-Codex worker commit; Codex may require attributed corrections.
- Fast-forward integration only from the reviewed start; rollback is a normal revert.
- Worker must not amend, push, merge, deploy, restart, SSH, mutate lifecycle, use a
  subagent, or edit outside the allowed paths.
- Stop on behavior/key/AST/import/scope drift, real side effect, or unexpected provider
  transition.
