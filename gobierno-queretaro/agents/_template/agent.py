"""
Gobierno Querétaro - LangGraph Agent Template
Base agent implementation with task/subtask support

This is a TEMPLATE. Each specialized agent should:
1. Copy this structure
2. Override AGENT_CONFIG
3. Add domain-specific tools in tools.py
4. Customize prompts in prompts.py
"""

import logging
import operator
from typing import Annotated, Any, AsyncGenerator, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from agentlightning.agent import emit_annotation, emit_message, operation

from .config import get_settings
from .prompts import get_system_prompt
from .tools import get_tools

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================
# Agent State Definition
# ============================================

class AgentState(TypedDict):
    """
    State for the LangGraph agent.

    Attributes:
        messages: Conversation history
        task_type: Classified task type
        subtask_results: Results from completed subtasks
        current_subtask: Currently executing subtask
        contract_number: Extracted contract number (if any)
        user_data: Collected user information
        metadata: Additional context
    """

    messages: Annotated[list[BaseMessage], operator.add]
    task_type: str | None
    subtask_results: dict[str, Any]
    current_subtask: str | None
    contract_number: str | None
    user_data: dict[str, Any]
    metadata: dict[str, Any]


# ============================================
# Agent Configuration (Override per agent)
# ============================================

AGENT_CONFIG = {
    "id": "template-agent",
    "name": "Template Agent",
    "category_code": "ATC",
    "task_types": [
        "general_inquiry",
        "create_ticket",
        "check_status",
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


def classify_task(state: AgentState) -> dict[str, Any]:
    """
    Classify the user's request into a task type.

    This node analyzes the conversation and determines
    what type of task the user is requesting.
    """
    messages = state["messages"]
    if not messages:
        return {"task_type": "general_inquiry"}

    # Get last user message
    last_message = messages[-1].content if messages else ""

    # Simple keyword-based classification (override per agent)
    task_type = "general_inquiry"

    # Example classification logic (customize per agent)
    lower_message = last_message.lower() if isinstance(last_message, str) else ""

    if any(word in lower_message for word in ["ticket", "reporte", "queja", "solicitud"]):
        task_type = "create_ticket"
    elif any(word in lower_message for word in ["estado", "estatus", "seguimiento", "folio"]):
        task_type = "check_status"

    logger.info(f"Classified task type: {task_type}")

    return {
        "task_type": task_type,
        "current_subtask": None,
    }


def route_to_handler(state: AgentState) -> str:
    """
    Route to appropriate task handler based on task_type.

    Returns the name of the next node to execute.
    """
    task_type = state.get("task_type", "general_inquiry")

    # Map task types to handler nodes
    handler_map = {
        "general_inquiry": "handle_inquiry",
        "create_ticket": "handle_ticket",
        "check_status": "handle_status",
    }

    return handler_map.get(task_type, "handle_inquiry")


async def handle_inquiry(state: AgentState) -> dict[str, Any]:
    """Handle general inquiry tasks"""
    llm = get_llm()
    tools = get_tools()

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    # Create system message
    system_prompt = get_system_prompt("inquiry")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    # Generate response
    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "inquiry": {"status": "completed"},
        },
    }


async def handle_ticket(state: AgentState) -> dict[str, Any]:
    """Handle ticket creation tasks"""
    llm = get_llm()
    tools = get_tools()

    llm_with_tools = llm.bind_tools(tools) if tools else llm

    system_prompt = get_system_prompt("ticket")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "ticket": {"status": "completed"},
        },
    }


async def handle_status(state: AgentState) -> dict[str, Any]:
    """Handle status check tasks"""
    llm = get_llm()
    tools = get_tools()

    llm_with_tools = llm.bind_tools(tools) if tools else llm

    system_prompt = get_system_prompt("status")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [response],
        "subtask_results": {
            **state.get("subtask_results", {}),
            "status": {"status": "completed"},
        },
    }


def should_continue(state: AgentState) -> Literal["tools", "respond"]:
    """
    Determine if we should execute tools or generate final response.

    Checks if the last message contains tool calls.
    """
    messages = state.get("messages", [])
    if not messages:
        return "respond"

    last_message = messages[-1]

    # Check if last message has tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "respond"


def generate_response(state: AgentState) -> dict[str, Any]:
    """
    Generate final response from state.

    This node creates the final response to send back to the user,
    incorporating any tool results and subtask completions.
    """
    messages = state.get("messages", [])
    subtask_results = state.get("subtask_results", {})

    # The response is already in messages from the handler
    # This node can add any final processing

    logger.info(f"Generated response with subtasks: {list(subtask_results.keys())}")

    return {}  # No state changes needed


