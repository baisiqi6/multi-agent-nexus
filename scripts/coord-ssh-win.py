#!/usr/bin/env python3
"""coord-ssh-win.py — Windows wrapper that proxies coordinate CLI calls via SSH.

Usage: python coord-ssh-win.py <coordinate subcommand and args...>

Example: python coord-ssh-win.py runtime agent register --agent-id win-claude --host-id win-admin
"""

import shlex
import subprocess
import sys

SSH_TARGET = "kook-hermes-admin"
REMOTE_CLI = "/usr/local/bin/coord-local"


def main() -> int:
    args = sys.argv[1:]
    if not args:
        args = ["--help"]

    quoted = [shlex.quote(a) for a in args]
    remote_cmd = REMOTE_CLI + " " + " ".join(quoted)

    result = subprocess.run(
        ["ssh", SSH_TARGET, remote_cmd],
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
