# P9-0A5 Plan Review — Round 1

## Decision

**CHANGES_REQUESTED** for plan SHA-256
`1b7cccbf52a32272a11de7e093ea85605e4870231e75d22a3c673ed324eab657`.

The Kimi reviewer independently confirmed every source measurement, dependency
boundary, key-set relationship, and test baseline, and its textual verdict was
`APPROVE`. Operator cannot accept the attached implementation condition requiring
permanent whole-`FunctionDef`
`ast.dump(node, include_attributes=False)` hashes. Earlier P9-0A3a review established
that whole AST dumps are Python-version-sensitive proof; the accepted package-wide
standard is the portable canonical projection that drops only absent/empty fields.

No implementation or bootstrap is authorized from this round.

## Reviewer identity

- Reviewer/model: `kimi-code/kimi-for-coding-highspeed` through Oh-My-Pi.
- OMP session: `019f574f-afb1-7000-bf51-7b902de537eb`.
- Provider JSONL:
  `/Users/yinxin/.omp/agent/sessions/-Documents-Codex-2026-07-10-ni-work-coordinate-p9-0a5-plan-review/2026-07-12T17-11-07-953Z_019f574f-afb1-7000-bf51-7b902de537eb.jsonl`.
- Provider transition: none; Kimi remained available and GLM fallback was not used.
- Review was read-only; worktree remained clean.

## Accepted evidence

- exact plan SHA and Coordinate start `882c2a1` verified;
- 44 pure top-level functions / 550 span / 543 nonblank verified;
- registry assignment 66 span / 66 nonblank verified;
- 34 supported = 34 rendered = 31 styled plus exact three unstyled verified;
- pure closure excludes DB/delivery/embed/orchestration authorities;
- focused 247/247 and full 1,555/1,555 passed;
- no circular dependency or source-of-truth collapse found.

## Required revision

Specify the exact portable projection used by P9-0A3a/b and P9-0A4a/b:

1. recursively preserve AST node type, non-empty fields, scalar values, contexts, and
   list order;
2. drop only `None` and empty list/tuple fields;
3. serialize as deterministic sorted-key compact JSON and SHA-256 the UTF-8 bytes;
4. use constants generated from reviewed start `882c2a1`; and
5. prohibit permanent proof based on `ast.dump`, `ast.unparse`, git history, or a
   regenerated post-move expected value.

After revision, bind the new full plan SHA in a corrected `plan.ready`, request a fresh
independent review, and accept only a verdict that does not override this projection.