# ============================================
# Build the Graph
# ============================================

def build_agent_graph() -> StateGraph:
    """
    Build the LangGraph agent graph.

    Graph structure:
    1. classify -> route to handler
    2. handler -> check for tool calls
    3. tools (if needed) -> back to handler
    4. respond -> END
    """
    # Initialize graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("classify", classify_task)
    graph.add_node("handle_inquiry", handle_inquiry)
    graph.add_node("handle_ticket", handle_ticket)
    graph.add_node("handle_status", handle_status)
    graph.add_node("tools", ToolNode(get_tools()))
    graph.add_node("respond", generate_response)

    # Set entry point
    graph.set_entry_point("classify")

    # Add conditional edges from classify
    graph.add_conditional_edges(
        "classify",
        route_to_handler,
        {
            "handle_inquiry": "handle_inquiry",
            "handle_ticket": "handle_ticket",
            "handle_status": "handle_status",
        },
    )

    # Add conditional edges from handlers
    for handler in ["handle_inquiry", "handle_ticket", "handle_status"]:
        graph.add_conditional_edges(
            handler,
            should_continue,
            {
                "tools": "tools",
                "respond": "respond",
            },
        )

    # Tools loop back to appropriate handler
    graph.add_edge("tools", "respond")

    # Response ends the graph
    graph.add_edge("respond", END)

    return graph


# ============================================
# Agent Runner
# ============================================

class Agent:
    """
    Wrapper class for the LangGraph agent.

    Provides a simple interface for running the agent
    and managing conversation state.
    """

    def __init__(self):
        self.graph = build_agent_graph()
        self.app = self.graph.compile()
        self.config = AGENT_CONFIG

    async def run(
        self,
        message: str,
        conversation_history: list[BaseMessage] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run the agent with a user message.

        Args:
            message: User's message
            conversation_history: Previous messages (optional)
            metadata: Additional context (optional)

        Returns:
            Agent response with messages and state
        """
        # Build initial state
        messages = list(conversation_history or [])
        messages.append(HumanMessage(content=message))

        metadata = metadata or {}

        # Memory recall — each agent's own scoped memories
        if settings.memory_enabled:
            contact_id = metadata.get("contact_id")
            if contact_id:
                try:
                    from shared.memory import get_paco_memory
                    memory = get_paco_memory(scope_id=self.config["id"])
                    bundle = await memory.recall(contact_id)
                    if bundle and bundle.formatted_context:
                        metadata["memory_context"] = bundle.formatted_context
                except Exception as e:
                    logger.warning(f"Memory recall failed: {e}")

        initial_state: AgentState = {
            "messages": messages,
            "task_type": None,
            "subtask_results": {},
            "current_subtask": None,
            "contract_number": metadata.get("contract_number"),
            "user_data": metadata.get("user_data", {}),
            "metadata": metadata,
        }

        agent_id = self.config["id"]

        with operation(name=f"agent.{agent_id}"):
            try:
                # Emit incoming message for tracing
                try:
                    emit_message(message, attributes={"message.role": "user"})
                except Exception:
                    pass

                # Run the graph
                result = await self.app.ainvoke(initial_state)

                # Extract response
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

                # Emit agent response and task classification for tracing
                try:
                    emit_message(
                        response_text,
                        attributes={"message.role": "assistant"},
                    )
                    emit_annotation({
                        "agent.task_type": result.get("task_type", ""),
                        "agent.id": agent_id,
                    })
                except Exception:
                    pass

                return {
                    "response": response_text,
                    "messages": response_messages,
                    "task_type": result.get("task_type"),
                    "subtask_results": result.get("subtask_results", {}),
                    "agent_id": agent_id,
                }

            except Exception as e:
                logger.error(f"Agent error: {e}")
                return {
                    "response": "Lo siento, tuve un problema procesando tu solicitud. ¿Podrías intentar de nuevo?",
                    "messages": messages,
                    "error": str(e),
                    "agent_id": agent_id,
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

        initial_state: AgentState = {
            "messages": messages,
            "task_type": None,
            "subtask_results": {},
            "current_subtask": None,
            "contract_number": metadata.get("contract_number"),
            "user_data": metadata.get("user_data", {}),
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


# Singleton agent instance
_agent: Agent | None = None


def get_agent() -> Agent:
    """Get or create the singleton agent instance"""
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent
