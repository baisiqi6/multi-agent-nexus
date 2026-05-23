#!/usr/bin/env python3
"""Discord Nexus: one-process-per-agent Discord bot runner.

Usage:
    python nexus.py --agent mac-claude
    python nexus.py --config agents.toml --agent mac-claude

Each invocation starts one Discord bot for the specified agent.
"""

import asyncio
import logging
import sys

from discord_nexus.client import DiscordClient
from discord_nexus.config import load_config

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nexus")


def main():
    config = load_config()
    log.info(
        "Starting Discord Nexus: agent=%s adapter=%s display_name=%s",
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
