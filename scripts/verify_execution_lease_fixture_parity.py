#!/usr/bin/env python3
"""Verify that MultiNexus execution_lease fixtures match Coordinate byte-for-byte.

This is intentionally a standalone script: it does not import any project code
and reads raw file bytes only.  The coordinate repository is reachable via
``--coordinate-repo``.  Either ``--ref REF`` (read from git) or ``--worktree``
(read from the working tree path) must be supplied.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


FIXTURE_NAMES = [
    "execution_lease_v1_bad_digest.json",
    "execution_lease_v1_bad_identity.json",
    "execution_lease_v1_bad_timestamps.json",
    "execution_lease_v1_context_mismatch.json",
    "execution_lease_v1_extra_keys.json",
    "execution_lease_v1_invalid_ttl_interval.json",
    "execution_lease_v1_missing_keys.json",
    "execution_lease_v1_positive.json",
    "execution_lease_v1_resource_mismatch.json",
    "execution_lease_v1_stale_token.json",
]


def _local_bytes(repo_root: Path, name: str) -> bytes:
    path = repo_root / "tests" / "fixtures" / name
    if not path.exists():
        raise FileNotFoundError(f"missing local fixture: {path}")
    return path.read_bytes()


def _git_bytes(repo_root: Path, ref: str, name: str) -> bytes:
    cmd = ["git", "-C", str(repo_root), "show", f"{ref}:tests/fixtures/{name}"]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git show failed for {name}: {stderr}")
    return result.stdout


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify execution_lease fixture parity with Coordinate.",
    )
    parser.add_argument(
        "--coordinate-repo",
        type=Path,
        required=True,
        help="Path to the Coordinate repository.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--ref",
        help="Git ref in the Coordinate repo to read committed fixtures from.",
    )
    group.add_argument(
        "--worktree",
        action="store_true",
        help="Read fixtures from the Coordinate working tree instead of git.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = args.coordinate_repo.resolve()
    if not (repo_root / ".git").exists() and args.ref:
        print(
            f"error: {repo_root} does not look like a git repository", file=sys.stderr
        )
        return 2

    if args.ref:
        read_remote = lambda name: _git_bytes(repo_root, args.ref, name)  # noqa: E731
    else:
        read_remote = lambda name: _local_bytes(repo_root, name)  # noqa: E731

    local_root = Path(__file__).resolve().parents[1]
    failures: list[tuple[str, str]] = []

    for name in FIXTURE_NAMES:
        local_path = local_root / "tests" / "fixtures" / name
        try:
            local = local_path.read_bytes()
        except FileNotFoundError:
            failures.append((name, f"missing local fixture: {local_path}"))
            continue

        try:
            remote = read_remote(name)
        except Exception as exc:  # noqa: BLE001
            failures.append((name, f"cannot read Coordinate fixture: {exc}"))
            continue

        if local != remote:
            failures.append(
                (
                    name,
                    f"byte mismatch (local {len(local)} B != remote {len(remote)} B)",
                )
            )

    if failures:
        print("Fixture parity check failed:", file=sys.stderr)
        for name, reason in failures:
            print(f"  {name}: {reason}", file=sys.stderr)
        return 1

    print(f"All {len(FIXTURE_NAMES)} fixtures match byte-for-byte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
