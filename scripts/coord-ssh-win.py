#!/usr/bin/env python3
"""coord-ssh-win.py — Windows wrapper that proxies coordinate CLI calls via SSH.

Usage: python coord-ssh-win.py <coordinate subcommand and args...>

Example: python coord-ssh-win.py runtime agent register --agent-id win-claude --host-id win-admin

On Windows, pipes the remote command through SSH stdin to avoid list2cmdline
mangling JSON arguments that contain backslashes and double quotes.
"""

import shlex
import subprocess
import sys

SSH_TARGET = "kook-hermes-admin"
REMOTE_CLI = "/usr/local/bin/coord-local"


def _run_via_stdin(remote_cmd: str) -> int:
    result = subprocess.run(
        ["ssh", "-T", SSH_TARGET, "sh"],
        input=(remote_cmd + "\n").encode("utf-8"),
        capture_output=True,
    )
    if result.stdout:
        sys.stdout.buffer.write(result.stdout)
    if result.stderr:
        sys.stderr.buffer.write(result.stderr)
    return result.returncode


def _run_via_argv(remote_cmd: str) -> int:
    result = subprocess.run(
        ["ssh", SSH_TARGET, remote_cmd],
    )
    return result.returncode


def main() -> int:
    args = sys.argv[1:]
    dry_run = False
    if args and args[0] == "--dry-run":
        dry_run = True
        args = args[1:]
    if not args:
        args = ["--help"]

    quoted = [shlex.quote(a) for a in args]
    remote_cmd = REMOTE_CLI + " " + " ".join(quoted)

    if dry_run:
        print(remote_cmd)
        return 0

    if sys.platform == "win32":
        return _run_via_stdin(remote_cmd)
    return _run_via_argv(remote_cmd)


if __name__ == "__main__":
    raise SystemExit(main())
