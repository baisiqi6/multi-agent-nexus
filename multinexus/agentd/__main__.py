"""Standalone agentd launcher.

Run as: python -m multinexus.agentd --config agents.toml --agent <id> --port <port>

One agentd process per agent identity. Bridges connect to it via HTTP.
"""

import argparse
import asyncio
import logging
import signal
import sys

from ..config import load_config
from .server import AgentDaemon

log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="MultiNexus agentd — local agent daemon")
    parser.add_argument("--config", default="agents.toml")
    parser.add_argument("--agent", required=True, help="Agent ID to run agentd for")
    parser.add_argument("--port", type=int, required=True, help="HTTP port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    args = parser.parse_args(argv)

    config = load_config(["--config", args.config, "--agent", args.agent])
    config.agentd_port = args.port
    config.agentd_host = args.host

    daemon = AgentDaemon(config, host=args.host, port=args.port)

    loop = asyncio.new_event_loop()

    def _shutdown():
        log.info("Shutting down agentd for %s", config.id)
        loop.create_task(_async_shutdown())

    async def _async_shutdown():
        await daemon.stop()
        loop.stop()

    loop.add_signal_handler(signal.SIGINT, _shutdown)
    loop.add_signal_handler(signal.SIGTERM, _shutdown)

    try:
        port = loop.run_until_complete(daemon.start())
        log.info("agentd running: agent=%s host=%s port=%s", config.id, args.host, port)
        log.info("Press Ctrl+C to stop")
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(daemon.stop())
        loop.close()


if __name__ == "__main__":
    main()
