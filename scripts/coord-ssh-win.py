#!/usr/bin/env python3
"""coord-ssh-win.py — Windows wrapper that proxies coordinate CLI calls via SSH.

Usage: python coord-ssh-win.py <coordinate subcommand and args...>

Example: python coord-ssh-win.py runtime agent register --agent-id win-claude --host-id win-admin

The agentd should point coordinator_cli_path at this .py wrapper, not the .cmd
shim, so JSON arguments arrive here intact before being POSIX-quoted for the
remote shell.
"""

import shlex
import os
import subprocess
import sys

DEFAULT_SSH_TARGET = "kook-hermes-admin"
REMOTE_CLI = "/usr/local/bin/coord-local"


def _ssh_base_cmd() -> list[str]:
    cmd = ["ssh"]
    identity_file = os.environ.get("COORD_SSH_IDENTITY_FILE", "").strip()
    if identity_file:
        cmd += ["-i", identity_file, "-o", "IdentitiesOnly=yes"]
    known_hosts_file = os.environ.get("COORD_SSH_KNOWN_HOSTS_FILE", "").strip()
    cmd += [
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "LogLevel=ERROR",
        "-o",
        f"ConnectTimeout={_ssh_timeout_seconds()}",
    ]
    if known_hosts_file:
        cmd += ["-o", f"UserKnownHostsFile={known_hosts_file}"]
    cmd += [os.environ.get("COORD_SSH_TARGET", DEFAULT_SSH_TARGET)]
    return cmd


def _ssh_timeout_seconds() -> int:
    raw = os.environ.get("COORD_SSH_TIMEOUT_SECONDS", "30").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 30


def _run_via_argv(remote_cmd: str) -> int:
    try:
        result = subprocess.run(
            [*_ssh_base_cmd(), "--", remote_cmd],
            timeout=_ssh_timeout_seconds() + 5,
        )
    except subprocess.TimeoutExpired:
        print("coord-ssh-win: ssh timed out", file=sys.stderr)
        return 124
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

    return _run_via_argv(remote_cmd)


if __name__ == "__main__":
    raise SystemExit(main())
