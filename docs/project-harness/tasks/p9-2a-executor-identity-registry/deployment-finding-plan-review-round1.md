# P9-2A deployment-finding plan review: round 1

Date: 2026-07-13  
Plan SHA-256: `7ba1a38e827c6ead027df68d33a67db285fbfb888f6e8b13bb95240cbb6ba404`  
Verdict: **changes_requested**

## Reviewer routing

- GLM 5.2 was attempted first as requested. Session
  `019f5a78-a22a-7000-ad3b-19de6c1b04b1` performed sustained read-only code/test
  inspection, then stopped producing JSONL events while the process remained alive;
  the operator terminated it after multiple quiet observation windows.
- Ordinary Kimi for Coding reviewed the plan in session
  `019f5a7e-742e-7000-bbdb-3e82eecb4d12`.

## Must-fix

The production repair procedure required the current mirror to be missing
`split_operation`, while also requiring exact retries to be idempotent. After the
first successful repair the metadata is present, so those requirements contradicted
each other.

Required correction:

- missing metadata: repair;
- exact metadata: return success without another write/event;
- malformed or conflicting metadata: fail closed.

## Additional review notes

- define the exact valid metadata keys and value shapes;
- use the real `create_plan_task_record()` function name;
- separate Kimi worker, Codex reviewer, and `codex-operator` production authority;
- require the exact production script to run against a disposable production DB copy,
  including its commit and retry path.

