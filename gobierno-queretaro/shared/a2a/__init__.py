"""
Gobierno Queretaro - A2A Protocol Integration
Agent Card generation, task lifecycle, and streaming support
"""

from .card_builder import build_agent_card, tools_to_skills

__all__ = [
    "build_agent_card",
    "tools_to_skills",
]
