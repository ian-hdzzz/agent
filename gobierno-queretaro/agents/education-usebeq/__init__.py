"""
Gobierno Queretaro - Education USEBEQ Agent
Specialized agent for education services (USEBEQ)
"""

from .agent import EducationAgent, get_agent, AGENT_CONFIG
from .config import get_settings, EducationAgentSettings
from .tools import get_tools
from .prompts import get_system_prompt

__all__ = [
    "EducationAgent",
    "get_agent",
    "AGENT_CONFIG",
    "get_settings",
    "EducationAgentSettings",
    "get_tools",
    "get_system_prompt",
]
