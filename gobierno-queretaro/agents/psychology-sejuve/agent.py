"""
Gobierno Queretaro - Psychology SEJUVE Agent
LangGraph-based agent for psychology/mental health services
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

class PsychologyAgentState(TypedDict):
    """State for the Psychology SEJUVE agent"""

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
    "id": "psychology-sejuve",
    "name": "Agente de Psicologia - SEJUVE",
    "category_code": "PSI",
    "task_types": [
        "appointment",   # Citas
        "crisis",        # Crisis emocional
        "addiction",     # Adicciones
        "orientation",   # Orientacion
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


def classify_task(state: PsychologyAgentState) -> dict[str, Any]:
    """Classify the psychology service request into task type"""
    messages = state["messages"]
    if not messages:
        return {"task_type": "inquiry"}

    last_message = messages[-1].content if messages else ""
    lower_message = last_message.lower() if isinstance(last_message, str) else ""

    task_type = "inquiry"

    # CRITICAL: Crisis detection FIRST
    crisis_words = [
        "suicid", "morir", "matarme", "no quiero vivir", "acabar con todo",
        "autolesion", "cortarme", "hacerme dano", "no puedo mas"
    ]
    if any(word in lower_message for word in crisis_words):
        task_type = "crisis"

    # Addiction keywords
    elif any(word in lower_message for word in [
        "adiccion", "droga", "alcohol", "adicto", "consumo", "sustancia"
    ]):
        task_type = "addiction"

    # Appointment keywords
    elif any(word in lower_message for word in [
        "cita", "psicologo", "terapia", "sesion", "atencion"
    ]):
        task_type = "appointment"

    # Orientation keywords
    elif any(word in lower_message for word in [
        "orientacion", "ayuda", "problema", "familia", "escuela", "vocacion"
    ]):
        task_type = "orientation"

    logger.info(f"Classified psychology task type: {task_type}")

    return {
        "task_type": task_type,
        "current_subtask": None,
    }


def route_to_handler(state: PsychologyAgentState) -> str:
    """Route to appropriate task handler"""
    task_type = state.get("task_type", "inquiry")
    return f"handle_{task_type}"


async def handle_appointment(state: PsychologyAgentState) -> dict[str, Any]:
    """Handle appointment request"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("appointment")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "appointment": {"status": "completed"},
        },
    }


async def handle_crisis(state: PsychologyAgentState) -> dict[str, Any]:
    """Handle crisis situation - PRIORITY"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("crisis")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "crisis": {"status": "completed", "is_crisis": True},
        },
    }


async def handle_addiction(state: PsychologyAgentState) -> dict[str, Any]:
    """Handle addiction inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("addiction")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "addiction": {"status": "completed"},
        },
    }


async def handle_orientation(state: PsychologyAgentState) -> dict[str, Any]:
    """Handle orientation inquiry"""
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    system_prompt = get_system_prompt("orientation")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "orientation": {"status": "completed"},
        },
    }


async def handle_inquiry(state: PsychologyAgentState) -> dict[str, Any]:
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


def should_continue(state: PsychologyAgentState) -> Literal["tools", "respond"]:
    """Check if we should execute tools or respond"""
    messages = state.get("messages", [])
    if not messages:
        return "respond"

    last_message = messages[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "respond"


def generate_response(state: PsychologyAgentState) -> dict[str, Any]:
    """Generate final response"""
    logger.info("Generated psychology agent response")
    return {}


# ============================================
# Build the Graph
# ============================================

def build_psychology_agent_graph() -> StateGraph:
    """Build the LangGraph for Psychology SEJUVE agent"""
    graph = StateGraph(PsychologyAgentState)

    # Add nodes
    graph.add_node("classify", classify_task)
    graph.add_node("handle_appointment", handle_appointment)
    graph.add_node("handle_crisis", handle_crisis)
    graph.add_node("handle_addiction", handle_addiction)
    graph.add_node("handle_orientation", handle_orientation)
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
            "handle_appointment": "handle_appointment",
            "handle_crisis": "handle_crisis",
            "handle_addiction": "handle_addiction",
            "handle_orientation": "handle_orientation",
            "handle_inquiry": "handle_inquiry",
        },
    )

    # Add tool execution edges from handlers
    for handler in [
        "handle_appointment", "handle_crisis", "handle_addiction",
        "handle_orientation", "handle_inquiry"
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

class PsychologyAgent:
    """Psychology SEJUVE Agent wrapper"""

    def __init__(self):
        self.graph = build_psychology_agent_graph()
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

        initial_state: PsychologyAgentState = {
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
            logger.error(f"Psychology agent error: {e}")
            return {
                "response": "Lo siento, tuve un problema. Si necesitas ayuda urgente, llama a la Linea de la Vida: 800-911-2000",
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

        initial_state: PsychologyAgentState = {
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
_agent: PsychologyAgent | None = None


def get_agent() -> PsychologyAgent:
    """Get or create the Psychology agent instance"""
    global _agent
    if _agent is None:
        _agent = PsychologyAgent()
    return _agent
