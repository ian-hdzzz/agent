"""
Gobierno Querétaro - Claude API Wrapper
Shared utilities for interacting with Claude/Anthropic API
"""

import logging
import os
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


# ============================================
# Claude Client
# ============================================

class ClaudeClient:
    """
    Claude API client wrapper with tool support.

    Features:
    - Message creation with tools
    - Streaming support
    - Cost tracking
    - Error handling
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 4096,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.model = model
        self.max_tokens = max_tokens
        self.client = Anthropic(api_key=self.api_key)

    async def generate(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Generate a response from Claude.

        Args:
            system_prompt: System instructions
            messages: Conversation history
            tools: Available tools (optional)
            temperature: Sampling temperature

        Returns:
            Response dict with content, tool_use, usage
        """
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": system_prompt,
                "messages": messages,
                "temperature": temperature,
            }

            if tools:
                kwargs["tools"] = tools

            response = self.client.messages.create(**kwargs)

            # Parse response
            result = {
                "content": "",
                "tool_use": [],
                "stop_reason": response.stop_reason,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }

            for block in response.content:
                if block.type == "text":
                    result["content"] += block.text
                elif block.type == "tool_use":
                    result["tool_use"].append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            return result

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict[str, Any]],
        tool_executor: callable,
        max_iterations: int = 5,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        Generate response with automatic tool execution loop.

        Args:
            system_prompt: System instructions
            user_message: User's message
            tools: Available tools
            tool_executor: Function to execute tools (name, input) -> result
            max_iterations: Max tool call iterations
            conversation_history: Previous messages (optional)

        Returns:
            Final response with all tool results
        """
        messages = list(conversation_history or [])
        messages.append({"role": "user", "content": user_message})

        tools_used = []
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            response = await self.generate(
                system_prompt=system_prompt,
                messages=messages,
                tools=tools,
            )

            # If no tool use, return the response
            if not response["tool_use"]:
                return {
                    "response": response["content"],
                    "tools_used": tools_used,
                    "usage": response["usage"],
                }

            # Execute tools and add results
            tool_results = []
            for tool_call in response["tool_use"]:
                tools_used.append(tool_call["name"])
                try:
                    result = await tool_executor(tool_call["name"], tool_call["input"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": str(result),
                    })
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": f"Error: {e}",
                        "is_error": True,
                    })

            # Add assistant message with tool use
            assistant_content = []
            if response["content"]:
                assistant_content.append({"type": "text", "text": response["content"]})
            for tool_call in response["tool_use"]:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["name"],
                    "input": tool_call["input"],
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # Add tool results
            messages.append({"role": "user", "content": tool_results})

        # Max iterations reached
        logger.warning(f"Max tool iterations ({max_iterations}) reached")
        return {
            "response": response.get("content", ""),
            "tools_used": tools_used,
            "usage": response.get("usage", {}),
            "max_iterations_reached": True,
        }


# ============================================
# Classification Helper
# ============================================

CLASSIFICATION_PROMPT = """Clasifica la solicitud del ciudadano en UNA de estas 13 categorías:

1. CEA - Agua CEA (agua, fugas, deuda de agua, consumos, reconexión)
2. TRA - Transporte AMEQ (rutas, horarios, autobús, tarjetas)
3. EDU - Educación USEBEQ (escuelas, inscripciones, becas educativas)
4. VEH - Vehículos (placas, multas, registro vehicular, licencias)
5. PSI - Psicología SEJUVE (citas, salud mental, orientación)
6. IQM - Atención a Mujeres (apoyo, violencia de género, orientación)
7. CUL - Cultura (eventos, talleres, becas culturales, museos)
8. RPP - Registro Público (documentos, certificados, actas)
9. LAB - Conciliación Laboral (trabajo, demandas, despidos)
10. VIV - Vivienda IVEQ (créditos, programas de vivienda)
11. APP - APPQRO (soporte técnico de la aplicación)
12. SOC - Programas Sociales (beneficios, ayudas, apoyos)
13. ATC - Atención Ciudadana (quejas, sugerencias, PQRS generales)
14. EXIT - El usuario quiere terminar la conversación

Responde SOLO con el código de categoría (CEA, TRA, EDU, VEH, PSI, IQM, CUL, RPP, LAB, VIV, APP, SOC, ATC, EXIT).
No incluyas explicaciones."""


async def classify_intent(
    client: ClaudeClient,
    message: str,
    context: str | None = None,
) -> dict[str, Any]:
    """
    Classify user intent into one of 13 categories.

    Args:
        client: Claude client
        message: User message
        context: Additional context (optional)

    Returns:
        Classification result with category and confidence
    """
    prompt = CLASSIFICATION_PROMPT
    if context:
        prompt = f"{context}\n\n{prompt}"

    response = await client.generate(
        system_prompt=prompt,
        messages=[{"role": "user", "content": message}],
        temperature=0.1,  # Low temperature for classification
    )

    # Parse category from response
    content = response["content"].strip().upper()

    # Extract category code
    valid_categories = [
        "CEA", "TRA", "EDU", "VEH", "PSI", "IQM", "CUL",
        "RPP", "LAB", "VIV", "APP", "SOC", "ATC", "EXIT",
    ]

    category = "ATC"  # Default to citizen attention
    for cat in valid_categories:
        if cat in content:
            category = cat
            break

    return {
        "category": category,
        "raw_response": content,
        "confidence": 0.9 if category != "ATC" else 0.5,  # Lower confidence for default
    }


# ============================================
# Singleton Client
# ============================================

_claude_client: ClaudeClient | None = None


def get_claude_client() -> ClaudeClient:
    """Get or create the singleton Claude client"""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
