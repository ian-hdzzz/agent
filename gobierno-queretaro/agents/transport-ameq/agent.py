"""
Gobierno Queretaro - Transport AMEQ Agent
LangGraph-based agent for transport services
"""

import logging
import operator
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

class TransportAgentState(TypedDict):
    """State for the Transport AMEQ agent"""

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
    "id": "transport-ameq",
    "name": "Agente de Transporte - AMEQ",
    "category_code": "TRA",
    "task_types": [
        "routes",      # Consulta de rutas
        "schedules",   # Horarios
        "fares",       # Tarifas
        "report",      # Reportar problema
        "qrobus",      # Tarjeta QroBus
        "inquiry",     # Consulta general
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


def classify_task(state: TransportAgentState) -> dict[str, Any]:
    """Classify the transport service request into task type"""
    messages = state["messages"]
    if not messages:
        return {"task_type": "inquiry"}

    last_message = messages[-1].content if messages else ""
    lower_message = last_message.lower() if isinstance(last_message, str) else ""

    task_type = "inquiry"

    # Routes keywords
    if any(word in lower_message for word in [
        "ruta", "llegar", "ir a", "camion", "autobus", "parada"
    ]):
        task_type = "routes"

    # Schedule keywords
    elif any(word in lower_message for word in [
        "horario", "hora", "pasa", "frecuencia", "cuando"
    ]):
        task_type = "schedules"

    # Fare keywords
    elif any(word in lower_message for word in [
        "costo", "precio", "tarifa", "pasaje", "cuanto cuesta"
    ]):
        task_type = "fares"

    # Report keywords
    elif any(word in lower_message for word in [
        "reportar", "queja", "problema", "accidente", "chofer", "conductor"
    ]):
        task_type = "report"

    # QroBus keywords
    elif any(word in lower_message for word in [
        "qrobus", "tarjeta", "recarga", "saldo"
    ]):
        task_type = "qrobus"

    logger.info(f"Classified transport task type: {task_type}")

    return {
        "task_type": task_type,
        "current_subtask": None,
    }


def route_to_handler(state: TransportAgentState) -> str:
    """Route to appropriate task handler"""
    task_type = state.get("task_type", "inquiry")
    return f"handle_{task_type}"


async def handle_routes(state: TransportAgentState) -> dict[str, Any]:
    """Handle route inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("routes")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "routes": {"status": "completed"},
        },
    }


async def handle_schedules(state: TransportAgentState) -> dict[str, Any]:
    """Handle schedule inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("schedules")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "schedules": {"status": "completed"},
        },
    }


async def handle_fares(state: TransportAgentState) -> dict[str, Any]:
    """Handle fare inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("fares")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "fares": {"status": "completed"},
        },
    }


async def handle_report(state: TransportAgentState) -> dict[str, Any]:
    """Handle service report"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("report")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "report": {"status": "completed"},
        },
    }


async def handle_qrobus(state: TransportAgentState) -> dict[str, Any]:
    """Handle QroBus inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("qrobus")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "qrobus": {"status": "completed"},
        },
    }


async def handle_inquiry(state: TransportAgentState) -> dict[str, Any]:
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


def should_continue(state: TransportAgentState) -> Literal["tools", "respond"]:
    """Check if we should execute tools or respond"""
    messages = state.get("messages", [])
    if not messages:
        return "respond"

    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "respond"


def generate_response(state: TransportAgentState) -> dict[str, Any]:
    """Generate final response"""
    logger.info("Generated transport agent response")
    return {}


# ============================================
# Build the Graph
# ============================================

def build_transport_agent_graph() -> StateGraph:
    """Build the LangGraph for Transport AMEQ agent"""
    graph = StateGraph(TransportAgentState)

    # Add nodes
    graph.add_node("classify", classify_task)
    graph.add_node("handle_routes", handle_routes)
    graph.add_node("handle_schedules", handle_schedules)
    graph.add_node("handle_fares", handle_fares)
    graph.add_node("handle_report", handle_report)
    graph.add_node("handle_qrobus", handle_qrobus)
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
            "handle_routes": "handle_routes",
            "handle_schedules": "handle_schedules",
            "handle_fares": "handle_fares",
            "handle_report": "handle_report",
            "handle_qrobus": "handle_qrobus",
            "handle_inquiry": "handle_inquiry",
        },
    )

    # Add tool execution edges from handlers
    for handler in [
        "handle_routes", "handle_schedules", "handle_fares",
        "handle_report", "handle_qrobus", "handle_inquiry"
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

class TransportAgent:
    """Transport AMEQ Agent wrapper"""

    def __init__(self):
        self.graph = build_transport_agent_graph()
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

        initial_state: TransportAgentState = {
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
            logger.error(f"Transport agent error: {e}")
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

        initial_state: TransportAgentState = {
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
_agent: TransportAgent | None = None


def get_agent() -> TransportAgent:
    """Get or create the Transport agent instance"""
    global _agent
    if _agent is None:
        _agent = TransportAgent()
    return _agent
