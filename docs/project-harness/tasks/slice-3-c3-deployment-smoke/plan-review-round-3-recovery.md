# Plan Review Round 3: Attempt-2 Recovery Exception

- Reviewer runtime: OpenCode CLI
- Provider/model: `zhipuai-coding-plan/glm-5.2`
- Session: `ses_0ab13136affe0WSciu0Y2qhvBI`
- Reviewed plan hash: `8ee979c70d4fc724`
- Decision: `changes_requested`

## Finding

The proposed `--skip-install` exception was conditionally safe because every existing
dependency manifest was unchanged and the previous venv was preserved. However, the
plan did not pair it with `--no-smoke`; the unchanged `server-smoke.sh` would fail on
the known proxy outage before the receipt-only matrix, creating a contradiction
between fail-closed behavior and intended continuation.

The reviewer also required any recovery rollback to state its install behavior and
all worker/gate artifacts to be regenerated for the recovery hash.

## Disposition

The proxy blocker was subsequently removed by installing a user-provided Mihomo
configuration that passed server-side validation. Discord and PyPI probes passed and
both production services remained active with zero restarts across two observation
windows. The recovery exception is therefore withdrawn instead of revised. The
canonical plan was restored byte-for-byte to the already independently approved
normal-deployment hash `871664176c514bec`.
