"""Standalone agentd launcher.

Run as: python -m multinexus.agentd --config agents.toml --agent <id>

One agentd process per agent identity. Claims jobs from coordinate runtime,
executes via adapter, reports results.
"""

import argparse
import asyncio
import logging
import signal
import sys

from ..config import load_config
from .coordinate_client import CoordinateRuntimeError, normalize_recovery_reason
from .worker import AgentdWorker

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="MultiNexus agentd — coordinate worker")
    parser.add_argument("--config", default="agents.toml")
    parser.add_argument("--agent", required=True, help="Agent ID to run agentd for")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Job poll interval (seconds)")
    parser.add_argument(
        "--recoverable",
        action="store_true",
        default=False,
        help="OPERATOR RECOVERY MODE: also claim timed_out+recoverable jobs to resume them. "
             "Normal launchd agentd must NOT set this (8.4.3 P1 #1: prevent auto-reclaim of stuck jobs).",
    )
    parser.add_argument(
        "--recovery-reason",
        default="",
        help="Evidence: human-readable reason for recovery mode (e.g. prior-process-crashed).",
    )
    parser.add_argument(
        "--prior-process-stopped",
        action="store_true",
        default=False,
        help="Evidence: the prior process handling this agent was confirmed stopped before recovery.",
    )
    args = parser.parse_args(argv)

    if args.recoverable:
        try:
            args.recovery_reason = normalize_recovery_reason(args.recovery_reason)
        except CoordinateRuntimeError as exc:
            parser.error(str(exc))
        if not args.prior_process_stopped:
            parser.error("--recoverable requires --prior-process-stopped")
    else:
        if args.recovery_reason != "":
            parser.error("--recovery-reason requires --recoverable")
        if args.prior_process_stopped:
            parser.error("--prior-process-stopped requires --recoverable")

    config = load_config(
        ["--config", args.config, "--agent", args.agent],
        require_token=False,
    )

    worker = AgentdWorker(config)
    loop = asyncio.new_event_loop()

    def _shutdown():
        log.info("Shutting down agentd for %s", config.id)
        worker.stop()

    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, _shutdown)
        loop.add_signal_handler(signal.SIGTERM, _shutdown)

    try:
        log.info("agentd worker starting: agent=%s recoverable=%s", config.id, args.recoverable)
        loop.run_until_complete(
            worker.run(
                poll_interval=args.poll_interval,
                recoverable=args.recoverable,
                recovery_reason=args.recovery_reason,
                prior_process_stopped=args.prior_process_stopped,
            )
        )
    except (KeyboardInterrupt, RuntimeError):
        pass
    finally:
        worker.stop()
        loop.close()


if __name__ == "__main__":
    main()
