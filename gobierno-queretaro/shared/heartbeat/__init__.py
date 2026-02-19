"""
Gobierno Queretaro - Agent Heartbeat Loop

Per-agent heartbeat system that runs inside each agent process.
Agents manage their own schedules, execute heartbeat checks through
their LangGraph, and report results back to PACO.
"""

from .loop import AgentHeartbeatLoop

__all__ = ["AgentHeartbeatLoop"]
