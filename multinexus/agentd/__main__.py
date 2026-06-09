"""Standalone agentd launcher.

Run as: python -m multinexus.agentd --config agents.toml --agent <id>

One agentd process per agent identity. Claims jobs from coordinate runtime,
executes via adapter, reports results.
"""

import argparse
import asyncio
import logging
import signal

from ..config import load_config
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
    args = parser.parse_args(argv)

    config = load_config(
        ["--config", args.config, "--agent", args.agent],
        require_token=False,
    )

    worker = AgentdWorker(config)
    loop = asyncio.new_event_loop()

    def _shutdown():
        log.info("Shutting down agentd for %s", config.id)
        worker.stop()

    loop.add_signal_handler(signal.SIGINT, _shutdown)
    loop.add_signal_handler(signal.SIGTERM, _shutdown)

    try:
        log.info("agentd worker starting: agent=%s", config.id)
        loop.run_until_complete(worker.run(poll_interval=args.poll_interval))
    except (KeyboardInterrupt, RuntimeError):
        pass
    finally:
        worker.stop()
        loop.close()


if __name__ == "__main__":
    main()
