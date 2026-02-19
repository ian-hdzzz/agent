"""Gobierno Queretaro - Social SEDESOQ Agent - Social programs"""
from .agent import SocialAgent, get_agent, AGENT_CONFIG
from .config import get_settings, SocialAgentSettings
from .tools import get_tools
from .prompts import get_system_prompt
__all__ = ["SocialAgent", "get_agent", "AGENT_CONFIG", "get_settings", "SocialAgentSettings", "get_tools", "get_system_prompt"]
