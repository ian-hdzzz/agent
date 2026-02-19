"""
Gobierno Queretaro - Women IQM Agent
Specialized agent for women's services (Instituto Queretano de la Mujer)
"""

from .agent import WomenAgent, get_agent, AGENT_CONFIG
from .config import get_settings, WomenAgentSettings
from .tools import get_tools
from .prompts import get_system_prompt

__all__ = [
    "WomenAgent",
    "get_agent",
    "AGENT_CONFIG",
    "get_settings",
    "WomenAgentSettings",
    "get_tools",
    "get_system_prompt",
]
