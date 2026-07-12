# Worker Bootstrap: P9-0A5 Event Presentation Registry Extraction

你是本包唯一 coding worker。严格执行 Round 2 已批准的 movement-only 计划，不做架构
扩展、语义重写或顺手清理。

## Exact identity

- Task: `p9-0a5-event-presentation-registry`.
- Worker worktree:
  `/Users/yinxin/Documents/Codex/2026-07-10/ni/work/coordinate-p9-0a5-kimi`.
- Branch: `agents/mac-omp/p9-0a5-event-presentation-registry`.
- Required start HEAD:
  `882c2a1487e4102d35c3c1f5b18b4a542be2d3bc`.
- Approved plan:
  `/Users/yinxin/projects/multinexus/docs/project-harness/tasks/p9-0a5-event-presentation-registry/plan.md`.
- Approved plan SHA-256:
  `f8507735838a22b3d7c69982f9fed9493e09caf4ab1b8b709f4085d12fc3c1c2`.
- Approval event: `9c58080d-bf46-4a2b-97ae-1dd15a747071`.
- Read `plan-review-round-1.md` and `plan-review-round-2.md` before editing.

开始前核验 `pwd`、branch、HEAD、clean status 和 plan SHA；任一不符立即停止。不要
switch/reset/rebase/cherry-pick 或碰共享 checkout。

## Authorized implementation

1. 新增 `src/coordinate/event_presentation.py`，仅依赖 stdlib `sqlite3` 和 typing；
2. 原样移动批准的 44 个 top-level pure functions（550 span / 543 nonblank）和一个
   66-line `_EVENT_BASE_PAYLOAD_RENDERERS` registry assignment；
3. 新增精确常量 `EXPLICITLY_UNSTYLED_EVENT_TYPES = frozenset({...})`，内容只能是
   `issue.materialized`、`issue.triaged`、`review.rejected`；它只作为 partition witness，
   不能参与实际 styling 决策；
4. `policy.py` 直接 import/re-export registry、44 个 private names 和 explicit-unstyle
   witness，保证 facade names 与 presentation owner object-identical；
5. `SUPPORTED_EVENT_TYPES` literal、`SUPPORTED_PLATFORMS`、`PolicyError`、
   `_render_event_base_payload`、`render_event_payload`、`_enrich_with_embed`、
   `_event_payload`、`_delivery_for_message_key` 以及全部 DB/delivery/pump/skip/message-key
   authority 必须留在 `policy.py`；
6. 新增 `tests/test_event_presentation.py`，证明 object identity、44 body witnesses、
   registry witness、34 supported = 34 rendered = 31 styled + exact 3 unstyled、exact
   `PolicyError` fallback、三种 cold import order 以及 dependency direction；
7. 只有在上述 boundary 文件无法承载一条窄 ownership assertion 时，才允许最小修改
   `tests/test_policy.py`。

所有 moved function body 和 registry expression 必须原样。不得从 registry 推导
`SUPPORTED_EVENT_TYPES`，不得从 explicit-unstyle set 驱动 Discord styling。

## Portable witness — exact algorithm

从 reviewed start `882c2a1`、在移动前一次性生成并人工核对 44 + 1 个 expected hashes。
递归投影必须使用 `ast.iter_fields`：

- 每个 AST object 保留 node type；
- 按 field 递归保留非空字段、标量值、context 和 list order；
- 只丢弃 `None` 和空 list/tuple；
- 不读取或遍历 `_attributes`，因此不包含 `lineno`、`col_offset`、`end_lineno`、
  `end_col_offset`；
- 以 sorted-key compact JSON 序列化，UTF-8 编码后计算 SHA-256。

永久 tests 禁止使用 whole-node `ast.dump`、`ast.unparse`、git history lookup，也禁止
从 post-move code 重新生成 expected values。若 pre-move witness 没有在首次 source edit
前保存，立即停止，不得补造。

## Allowed paths only

- `src/coordinate/policy.py`;
- `src/coordinate/event_presentation.py`;
- `tests/test_event_presentation.py`;
- `tests/test_policy.py` only for one truly necessary narrow ownership assertion.

禁止修改 `discord_rendering.py`、CLI、service、schema、DB、delivery、daemon、harness、
docs 或其他 tests。若需要超范围，停止并报告 blocker。

## Validation

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.test_event_presentation tests.test_policy tests.test_discord_rendering \
  tests.test_delivery_cli tests.test_cli_contract
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover tests
```

Focused baseline 不得低于 247。当前 host 的 Python 3.12 可能复现八个已审核的既有失败
（七个 interpreter-specific CLI contract fixture、一个 historical issue-CLI witness）；
不得把它们写成全绿，也不得新增失败。记录 exact counts、44 + 1 witness、34/34/31/3、
fresh import orders、modified paths 和任何环境差异。

全部完成后创建一个 local commit。禁止 subagent、push、merge、deploy、restart、SSH、
Coordinate lifecycle 或 MultiNexus 修改。最终中文优先报告 commit、paths、证据与风险。

Provider 默认 `kimi-code/kimi-for-coding-highspeed`。只有 Kimi 出现 quota/auth/provider
失败时才由 Operator 终止并以 GLM 重启；worker 不得自行无记录切换。任何切换都必须在
provider JSONL 与 closeout 中明确归因。
