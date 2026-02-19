"""
Gobierno Queretaro - Vehicles Agent
Specialized agent for vehicle registration services
"""

from .agent import VehiclesAgent, get_agent, AGENT_CONFIG
from .config import get_settings, VehiclesAgentSettings
from .tools import get_tools
from .prompts import get_system_prompt

__all__ = [
    "VehiclesAgent",
    "get_agent",
    "AGENT_CONFIG",
    "get_settings",
    "VehiclesAgentSettings",
    "get_tools",
    "get_system_prompt",
]
