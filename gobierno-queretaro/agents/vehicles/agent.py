"""
Gobierno Queretaro - Vehicles Agent
LangGraph-based agent for vehicle registration services
"""

import logging
import operator
import re
from typing import Annotated, Any, AsyncGenerator, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from .config import get_settings
from .prompts import get_system_prompt
from .tools import get_tools

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================
# Agent State
# ============================================

class VehiclesAgentState(TypedDict):
    """State for the Vehicles agent"""

    messages: Annotated[list[BaseMessage], operator.add]
    task_type: str | None
    subtask_results: dict[str, Any]
    current_subtask: str | None
    user_data: dict[str, Any]
    metadata: dict[str, Any]


# ============================================
# Agent Configuration
# ============================================

AGENT_CONFIG = {
    "id": "vehicles",
    "name": "Agente de Vehiculos",
    "category_code": "VEH",
    "task_types": [
        "debt",          # Adeudos
        "plates",        # Placas
        "verification",  # Verificacion
        "fines",         # Infracciones
        "inquiry",       # Consulta general
    ],
    "requires_contract": False,
}


# ============================================
# Node Functions
# ============================================

def get_llm() -> ChatAnthropic:
    """Get configured LLM instance"""
    return ChatAnthropic(
        model=settings.model,
        api_key=settings.anthropic_api_key,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )


def classify_task(state: VehiclesAgentState) -> dict[str, Any]:
    """Classify the vehicle service request into task type with context awareness"""
    messages = state["messages"]
    if not messages:
        return {"task_type": "inquiry", "current_subtask": None}

    # Check for pending task from previous turn
    metadata = state.get("metadata", {})
    pending_task_type = metadata.get("pending_task_type")

    last_message = messages[-1].content if messages else ""
    lower_message = last_message.lower() if isinstance(last_message, str) else ""

    # Build context from conversation history (last 4 messages)
    conversation_context = ""
    for msg in messages[-4:]:
        if hasattr(msg, "content"):
            content = msg.content if isinstance(msg.content, str) else ""
            conversation_context += " " + content.lower()

    # Detect if last message is just data (plate number, etc.)
    # Plate numbers are typically 3-10 alphanumeric characters
    is_data_response = bool(re.match(r"^[a-z0-9]{3,10}$", lower_message.strip()))

    task_type = "inquiry"

    # If user is providing data, continue with pending task
    if is_data_response and pending_task_type:
        task_type = pending_task_type
        logger.info(f"Continuing with pending task: {task_type}")
    else:
        # Use full context for classification if user provided just data
        context_to_check = conversation_context if is_data_response else lower_message

        # Debt keywords
        if any(word in context_to_check for word in [
            "adeudo", "debo", "tenencia", "pagar", "deuda"
        ]):
            task_type = "debt"

        # Plates keywords
        elif any(word in context_to_check for word in [
            "placa", "tarjeta de circulacion", "alta", "cambio de propietario", "reposicion"
        ]):
            task_type = "plates"

        # Verification keywords
        elif any(word in context_to_check for word in [
            "verificacion", "verificar", "holograma", "emisiones"
        ]):
            task_type = "verification"

        # Fines keywords
        elif any(word in context_to_check for word in [
            "multa", "infraccion", "foto multa", "radar"
        ]):
            task_type = "fines"

    logger.info(f"Classified vehicle task type: {task_type}")

    return {
        "task_type": task_type,
        "current_subtask": None,
    }


def route_to_handler(state: VehiclesAgentState) -> str:
    """Route to appropriate task handler"""
    task_type = state.get("task_type", "inquiry")
    return f"handle_{task_type}"


async def handle_debt(state: VehiclesAgentState) -> dict[str, Any]:
    """Handle debt inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("debt")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "debt": {"status": "completed"},
        },
    }


async def handle_plates(state: VehiclesAgentState) -> dict[str, Any]:
    """Handle plates inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("plates")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "plates": {"status": "completed"},
        },
    }


async def handle_verification(state: VehiclesAgentState) -> dict[str, Any]:
    """Handle verification inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("verification")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "verification": {"status": "completed"},
        },
    }


async def handle_fines(state: VehiclesAgentState) -> dict[str, Any]:
    """Handle fines inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("fines")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "fines": {"status": "completed"},
        },
    }


