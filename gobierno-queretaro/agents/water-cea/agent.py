"""
Gobierno Querétaro - Water CEA Agent
LangGraph-based agent for water services
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

class WaterAgentState(TypedDict):
    """State for the Water CEA agent"""

    messages: Annotated[list[BaseMessage], operator.add]
    task_type: str | None
    subtask_results: dict[str, Any]
    current_subtask: str | None
    contract_number: str | None
    user_data: dict[str, Any]
    metadata: dict[str, Any]


# ============================================
# Agent Configuration
# ============================================

AGENT_CONFIG = {
    "id": "water-cea",
    "name": "Agente de Agua - CEA",
    "category_code": "CEA",
    "task_types": [
        "balance",       # Consulta de saldo
        "consumption",   # Historial de consumo
        "contract",      # Información de contrato
        "report",        # Reportar fuga/problema
        "reconnection",  # Reconexión
        "inquiry",       # Consulta general
    ],
    "requires_contract": True,
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


def classify_task(state: WaterAgentState) -> dict[str, Any]:
    """Classify the water service request into task type"""
    messages = state["messages"]
    if not messages:
        return {"task_type": "inquiry"}

    last_message = messages[-1].content if messages else ""
    lower_message = last_message.lower() if isinstance(last_message, str) else ""

    task_type = "inquiry"

    # Balance/debt keywords
    if any(word in lower_message for word in [
        "saldo", "debo", "deuda", "adeudo", "pagar", "cuánto", "cuanto"
    ]):
        task_type = "balance"

    # Consumption keywords
    elif any(word in lower_message for word in [
        "consumo", "historial", "gastado", "metros", "m3", "litros"
    ]):
        task_type = "consumption"

    # Contract keywords
    elif any(word in lower_message for word in [
        "contrato", "titular", "dirección", "direccion", "datos"
    ]) and "nuevo" not in lower_message:
        task_type = "contract"

    # Report keywords
    elif any(word in lower_message for word in [
        "fuga", "reportar", "drenaje", "agua turbia", "sin agua",
        "no hay agua", "huele", "tapado"
    ]):
        task_type = "report"

    # Reconnection keywords
    elif any(word in lower_message for word in [
        "reconexión", "reconexion", "corte", "cortaron", "suspendido"
    ]):
        task_type = "reconnection"

    logger.info(f"Classified water task type: {task_type}")

    return {
        "task_type": task_type,
        "current_subtask": None,
    }


def route_to_handler(state: WaterAgentState) -> str:
    """Route to appropriate task handler"""
    task_type = state.get("task_type", "inquiry")
    return f"handle_{task_type}"


async def handle_balance(state: WaterAgentState) -> dict[str, Any]:
    """Handle balance inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("balance")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "balance": {"status": "completed"},
        },
    }


async def handle_consumption(state: WaterAgentState) -> dict[str, Any]:
    """Handle consumption history inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("consumption")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "consumption": {"status": "completed"},
        },
    }


async def handle_contract(state: WaterAgentState) -> dict[str, Any]:
    """Handle contract information inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("contract")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "contract": {"status": "completed"},
        },
    }


async def handle_report(state: WaterAgentState) -> dict[str, Any]:
    """Handle service report (leak, drainage, etc.)"""
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


async def handle_reconnection(state: WaterAgentState) -> dict[str, Any]:
    """Handle reconnection inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("reconnection")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "reconnection": {"status": "completed"},
        },
    }


async def handle_inquiry(state: WaterAgentState) -> dict[str, Any]:
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


def should_continue(state: WaterAgentState) -> Literal["tools", "respond"]:
    """Check if we should execute tools or respond"""
    messages = state.get("messages", [])
    if not messages:
        return "respond"

    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "respond"


def generate_response(state: WaterAgentState) -> dict[str, Any]:
    """Generate final response"""
    logger.info(f"Generated water agent response")
    return {}


# ============================================
# Build the Graph
# ============================================

def build_water_agent_graph() -> StateGraph:
    """Build the LangGraph for Water CEA agent"""
    graph = StateGraph(WaterAgentState)

    # Add nodes
    graph.add_node("classify", classify_task)
    graph.add_node("handle_balance", handle_balance)
    graph.add_node("handle_consumption", handle_consumption)
    graph.add_node("handle_contract", handle_contract)
    graph.add_node("handle_report", handle_report)
    graph.add_node("handle_reconnection", handle_reconnection)
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
            "handle_balance": "handle_balance",
            "handle_consumption": "handle_consumption",
            "handle_contract": "handle_contract",
            "handle_report": "handle_report",
            "handle_reconnection": "handle_reconnection",
            "handle_inquiry": "handle_inquiry",
        },
    )

    # Add tool execution edges from handlers
    for handler in [
        "handle_balance", "handle_consumption", "handle_contract",
        "handle_report", "handle_reconnection", "handle_inquiry"
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

class WaterAgent:
    """Water CEA Agent wrapper"""

    def __init__(self):
        self.graph = build_water_agent_graph()
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

        initial_state: WaterAgentState = {
            "messages": messages,
            "task_type": None,
            "subtask_results": {},
            "current_subtask": None,
            "contract_number": metadata.get("contract_number") if metadata else None,
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
            logger.error(f"Water agent error: {e}")
            return {
                "response": "Lo siento, tuve un problema procesando tu solicitud. ¿Podrías intentar de nuevo?",
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

        initial_state: WaterAgentState = {
            "messages": messages,
            "task_type": None,
            "subtask_results": {},
            "current_subtask": None,
            "contract_number": metadata.get("contract_number") if metadata else None,
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
_agent: WaterAgent | None = None


def get_agent() -> WaterAgent:
    """Get or create the Water agent instance"""
    global _agent
    if _agent is None:
        _agent = WaterAgent()
    return _agent
