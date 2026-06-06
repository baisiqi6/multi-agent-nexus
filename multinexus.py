#!/usr/bin/env python3
"""MultiNexus: one-process-per-agent Discord bot runner.

Usage:
    python multinexus.py --agent mac-claude
    python multinexus.py --config agents.toml --agent mac-claude

Each invocation starts one Discord bot for the specified agent.
"""

import asyncio
import logging
import sys

from multinexus.client import DiscordClient
from multinexus.config import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nexus")


def main():
    config = load_config()
    log.info(
        "Starting MultiNexus: agent=%s adapter=%s display_name=%s",
        config.id,
        config.adapter,
        config.display_name or config.id,
    )

    client = DiscordClient(config)

    try:
        asyncio.run(client.start(config.token))
    except KeyboardInterrupt:
        log.info("Shutting down agent %s", config.id)
        asyncio.run(client.close())


if __name__ == "__main__":
    main()
