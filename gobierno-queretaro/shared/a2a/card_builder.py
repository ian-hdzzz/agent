"""
Gobierno Queretaro - A2A Agent Card Builder
Auto-generates Agent Cards from existing agent config and tools
"""

import inspect
import logging
from typing import Any

from a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

logger = logging.getLogger(__name__)


def tools_to_skills(tools: list) -> list[AgentSkill]:
    """
    Convert LangChain @tool functions to A2A AgentSkill objects.

    Extracts name, description, and argument info from each tool
    to build skill metadata without manual authoring.

    Args:
        tools: List of LangChain tool objects (decorated with @tool)

    Returns:
        List of AgentSkill objects
    """
    skills = []
    for t in tools:
        # LangChain tools have .name, .description, and .args_schema
        name = getattr(t, "name", str(t))
        description = getattr(t, "description", "")

        # Extract example input keywords from description
        tags = []
        if hasattr(t, "args_schema") and t.args_schema:
            for field_name in t.args_schema.model_fields:
                tags.append(field_name)

        skills.append(
            AgentSkill(
                id=name,
                name=name,
                description=description,
                tags=tags,
                examples=[],
            )
        )

    return skills


def build_agent_card(
    agent_id: str,
    agent_name: str,
    agent_description: str,
    url: str,
    tools: list | None = None,
    version: str = "1.0.0",
    streaming: bool = False,
    extra_skills: list[AgentSkill] | None = None,
) -> AgentCard:
    """
    Build an A2A AgentCard from existing agent configuration.

    Auto-generates the card from the AGENT_CONFIG dict and @tool functions
    that each agent already has, requiring zero manual authoring.

    Args:
        agent_id: Agent identifier (e.g., "vehicles", "water-cea")
        agent_name: Human-readable agent name
        agent_description: What this agent does
        url: Base URL where the agent is accessible
        tools: LangChain tool objects to convert to skills
        version: Agent version string
        streaming: Whether agent supports SSE streaming
        extra_skills: Additional skills to include beyond auto-generated ones

    Returns:
        A2A AgentCard instance
    """
    skills = []
    if tools:
        skills = tools_to_skills(tools)
    if extra_skills:
        skills.extend(extra_skills)

    capabilities = AgentCapabilities(streaming=streaming)

    card = AgentCard(
        name=agent_name,
        description=agent_description,
        url=url,
        version=version,
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=skills,
        authentication=AgentAuthentication(schemes=["public"]),
    )

    logger.info(
        f"Built Agent Card for {agent_id}: "
        f"{len(skills)} skills, streaming={streaming}"
    )

    return card
