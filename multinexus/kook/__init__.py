"""KOOK bridge for MultiNexus.

Handles KOOK Gateway (WebSocket) and HTTP polling, mention routing,
and message filtering. Submits AgentRequests to the local agentd
instead of calling adapters directly.
"""

from multinexus.kook.bot import KookBridge

__all__ = ["KookBridge"]
