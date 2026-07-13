#!/usr/bin/env python3
"""Internal operational helper for capacity snapshot capture/restore.

This is not a public runtime CLI. It is used by deploy-server.sh to capture
and restore the capacity projection snapshot before/after authority overwrite.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from coordinate.executor_capacity import capture_capacity_snapshot, restore_capacity_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Internal capacity snapshot helper. Not a public CLI."
    )
    parser.add_argument("--db", required=True, help="Path to Coordinate SQLite DB")
    parser.add_argument(
        "--target-source-id",
        default="multinexus.discord.capacity",
        help="Expected capacity source id",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--capture", metavar="OUT_PATH", help="Capture snapshot to file")
    group.add_argument("--restore", metavar="IN_PATH", help="Restore snapshot from file")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        if args.capture:
            capture_capacity_snapshot(conn, args.target_source_id, args.capture)
        else:
            restore_capacity_snapshot(conn, args.target_source_id, args.restore)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
