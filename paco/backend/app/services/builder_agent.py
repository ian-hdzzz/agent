"""
PACO Agent Builder Service

Core logic for the conversational agent builder.
Calls Anthropic Messages API with tools that map to existing PACO services.
"""

import json
import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import (
    Agent,
    AgentSkill,
    AgentTool,
    BuilderSession,
    McpServer,
    Skill,
    Tool,
)
from app.services.skill_filesystem import SkillFilesystemService


# =============================================================================
# Builder Tool Definitions (Anthropic format)
# =============================================================================

BUILDER_TOOLS = [
    {
        "name": "search_existing_skills",
        "description": "Search the PACO skill library for reusable skills. Returns matching skills with name, description, and code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to find relevant skills (e.g. 'consulta', 'pago', 'registro')",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_existing_tools",
        "description": "Search registered tools across MCP servers. Returns tools with name, description, and input schema.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to find relevant tools",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_existing_agents",
        "description": "Search existing agents for reference patterns. Returns agents with name, description, model, and status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term to find similar agents",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_agent_draft",
        "description": "Create a new agent with status='draft'. This is the first step in building an agent. Returns the agent ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Technical name for the agent (lowercase, hyphens, e.g. 'predial-queretaro')",
                },
                "display_name": {
                    "type": "string",
                    "description": "Human-readable name in Spanish (e.g. 'Agente de Predial')",
                },
                "description": {
                    "type": "string",
                    "description": "Description of what this agent does, in Spanish",
                },
                "model": {
                    "type": "string",
                    "description": "Claude model to use",
                    "default": "claude-sonnet-4-5-20250929",
                },
            },
            "required": ["name", "display_name", "description"],
        },
    },
    {
        "name": "update_agent_config",
        "description": "Update the agent's system prompt, model, or other settings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "system_prompt": {
                    "type": "string",
                    "description": "The full system prompt for the agent",
                },
                "model": {
                    "type": "string",
                    "description": "Claude model to use",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
                "sdk_config": {
                    "type": "object",
                    "description": "Additional SDK configuration",
                },
                "env_vars": {
                    "type": "object",
                    "description": "Environment variables for this agent (e.g. API keys)",
                    "additionalProperties": {"type": "string"},
                },
            },
        },
    },
    {
        "name": "set_agent_env_vars",
        "description": "Set or update environment variables (API keys, secrets) for the draft agent. Merges with existing env_vars.",
        "input_schema": {
            "type": "object",
            "properties": {
                "env_vars": {
                    "type": "object",
                    "description": "Key-value pairs of environment variables to set (e.g. {'ANTHROPIC_API_KEY': 'sk-...', 'OPENAI_API_KEY': 'sk-...'})",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["env_vars"],
        },
    },
    {
        "name": "create_skill",
        "description": "Create a new skill (SKILL.md) and register it in the database. Skills are reusable knowledge modules.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Unique skill code (lowercase, e.g. 'consulta_predial')",
                },
                "name": {
                    "type": "string",
                    "description": "Skill name in Spanish",
                },
                "description": {
                    "type": "string",
                    "description": "What this skill provides",
                },
                "body": {
                    "type": "string",
                    "description": "The skill content in markdown — instructions, knowledge, rules",
                },
                "allowed_tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tools this skill requires",
                },
            },
            "required": ["code", "name", "description", "body"],
        },
    },
    {
        "name": "attach_skill_to_agent",
        "description": "Link an existing skill to the draft agent being built.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_code": {
                    "type": "string",
                    "description": "The skill code to attach",
                },
            },
            "required": ["skill_code"],
        },
    },
    {
        "name": "create_tool_definition",
        "description": "Register a new tool that the agent can use. Tools represent API operations (queries, payments, appointments).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Tool name (e.g. 'consultar_adeudo_predial')",
                },
                "description": {
                    "type": "string",
                    "description": "What this tool does",
                },
                "input_schema": {
                    "type": "object",
                    "description": "JSON Schema for tool input parameters",
                },
            },
            "required": ["name", "description", "input_schema"],
        },
    },
    {
        "name": "create_mcp_server",
        "description": "Register an API endpoint as an MCP server for tool execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Server name (e.g. 'predial-api')",
                },
                "description": {
                    "type": "string",
                    "description": "Server description",
                },
                "url": {
                    "type": "string",
                    "description": "Base URL of the API",
                },
                "transport": {
                    "type": "string",
                    "description": "Transport type: 'http' or 'stdio'",
                    "default": "http",
                },
            },
            "required": ["name", "url"],
        },
    },
    {
        "name": "assign_tool_to_agent",
        "description": "Link a registered tool to the draft agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tool_id": {
                    "type": "string",
                    "description": "UUID of the tool to assign",
                },
            },
            "required": ["tool_id"],
        },
    },
    {
        "name": "set_process_flow",
        "description": "Define the step-by-step citizen journey for the agent. Stored in agent sdk_config.",
        "input_schema": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "integer"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "action": {"type": "string", "description": "What the agent does at this step"},
                        },
                    },
                    "description": "Ordered list of process steps",
                },
            },
            "required": ["steps"],
        },
    },
    {
        "name": "set_knowledge_base",
        "description": "Add FAQs, requirements, documents, costs, and other knowledge to the agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "faqs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                        },
                    },
                    "description": "Frequently asked questions",
                },
                "requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required documents or conditions",
                },
                "costs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "concept": {"type": "string"},
                            "amount": {"type": "string"},
                        },
                    },
                    "description": "Service costs",
                },
                "links": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Useful reference links",
                },
            },
        },
    },
    {
        "name": "test_agent_message",
        "description": "Send a test message to the draft agent and get its response. Useful for verifying behavior.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The test citizen message to send",
                },
                "conversation_history": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                    "description": "Previous messages in the test conversation",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "finalize_agent",
        "description": "Mark the agent as ready by changing status from 'draft' to 'stopped' (ready for deployment).",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# =============================================================================
