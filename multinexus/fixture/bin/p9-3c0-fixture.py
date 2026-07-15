#!/usr/bin/env python3
"""P9-3C0 Package 2 zero-provider fixture executable.

Mimics the smallest valid Claude stream-json child for a bounded, silent
quiet window. Uses only the Python standard library and produces no network,
credential, config, or provider side effects.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from typing import Any, Callable


_QUIET_SECONDS = 75
_ALLOWED_OPTIONS = {
    "-p",
    "--verbose",
    "--output-format",
    "--include-partial-messages",
}
_EXPECTED_PAIRS = {("--output-format", "stream-json")}


class FixtureError(Exception):
    """Validation or runtime failure exposed as one bounded stderr line."""

    def __init__(self, message: str):
        super().__init__(message[:500])


def validate_argv(argv: list[str]) -> list[str]:
    """Return normalized argv or raise FixtureError.

    Accepts exactly one occurrence of each allowed option. Equivalent ordering
    of option pairs is permitted; unknown/duplicate/missing options,
    positionals, --model, --resume, and dangerous-permission options fail.
    """
    if not argv:
        raise FixtureError("argv empty")

    program = argv[0]
    rest = argv[1:]
    seen: set[str] = set()
    parsed: dict[str, str | None] = {}
    i = 0
    while i < len(rest):
        token = rest[i]
        if token in ("-p", "--verbose", "--include-partial-messages"):
            if token in seen:
                raise FixtureError(f"duplicate option: {token}")
            seen.add(token)
            parsed[token] = None
            i += 1
            continue
        if token == "--output-format":
            if token in seen:
                raise FixtureError("duplicate option: --output-format")
            if i + 1 >= len(rest):
                raise FixtureError("--output-format missing value")
            value = rest[i + 1]
            if not value or value.startswith("-"):
                raise FixtureError(f"--output-format invalid value: {value!r}")
            seen.add(token)
            parsed[token] = value
            i += 2
            continue
        if token in ("--model", "--resume"):
            raise FixtureError(f"forbidden option: {token}")
        if token.startswith("--dangerously") or token.startswith("--bypass"):
            raise FixtureError(f"forbidden option: {token}")
        if token.startswith("-"):
            raise FixtureError(f"unknown option: {token}")
        raise FixtureError(f"positional argument not allowed: {token!r}")

    for opt in ("-p", "--verbose", "--output-format", "--include-partial-messages"):
        if opt not in seen:
            raise FixtureError(f"missing required option: {opt}")

    if parsed.get("--output-format") != "stream-json":
        raise FixtureError("--output-format must be stream-json")

    return [program] + rest


def parse_envelope(raw: str) -> dict[str, Any]:
    """Parse and validate the strict stdin JSON envelope.

    Requires exactly the keys contract_version, mode, quiet_seconds,
    spawn_descendant with integer-not-bool 1, complete|hold, integer-not-bool
    75, and real bool respectively. Trailing documents and extra keys fail.
    """
    raw = raw.strip()
    if not raw:
        raise FixtureError("stdin empty")

    # Reject trailing documents by only allowing optional outer whitespace.
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"stdin is not valid JSON: {exc}") from exc

    if not isinstance(decoded, dict):
        raise FixtureError("stdin JSON must be an object")

    expected_keys = {"contract_version", "mode", "quiet_seconds", "spawn_descendant"}
    if set(decoded.keys()) != expected_keys:
        raise FixtureError("stdin JSON has incorrect key set")

    contract_version = decoded["contract_version"]
    if isinstance(contract_version, bool) or not isinstance(contract_version, int):
        raise FixtureError("contract_version must be integer 1")
    if contract_version != 1:
        raise FixtureError("contract_version must be 1")

    mode = decoded["mode"]
    if mode not in ("complete", "hold"):
        raise FixtureError("mode must be complete or hold")

    quiet_seconds = decoded["quiet_seconds"]
    if isinstance(quiet_seconds, bool) or not isinstance(quiet_seconds, int):
        raise FixtureError("quiet_seconds must be integer 75")
    if quiet_seconds != _QUIET_SECONDS:
        raise FixtureError("quiet_seconds must be 75")

    spawn_descendant = decoded["spawn_descendant"]
    if not isinstance(spawn_descendant, bool):
        raise FixtureError("spawn_descendant must be a boolean")
    if spawn_descendant and mode != "hold":
        raise FixtureError("spawn_descendant=true requires mode=hold")

    return {
        "contract_version": contract_version,
        "mode": mode,
        "quiet_seconds": quiet_seconds,
        "spawn_descendant": spawn_descendant,
    }


_terminated = False


def _set_terminated(_signum, _frame) -> None:
    global _terminated
    _terminated = True


def _silence_signals() -> None:
    """Install silent SIGTERM/SIGINT handlers; keep behavior bounded."""
    signal.signal(signal.SIGTERM, _set_terminated)
    signal.signal(signal.SIGINT, _set_terminated)


def _wait_for_signal(deadline_func: Callable[[], float]) -> None:
    """Sleep in small increments until a signal arrives or deadline passes."""
    while not _terminated and time.monotonic() < deadline_func():
        time.sleep(0.05)


def run_fixture(
    envelope: dict[str, Any],
    *,
    sleep_fn: Callable[[int], None] | None = None,
    emit_fn: Callable[[dict[str, Any]], None] | None = None,
    descendant_fn: Callable[[], Any] | None = None,
    signal_wait_fn: Callable[[Callable[[], float]], None] | None = None,
) -> int:
    """Core fixture execution; returns exit code.

    Production uses real time/stdout/descendants. Tests inject virtual hooks.
    """
    real_sleep = sleep_fn if sleep_fn is not None else time.sleep
    real_emit = emit_fn if emit_fn is not None else (lambda event: print(json.dumps(event, separators=(",", ":")), flush=True))
    real_descendant = descendant_fn if descendant_fn is not None else _start_descendant
    real_signal_wait = signal_wait_fn if signal_wait_fn is not None else _wait_for_signal

    mode = envelope["mode"]
    spawn_descendant = envelope["spawn_descendant"]

    if mode == "complete":
        real_sleep(_QUIET_SECONDS)
        real_emit({
            "is_error": False,
            "result": "fixture complete",
            "subtype": "success",
            "type": "result",
        })
        return 0

    # hold mode
    _silence_signals()
    descendant = None
    if spawn_descendant:
        descendant = real_descendant()

    try:
        # Hold until signalled. No output, no invented session id.
        real_signal_wait(lambda: float("inf"))
        return 0
    finally:
        if descendant is not None:
            _terminate_descendant(descendant)


def _start_descendant() -> Any:
    """Start a fixed no-shell descendant for cgroup cleanup proof."""
    return os.spawnvp(os.P_NOWAIT, "/bin/sleep", ["/bin/sleep", "300"])


def _terminate_descendant(pid: int) -> None:
    """Best-effort termination and reap of the optional descendant.

    Bounded: send SIGTERM once, then reap repeatedly for a short window.
    """
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            waited, _ = os.waitpid(pid, os.WNOHANG)
            if waited != 0:
                return
        except (OSError, ChildProcessError):
            return
        time.sleep(0.05)


def main(argv: list[str] | None = None) -> int:
    """Production entrypoint. Always uses real 75-second sleep and real hooks."""
    argv = argv if argv is not None else sys.argv
    try:
        validate_argv(argv)
    except FixtureError as exc:
        print(f"fixture argv error: {exc}", file=sys.stderr)
        return 1

    raw_stdin = sys.stdin.read()
    try:
        envelope = parse_envelope(raw_stdin)
    except FixtureError as exc:
        print(f"fixture envelope error: {exc}", file=sys.stderr)
        return 1

    return run_fixture(
        envelope,
        sleep_fn=time.sleep,
        emit_fn=(lambda event: print(json.dumps(event, separators=(",", ":")), flush=True)),
        descendant_fn=_start_descendant,
        signal_wait_fn=_wait_for_signal,
    )


if __name__ == "__main__":
    raise SystemExit(main())
