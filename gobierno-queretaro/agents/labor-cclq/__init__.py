"""Gobierno Queretaro - Labor CCLQ Agent - Labor conciliation services"""
from .agent import LaborAgent, get_agent, AGENT_CONFIG
from .config import get_settings, LaborAgentSettings
from .tools import get_tools
from .prompts import get_system_prompt
__all__ = ["LaborAgent", "get_agent", "AGENT_CONFIG", "get_settings", "LaborAgentSettings", "get_tools", "get_system_prompt"]
