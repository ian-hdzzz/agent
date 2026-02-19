"""
Gobierno Querétaro - Water CEA Agent
Specialized agent for water services (CEA Querétaro)
"""

from .agent import WaterAgent, get_agent, AGENT_CONFIG
from .config import get_settings, WaterAgentSettings
from .tools import get_tools
from .prompts import get_system_prompt

__all__ = [
    "WaterAgent",
    "get_agent",
    "AGENT_CONFIG",
    "get_settings",
    "WaterAgentSettings",
    "get_tools",
    "get_system_prompt",
]
