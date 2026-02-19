"""
Gobierno Queretaro - Women IQM Agent
LangGraph-based agent for women's services
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


class WomenAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    task_type: str | None
    subtask_results: dict[str, Any]
    current_subtask: str | None
    user_data: dict[str, Any]
    metadata: dict[str, Any]


AGENT_CONFIG = {
    "id": "women-iqm",
    "name": "Agente de la Mujer - IQM",
    "category_code": "IQM",
    "task_types": ["violence", "empowerment", "legal", "health", "inquiry"],
    "requires_contract": False,
}


def get_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.model,
        api_key=settings.anthropic_api_key,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )


def classify_task(state: WomenAgentState) -> dict[str, Any]:
    messages = state["messages"]
    if not messages:
        return {"task_type": "inquiry"}

    last_message = messages[-1].content if messages else ""
    lower_message = last_message.lower() if isinstance(last_message, str) else ""

    task_type = "inquiry"

    # Violence detection FIRST
    violence_words = ["violencia", "golpe", "maltrato", "amenaza", "peligro", "miedo", "abuso"]
    if any(word in lower_message for word in violence_words):
        task_type = "violence"
    elif any(word in lower_message for word in ["empleo", "trabajo", "credito", "emprender", "negocio"]):
        task_type = "empowerment"
    elif any(word in lower_message for word in ["abogada", "legal", "pension", "custodia", "divorcio"]):
        task_type = "legal"
    elif any(word in lower_message for word in ["salud", "psicolog", "terapia", "apoyo"]):
        task_type = "health"

    logger.info(f"Classified women task type: {task_type}")
    return {"task_type": task_type, "current_subtask": None}


def route_to_handler(state: WomenAgentState) -> str:
    task_type = state.get("task_type", "inquiry")
    return f"handle_{task_type}"


async def handle_violence(state: WomenAgentState) -> dict[str, Any]:
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)
    system_prompt = get_system_prompt("violence")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "violence": {"status": "completed", "is_emergency": True}}}


async def handle_empowerment(state: WomenAgentState) -> dict[str, Any]:
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)
    system_prompt = get_system_prompt("empowerment")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "empowerment": {"status": "completed"}}}


async def handle_legal(state: WomenAgentState) -> dict[str, Any]:
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)
    system_prompt = get_system_prompt("legal")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "legal": {"status": "completed"}}}


async def handle_health(state: WomenAgentState) -> dict[str, Any]:
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)
    system_prompt = get_system_prompt("health")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "health": {"status": "completed"}}}


async def handle_inquiry(state: WomenAgentState) -> dict[str, Any]:
    llm = get_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)
    system_prompt = get_system_prompt("inquiry")
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "inquiry": {"status": "completed"}}}


def should_continue(state: WomenAgentState) -> Literal["tools", "respond"]:
    messages = state.get("messages", [])
    if not messages:
        return "respond"
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "respond"


def generate_response(state: WomenAgentState) -> dict[str, Any]:
    logger.info("Generated women agent response")
    return {}


def build_women_agent_graph() -> StateGraph:
    graph = StateGraph(WomenAgentState)

    graph.add_node("classify", classify_task)
    graph.add_node("handle_violence", handle_violence)
    graph.add_node("handle_empowerment", handle_empowerment)
    graph.add_node("handle_legal", handle_legal)
    graph.add_node("handle_health", handle_health)
    graph.add_node("handle_inquiry", handle_inquiry)
    graph.add_node("tools", ToolNode(get_tools()))
    graph.add_node("respond", generate_response)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify", route_to_handler,
        {"handle_violence": "handle_violence", "handle_empowerment": "handle_empowerment",
         "handle_legal": "handle_legal", "handle_health": "handle_health", "handle_inquiry": "handle_inquiry"}
    )

    for handler in ["handle_violence", "handle_empowerment", "handle_legal", "handle_health", "handle_inquiry"]:
        graph.add_conditional_edges(handler, should_continue, {"tools": "tools", "respond": "respond"})

    graph.add_edge("tools", "respond")
    graph.add_edge("respond", END)

    return graph


class WomenAgent:
    def __init__(self):
        self.graph = build_women_agent_graph()
        self.app = self.graph.compile()
        self.config = AGENT_CONFIG

    async def run(self, message: str, conversation_history: list[BaseMessage] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        messages = list(conversation_history or [])
        messages.append(HumanMessage(content=message))

        initial_state: WomenAgentState = {
            "messages": messages, "task_type": None, "subtask_results": {},
            "current_subtask": None, "user_data": metadata.get("user_data", {}) if metadata else {},
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
                    response_text = " ".join(block.get("text", "") for block in last_message.content if isinstance(block, dict) and block.get("type") == "text")

            return {"response": response_text, "messages": response_messages, "task_type": result.get("task_type"),
                    "subtask_results": result.get("subtask_results", {}), "agent_id": self.config["id"]}
        except Exception as e:
            logger.error(f"Women agent error: {e}")
            return {"response": "Lo siento, tuve un problema. Si necesitas ayuda urgente: Linea Violeta 800-670-3737",
                    "messages": messages, "error": str(e), "agent_id": self.config["id"]}

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

        initial_state: WomenAgentState = {
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
        return {"status": "healthy", "agent_id": self.config["id"], "agent_name": self.config["name"],
                "category_code": self.config["category_code"], "task_types": self.config["task_types"]}


_agent: WomenAgent | None = None


def get_agent() -> WomenAgent:
    global _agent
    if _agent is None:
        _agent = WomenAgent()
    return _agent