# SSE Event Helpers
# =============================================================================


def _sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format an SSE event line."""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, default=str)}\n\n"


# =============================================================================
# Builder Agent Service
# =============================================================================


class BuilderAgentService:
    """Orchestrates the agent-building conversation with Claude."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.fs = SkillFilesystemService()

    def _load_system_prompt(self) -> str:
        """Load builder system prompt from SKILL.md."""
        skill_path = Path(settings.skills_base_path) / "agent-builder" / "SKILL.md"
        if skill_path.exists():
            content = skill_path.read_text()
            # Strip frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return parts[2].strip()
            return content
        return "You are a government agent builder assistant. Help create AI agents for government services."

    async def process_message(
        self,
        session: BuilderSession,
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        """Process a user message and yield SSE events."""
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            yield _sse_event("error", {"error": "ANTHROPIC_API_KEY not configured"})
            return

        # Append user message to conversation history
        history = list(session.conversation_history or [])
        history.append({"role": "user", "content": user_message})

        system_prompt = self._load_system_prompt()
        model = "claude-sonnet-4-5-20250929"

        # Tool use loop
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Call Anthropic API
            api_body: Dict[str, Any] = {
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": history,
                "tools": BUILDER_TOOLS,
            }

            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json=api_body,
                    )

                if response.status_code != 200:
                    yield _sse_event("error", {
                        "error": f"Claude API error ({response.status_code}): {response.text}"
                    })
                    break

                result = response.json()

            except Exception as e:
                yield _sse_event("error", {"error": f"API call failed: {e}"})
                break

            # Track token usage
            usage = result.get("usage", {})
            session.total_input_tokens += usage.get("input_tokens", 0)
            session.total_output_tokens += usage.get("output_tokens", 0)

            # Process response content
            content_blocks = result.get("content", [])
            text_parts = []
            tool_uses = []

            for block in content_blocks:
                if block["type"] == "text":
                    text_parts.append(block["text"])
                    yield _sse_event("message_delta", {"text": block["text"]})
                elif block["type"] == "tool_use":
                    tool_uses.append(block)

            # Append assistant message to history
            history.append({"role": "assistant", "content": content_blocks})

            # If no tool calls, we're done
            if not tool_uses:
                break

            # Execute tool calls and build tool results
            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use["name"]
                tool_input = tool_use.get("input", {})
                tool_use_id = tool_use["id"]

                yield _sse_event("tool_call", {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "tool_use_id": tool_use_id,
                })

                # Execute the tool
                try:
                    tool_result = await self._execute_tool(
                        session, tool_name, tool_input
                    )
                    yield _sse_event("tool_result", {
                        "tool_name": tool_name,
                        "tool_use_id": tool_use_id,
                        "result": tool_result,
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(tool_result, default=str),
                    })
                except Exception as e:
                    error_msg = f"Tool execution failed: {e}"
                    yield _sse_event("tool_result", {
                        "tool_name": tool_name,
                        "tool_use_id": tool_use_id,
                        "error": error_msg,
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps({"error": error_msg}),
                        "is_error": True,
                    })

            # Append tool results to history and loop
            history.append({"role": "user", "content": tool_results})

        # Save updated conversation history and token counts
        session.conversation_history = history
        await self.db.commit()

        yield _sse_event("done", {
            "input_tokens": session.total_input_tokens,
            "output_tokens": session.total_output_tokens,
        })

    # =============================================================================
    # Tool Execution
    # =============================================================================

    async def _execute_tool(
        self,
        session: BuilderSession,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a builder tool and return the result."""
        handler = getattr(self, f"_tool_{tool_name}", None)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        return await handler(session, tool_input)

    async def _tool_search_existing_skills(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        query = input.get("query", "").lower()
        result = await self.db.execute(select(Skill).order_by(Skill.code))
        skills = result.scalars().all()
        matches = []
        for skill in skills:
            if (
                query in (skill.code or "").lower()
                or query in (skill.name or "").lower()
                or query in (skill.description or "").lower()
            ):
                matches.append({
                    "code": skill.code,
                    "name": skill.name,
                    "description": skill.description,
                })
        return {"skills": matches[:20], "total": len(matches)}

    async def _tool_search_existing_tools(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        query = input.get("query", "").lower()
        result = await self.db.execute(select(Tool).order_by(Tool.name))
        tools = result.scalars().all()
        matches = []
        for tool in tools:
            if (
                query in (tool.name or "").lower()
                or query in (tool.description or "").lower()
            ):
                matches.append({
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                })
        return {"tools": matches[:20], "total": len(matches)}

    async def _tool_search_existing_agents(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        query = input.get("query", "").lower()
        result = await self.db.execute(select(Agent).order_by(Agent.name))
        agents = result.scalars().all()
        matches = []
        for agent in agents:
            if (
                query in (agent.name or "").lower()
                or query in (agent.display_name or "").lower()
                or query in (agent.description or "").lower()
            ):
                matches.append({
                    "id": str(agent.id),
                    "name": agent.name,
                    "display_name": agent.display_name,
                    "description": agent.description,
                    "model": agent.model,
                    "status": agent.status,
                })
        return {"agents": matches[:20], "total": len(matches)}

    async def _tool_create_agent_draft(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        name = input["name"]
        # Check for existing
        existing = await self.db.execute(select(Agent).where(Agent.name == name))
        if existing.scalar_one_or_none():
            return {"error": f"Agent '{name}' already exists"}

        agent = Agent(
            name=name,
            display_name=input.get("display_name", name),
            description=input.get("description"),
            model=input.get("model", "claude-sonnet-4-5-20250929"),
            status="draft",
            pm2_name=name,
        )
        self.db.add(agent)
        await self.db.flush()

        # Link agent to session
        session.agent_id = agent.id
        session.phase = "build"
        session.draft_config = {
            "name": name,
            "display_name": input.get("display_name", name),
            "description": input.get("description"),
        }

        # Record artifact
        artifacts = list(session.artifacts or [])
        artifacts.append({
            "type": "agent",
            "id": str(agent.id),
            "name": name,
            "display_name": input.get("display_name", name),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session.artifacts = artifacts

        await self.db.commit()

        return {
            "success": True,
            "agent_id": str(agent.id),
            "name": name,
            "status": "draft",
        }

    async def _tool_update_agent_config(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet. Use create_agent_draft first."}

        result = await self.db.execute(
            select(Agent).where(Agent.id == session.agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return {"error": "Draft agent not found"}

        if "system_prompt" in input:
            agent.system_prompt = input["system_prompt"]
        if "model" in input:
            agent.model = input["model"]
        if "description" in input:
            agent.description = input["description"]
        if "sdk_config" in input:
            current = agent.sdk_config or {}
            current.update(input["sdk_config"])
            agent.sdk_config = current
        if "env_vars" in input:
            current_env = agent.env_vars or {}
            current_env.update(input["env_vars"])
            agent.env_vars = current_env

        await self.db.commit()

        # Update artifacts
        artifacts = list(session.artifacts or [])
        artifacts.append({
            "type": "agent_config_update",
            "agent_id": str(agent.id),
            "fields_updated": list(input.keys()),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session.artifacts = artifacts
        await self.db.commit()

        return {"success": True, "agent_id": str(agent.id), "updated": list(input.keys())}

    async def _tool_set_agent_env_vars(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet. Use create_agent_draft first."}

        result = await self.db.execute(
            select(Agent).where(Agent.id == session.agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return {"error": "Draft agent not found"}

        current_env = agent.env_vars or {}
        current_env.update(input.get("env_vars", {}))
        agent.env_vars = current_env

        await self.db.commit()

        # Mask values for the response
        from app.core.secrets import mask_env_vars
        return {
            "success": True,
            "agent_id": str(agent.id),
            "env_vars_set": list(input.get("env_vars", {}).keys()),
            "current_keys": list(current_env.keys()),
        }

    async def _tool_create_skill(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        code = input["code"]

        # Check existing
        existing = await self.db.execute(select(Skill).where(Skill.code == code))
        if existing.scalar_one_or_none():
            return {"error": f"Skill '{code}' already exists. Use attach_skill_to_agent to link it."}

        # Write SKILL.md to filesystem
        self.fs.write_skill_md(
            code,
            input["name"],
            input.get("description", ""),
            input.get("allowed_tools", []),
            input.get("body", ""),
        )

        # Create DB record
        skill = Skill(
            code=code,
            name=input["name"],
            description=input.get("description"),
            skill_path=str(self.fs._skill_md_path(code)),
            is_active=True,
        )
        self.db.add(skill)
        await self.db.flush()

        # Auto-attach to agent if one exists
        if session.agent_id:
            agent_skill = AgentSkill(agent_id=session.agent_id, skill_id=skill.id)
            self.db.add(agent_skill)

        # Record artifact
        artifacts = list(session.artifacts or [])
        artifacts.append({
            "type": "skill",
            "id": str(skill.id),
            "code": code,
            "name": input["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session.artifacts = artifacts

        await self.db.commit()

        return {
            "success": True,
            "skill_id": str(skill.id),
            "code": code,
            "attached_to_agent": session.agent_id is not None,
        }

    async def _tool_attach_skill_to_agent(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet"}

        skill_code = input["skill_code"]
        result = await self.db.execute(select(Skill).where(Skill.code == skill_code))
        skill = result.scalar_one_or_none()
        if not skill:
            return {"error": f"Skill '{skill_code}' not found"}

        # Check if already attached
        existing = await self.db.execute(
            select(AgentSkill).where(
                AgentSkill.agent_id == session.agent_id,
                AgentSkill.skill_id == skill.id,
            )
        )
        if existing.scalar_one_or_none():
            return {"info": f"Skill '{skill_code}' is already attached to this agent"}

        agent_skill = AgentSkill(agent_id=session.agent_id, skill_id=skill.id)
        self.db.add(agent_skill)
        await self.db.commit()

        return {"success": True, "skill_code": skill_code, "agent_id": str(session.agent_id)}

    async def _tool_create_tool_definition(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        tool = Tool(
            name=input["name"],
            description=input.get("description"),
            input_schema=input.get("input_schema", {"type": "object", "properties": {}}),
            is_enabled=True,
        )
        self.db.add(tool)
        await self.db.flush()

        # Auto-assign to agent if one exists
        if session.agent_id:
            agent_tool = AgentTool(
                agent_id=session.agent_id,
                tool_id=tool.id,
                is_required=True,
            )
            self.db.add(agent_tool)

        # Record artifact
        artifacts = list(session.artifacts or [])
        artifacts.append({
            "type": "tool",
            "id": str(tool.id),
            "name": input["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session.artifacts = artifacts

        await self.db.commit()

        return {
            "success": True,
            "tool_id": str(tool.id),
            "name": input["name"],
            "assigned_to_agent": session.agent_id is not None,
        }

    async def _tool_create_mcp_server(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        name = input["name"]
        existing = await self.db.execute(select(McpServer).where(McpServer.name == name))
        if existing.scalar_one_or_none():
            return {"error": f"MCP server '{name}' already exists"}

        server = McpServer(
            name=name,
            description=input.get("description"),
            transport=input.get("transport", "http"),
            url=input.get("url"),
            status="unknown",
        )
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)

        # Record artifact
        artifacts = list(session.artifacts or [])
        artifacts.append({
            "type": "mcp_server",
            "id": str(server.id),
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session.artifacts = artifacts
        await self.db.commit()

        return {"success": True, "server_id": str(server.id), "name": name}

    async def _tool_assign_tool_to_agent(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet"}

        tool_id = UUID(input["tool_id"])
        result = await self.db.execute(select(Tool).where(Tool.id == tool_id))
        tool = result.scalar_one_or_none()
        if not tool:
            return {"error": f"Tool {input['tool_id']} not found"}

        existing = await self.db.execute(
            select(AgentTool).where(
                AgentTool.agent_id == session.agent_id,
                AgentTool.tool_id == tool_id,
            )
        )
        if existing.scalar_one_or_none():
            return {"info": "Tool already assigned to this agent"}

        agent_tool = AgentTool(
            agent_id=session.agent_id,
            tool_id=tool_id,
            is_required=True,
        )
        self.db.add(agent_tool)
        await self.db.commit()

        return {"success": True, "tool_name": tool.name, "agent_id": str(session.agent_id)}

    async def _tool_set_process_flow(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet"}

        result = await self.db.execute(
            select(Agent).where(Agent.id == session.agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return {"error": "Draft agent not found"}

        sdk_config = agent.sdk_config or {}
        sdk_config["process_flow"] = input.get("steps", [])
        agent.sdk_config = sdk_config

        # Record artifact
        artifacts = list(session.artifacts or [])
        artifacts.append({
            "type": "process_flow",
            "agent_id": str(agent.id),
            "step_count": len(input.get("steps", [])),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session.artifacts = artifacts

        await self.db.commit()

        return {"success": True, "steps_saved": len(input.get("steps", []))}

    async def _tool_set_knowledge_base(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet"}

        result = await self.db.execute(
            select(Agent).where(Agent.id == session.agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return {"error": "Draft agent not found"}

        sdk_config = agent.sdk_config or {}
        knowledge = sdk_config.get("knowledge_base", {})

        if "faqs" in input:
            knowledge["faqs"] = input["faqs"]
        if "requirements" in input:
            knowledge["requirements"] = input["requirements"]
        if "costs" in input:
            knowledge["costs"] = input["costs"]
        if "links" in input:
            knowledge["links"] = input["links"]

        sdk_config["knowledge_base"] = knowledge
        agent.sdk_config = sdk_config

        # Record artifact
        artifacts = list(session.artifacts or [])
        artifacts.append({
            "type": "knowledge_base",
            "agent_id": str(agent.id),
            "sections": list(input.keys()),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        session.artifacts = artifacts

        await self.db.commit()

        return {"success": True, "sections_updated": list(input.keys())}

    async def _tool_test_agent_message(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet"}

        result = await self.db.execute(
            select(Agent)
            .where(Agent.id == session.agent_id)
            .options(
                selectinload(Agent.agent_tools).selectinload(AgentTool.tool),
            )
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return {"error": "Draft agent not found"}

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return {"error": "ANTHROPIC_API_KEY not configured"}

        # Build messages
        messages = []
        for msg in input.get("conversation_history", []):
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": input["message"]})

        # Build tools payload from agent's assigned tools
        tools_payload = []
        for at in agent.agent_tools:
            tool = at.tool
            if tool and tool.is_enabled:
                tools_payload.append({
                    "name": tool.name,
                    "description": tool.description or f"Tool: {tool.name}",
                    "input_schema": tool.input_schema or {"type": "object", "properties": {}},
                })

        api_body: Dict[str, Any] = {
            "model": agent.model or "claude-sonnet-4-5-20250929",
            "max_tokens": 2048,
            "system": agent.system_prompt or "You are a helpful assistant.",
            "messages": messages,
        }
        if tools_payload:
            api_body["tools"] = tools_payload

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=api_body,
                )

            if resp.status_code != 200:
                return {"error": f"Test API error ({resp.status_code}): {resp.text[:200]}"}

            api_result = resp.json()
            response_text = ""
            for block in api_result.get("content", []):
                if block["type"] == "text":
                    response_text += block["text"]

            return {
                "response": response_text,
                "model": api_result.get("model"),
                "input_tokens": api_result.get("usage", {}).get("input_tokens", 0),
                "output_tokens": api_result.get("usage", {}).get("output_tokens", 0),
            }
        except Exception as e:
            return {"error": f"Test failed: {e}"}

    async def _tool_finalize_agent(
        self, session: BuilderSession, input: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not session.agent_id:
            return {"error": "No draft agent created yet"}

        result = await self.db.execute(
            select(Agent).where(Agent.id == session.agent_id)
        )
        agent = result.scalar_one_or_none()
        if not agent:
            return {"error": "Draft agent not found"}

        agent.status = "stopped"
        session.status = "completed"
        session.phase = "deploy"

        await self.db.commit()

        return {
            "success": True,
            "agent_id": str(agent.id),
            "name": agent.name,
            "status": "stopped",
            "message": "Agent finalized and ready for deployment.",
        }
