# P9-3C1 P2 Inert Production Controller — Independent Plan Review Round 1

状态：`APPROVE_WITH_P2_NOTES_PLAN_REVISED_FRESH_REVIEW_REQUIRED`

日期：2026-07-16 Asia/Shanghai

## 1. Exact reviewed inputs

- Measurement SHA-256：
  `103791a22f66a1f927e40347eacf60fa369c5537f81108f098e18faea84a6d87`。
- Round 1 reviewed plan SHA-256：
  `461ae6750611563994512cb84227ba77c19ca7cbc4c4a9c068e5e22ff06951e6`。
- MultiNexus base：`7cd1c049d3157a778d79a0a69981032b2c9b2a02`。

## 2. Reviewer routing evidence

Primary Claude Code attempt used required `--model sonnet`。Native stream：

`sessions/p9-3c1-p2-inert-production-controller-plan-review-round1-claude-kimi/reviewer-stream.jsonl`

SHA-256：`e03cac42f1d36472bfa22fae0c2c730bdb1b131f9f272fa0e9c4a61d52b17ef5`。
It returned Kimi quota `403` before any tool/repo write。The init label
`claude-sonnet-4-6` is not counted as an actual reviewer result。

Fallback reviewer native session：

`sessions/p9-3c1-p2-inert-production-controller-plan-review-round1-deepseek-v4-pro/omp-session/2026-07-16T02-04-45-540Z_019f68ab-5064-7000-9062-bc89305da521.jsonl`

- session id：`019f68ab-5064-7000-9062-bc89305da521`；
- provider/model：`deepseek/deepseek-v4-pro`；thinking `high`；
- session SHA-256：
  `0687d76d20298580cba323725dfd4990b2b56d3480653c58525a8b4906198df4`；
- rendered output SHA-256：
  `c9326fe92cb79390bf2127cb3faf64432d270d54084a2765b7906ca2ae27ef1b`。

Reviewer read the measurement、plan、parent plan、agentd/helper/deploy source and adjacent tests。No
repo write、test mutation、SSH or production action occurred。

## 3. Verdict

```text
VERDICT: APPROVE
P0: None
P1: None
```

Approval means the reviewed Round 1 plan was safe enough to open bootstrap generation。Reviewer also
reported several P2 clarity/residual notes。Operator elected to harden the plan before bootstrap，so this
approval does not cover the revised bytes。

## 4. P2 notes and disposition

1. `production-render` interface/manifest-vs-CLI ambiguity：`ACCEPTED`。Revised plan defines exact six
   production subcommand interfaces，forbids wrapper/DB/template/user overrides and states render occurs
   only under held P3 lock。
2. Claim reason 512-codepoint/2048-byte bound vs existing recovery validator：`ACCEPTED`。Revised plan
   makes the extra byte bound claim-policy-only and preserves `normalize_recovery_reason()` compatibility。
3. Held-lock failure before `workspace-ready`：`ACCEPTED`。Revised plan distinguishes handled
   preactivation failure (prove zero mutation + exact release) from crash/uncertain authority (P0
   reviewed recover only)。
4. P9-3C1 placeholder namespace：`ACCEPTED`。Revised plan fixes exact `__P9C1_*__` prefix and rejects
   P9C0 markers。
5. Controller manifest vs P9-3C0 wrapper manifest：`ACCEPTED`。Revised plan defines separate
   `production_launcher_identity` object and forbids forging/reinterpreting `wrapper.manifest`。
6. Deploy asset inclusion test：`ACCEPTED`。Revised plan requires inspecting the staged/installed fake
   tree for every exact asset。
7. Canonical projection scope：`ACCEPTED`。Revised plan enumerates source/definition/binding/policy/
   roster/workspace-host components and keeps fixture evidence separate。
8. Shell/Python filename style：`DOCUMENTED` as intentional executable-vs-importable naming；not a
   functional or safety defect。

## 5. Revision boundary

Revised plan SHA-256：
`7c78a2609435751add2a7aeba94d089921239d6a83ac424792230644a7110f00`。

Because the bytes changed after Round 1，a fresh exact-delta Round 2 review is required before worker
bootstrap generation。

P9_3C1_P2_PLAN_REVIEW_ROUND1_APPROVED_OLD_SHA_ROUND2_REQUIRED
