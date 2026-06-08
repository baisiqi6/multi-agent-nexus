"""Agent daemon: local HTTP server that processes AgentRequests via existing adapters.

One agentd process per agent identity. Bridges submit requests via HTTP POST to localhost.
Agentd manages adapter call/resume, session persistence, timeouts, and health checks.
"""

from multinexus.agentd.server import AgentDaemon

__all__ = ["AgentDaemon"]
