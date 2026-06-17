# Phase 8 Host Profile Handoff Smoke

## Purpose

Verify the dogfood handoff path after moving the control plane to Tencent Cloud:

- coordinate runs on the server.
- Discord bridge runs on the server.
- worker agentd processes run on their own hosts.
- worker bootstrap text must use the target host's local checkout path, not the server deployment path.

This is a smoke task only. It must not change source files, services, tokens, deployment config, or agent runtime processes.

## Worker Instructions

When assigned this task, do only these checks:

1. Report the current working directory.
2. Report the current git branch.
3. Confirm whether the bootstrap asked you to work in the local host checkout path.
4. Confirm that `/opt/multinexus` was not presented as your execution checkout.
5. Send a concise `[agent-report] action=done` summary.

Do not edit files. Do not commit. Do not push. Do not restart services.

## Acceptance

- A Mac worker receives bootstrap text pointing at `/Users/yinxin/projects/multinexus`.
- A Windows worker receives bootstrap text pointing at `C:\Users\ADMIN\projects\multinexus`.
- The bootstrap text does not tell either worker to execute inside `/opt/multinexus`.
- The Discord handoff path produces an accept/progress/done report without `Job done` fallback text.