async def handle_inquiry(state: VehiclesAgentState) -> dict[str, Any]:
    """Handle general inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("inquiry")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "inquiry": {"status": "completed"},
        },
    }


def should_continue(state: VehiclesAgentState) -> Literal["tools", "respond"]:
    """Check if we should execute tools or respond"""
    messages = state.get("messages", [])
    if not messages:
        return "respond"

    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "respond"


def generate_response(state: VehiclesAgentState) -> dict[str, Any]:
    """Generate final response"""
    logger.info("Generated vehicles agent response")
    return {}


# ============================================
# Build the Graph
# ============================================

def build_vehicles_agent_graph() -> StateGraph:
    """Build the LangGraph for Vehicles agent"""
    graph = StateGraph(VehiclesAgentState)

    # Add nodes
    graph.add_node("classify", classify_task)
    graph.add_node("handle_debt", handle_debt)
    graph.add_node("handle_plates", handle_plates)
    graph.add_node("handle_verification", handle_verification)
    graph.add_node("handle_fines", handle_fines)
    graph.add_node("handle_inquiry", handle_inquiry)
    graph.add_node("tools", ToolNode(get_tools()))
    graph.add_node("respond", generate_response)

    # Set entry point
    graph.set_entry_point("classify")

    # Add routing from classify
    graph.add_conditional_edges(
        "classify",
        route_to_handler,
        {
            "handle_debt": "handle_debt",
            "handle_plates": "handle_plates",
            "handle_verification": "handle_verification",
            "handle_fines": "handle_fines",
            "handle_inquiry": "handle_inquiry",
        },
    )

    # Add tool execution edges from handlers
    for handler in [
        "handle_debt", "handle_plates", "handle_verification",
        "handle_fines", "handle_inquiry"
    ]:
        graph.add_conditional_edges(
            handler,
            should_continue,
            {
                "tools": "tools",
                "respond": "respond",
            },
        )

    # Tools loop back to respond
    graph.add_edge("tools", "respond")
    graph.add_edge("respond", END)

    return graph


# ============================================
# Agent Runner
# ============================================

class VehiclesAgent:
    """Vehicles Agent wrapper"""

    def __init__(self):
        self.graph = build_vehicles_agent_graph()
        self.app = self.graph.compile()
        self.config = AGENT_CONFIG

    async def run(
        self,
        message: str,
        conversation_history: list[BaseMessage] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the agent with a user message"""
        messages = list(conversation_history or [])
        messages.append(HumanMessage(content=message))

        initial_state: VehiclesAgentState = {
            "messages": messages,
            "task_type": None,
            "subtask_results": {},
            "current_subtask": None,
            "user_data": metadata.get("user_data", {}) if metadata else {},
            "metadata": metadata or {},
        }

        try:
            result = await self.app.ainvoke(initial_state)

            response_messages = result.get("messages", [])
            last_message = response_messages[-1] if response_messages else None

            response_text = ""
            if last_message:
                if isinstance(last_message.content, str):
                    response_text = last_message.content
                elif isinstance(last_message.content, list):
                    response_text = " ".join(
                        block.get("text", "") for block in last_message.content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )

            return {
                "response": response_text,
                "messages": response_messages,
                "task_type": result.get("task_type"),
                "subtask_results": result.get("subtask_results", {}),
                "agent_id": self.config["id"],
            }

        except Exception as e:
            logger.error(f"Vehicles agent error: {e}")
            return {
                "response": "Lo siento, tuve un problema procesando tu solicitud. Puedes intentar de nuevo?",
                "messages": messages,
                "error": str(e),
                "agent_id": self.config["id"],
            }

    async def run_streaming(
        self,
        message: str,
        conversation_history: list[BaseMessage] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
        """
        Stream agent execution, yielding (node_name, node_output) tuples.
        Uses LangGraph's astream() to capture each node transition.
        """
        messages = list(conversation_history or [])
        messages.append(HumanMessage(content=message))

        metadata = metadata or {}

        initial_state: VehiclesAgentState = {
            "messages": messages,
            "task_type": None,
            "subtask_results": {},
            "current_subtask": None,
            "user_data": metadata.get("user_data", {}) if metadata else {},
            "metadata": metadata,
        }

        async for chunk in self.app.astream(initial_state):
            node_name = list(chunk.keys())[0]
            yield (node_name, chunk[node_name])

    def get_health(self) -> dict[str, Any]:
        """Get agent health status"""
        return {
            "status": "healthy",
            "agent_id": self.config["id"],
            "agent_name": self.config["name"],
            "category_code": self.config["category_code"],
            "task_types": self.config["task_types"],
        }


# Singleton
_agent: VehiclesAgent | None = None


def get_agent() -> VehiclesAgent:
    """Get or create the Vehicles agent instance"""
    global _agent
    if _agent is None:
        _agent = VehiclesAgent()
    return _agent
