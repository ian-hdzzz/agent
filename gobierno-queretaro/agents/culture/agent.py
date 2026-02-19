"""Gobierno Queretaro - Culture Agent"""
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

class CultureAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    task_type: str | None
    subtask_results: dict[str, Any]
    current_subtask: str | None
    user_data: dict[str, Any]
    metadata: dict[str, Any]

AGENT_CONFIG = {"id": "culture", "name": "Agente de Cultura", "category_code": "CUL",
    "task_types": ["events", "workshops", "museums", "inquiry"], "requires_contract": False}

def get_llm() -> ChatAnthropic:
    return ChatAnthropic(model=settings.model, api_key=settings.anthropic_api_key, max_tokens=settings.max_tokens, temperature=settings.temperature)

def classify_task(state: CultureAgentState) -> dict[str, Any]:
    messages = state["messages"]
    if not messages: return {"task_type": "inquiry"}
    last_message = messages[-1].content if messages else ""
    lower_message = last_message.lower() if isinstance(last_message, str) else ""
    task_type = "inquiry"
    if any(word in lower_message for word in ["evento", "concierto", "festival", "teatro", "exposicion"]): task_type = "events"
    elif any(word in lower_message for word in ["taller", "curso", "clase", "aprender"]): task_type = "workshops"
    elif any(word in lower_message for word in ["museo", "galeria", "horario"]): task_type = "museums"
    logger.info(f"Classified culture task: {task_type}")
    return {"task_type": task_type, "current_subtask": None}

def route_to_handler(state: CultureAgentState) -> str:
    return f"handle_{state.get('task_type', 'inquiry')}"

async def handle_events(state: CultureAgentState) -> dict[str, Any]:
    llm_with_tools = get_llm().bind_tools(get_tools())
    messages = [SystemMessage(content=get_system_prompt("events"))] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "events": {"status": "completed"}}}

async def handle_workshops(state: CultureAgentState) -> dict[str, Any]:
    llm_with_tools = get_llm().bind_tools(get_tools())
    messages = [SystemMessage(content=get_system_prompt("workshops"))] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "workshops": {"status": "completed"}}}

async def handle_museums(state: CultureAgentState) -> dict[str, Any]:
    llm_with_tools = get_llm().bind_tools(get_tools())
    messages = [SystemMessage(content=get_system_prompt("museums"))] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "museums": {"status": "completed"}}}

async def handle_inquiry(state: CultureAgentState) -> dict[str, Any]:
    llm_with_tools = get_llm().bind_tools(get_tools())
    messages = [SystemMessage(content=get_system_prompt("inquiry"))] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response], "subtask_results": {**state.get("subtask_results", {}), "inquiry": {"status": "completed"}}}

def should_continue(state: CultureAgentState) -> Literal["tools", "respond"]:
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls: return "tools"
    return "respond"

def generate_response(state: CultureAgentState) -> dict[str, Any]:
    return {}

HANDLERS = {
    "handle_events": handle_events,
    "handle_workshops": handle_workshops,
    "handle_museums": handle_museums,
    "handle_inquiry": handle_inquiry,
}

def build_culture_agent_graph() -> StateGraph:
    graph = StateGraph(CultureAgentState)
    graph.add_node("classify", classify_task)
    for h in ["events", "workshops", "museums", "inquiry"]: graph.add_node(f"handle_{h}", HANDLERS[f"handle_{h}"])
    graph.add_node("tools", ToolNode(get_tools()))
    graph.add_node("respond", generate_response)
    graph.set_entry_point("classify")
    graph.add_conditional_edges("classify", route_to_handler, {f"handle_{h}": f"handle_{h}" for h in ["events", "workshops", "museums", "inquiry"]})
    for h in ["events", "workshops", "museums", "inquiry"]:
        graph.add_conditional_edges(f"handle_{h}", should_continue, {"tools": "tools", "respond": "respond"})
    graph.add_edge("tools", "respond")
    graph.add_edge("respond", END)
    return graph

class CultureAgent:
    def __init__(self):
        self.graph = build_culture_agent_graph()
        self.app = self.graph.compile()
        self.config = AGENT_CONFIG

    async def run(self, message: str, conversation_history: list[BaseMessage] | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        messages = list(conversation_history or [])
        messages.append(HumanMessage(content=message))
        initial_state: CultureAgentState = {"messages": messages, "task_type": None, "subtask_results": {}, "current_subtask": None, "user_data": metadata.get("user_data", {}) if metadata else {}, "metadata": metadata or {}}
        try:
            result = await self.app.ainvoke(initial_state)
            response_messages = result.get("messages", [])
            last_message = response_messages[-1] if response_messages else None
            response_text = ""
            if last_message:
                if isinstance(last_message.content, str): response_text = last_message.content
                elif isinstance(last_message.content, list): response_text = " ".join(block.get("text", "") for block in last_message.content if isinstance(block, dict) and block.get("type") == "text")
            return {"response": response_text, "messages": response_messages, "task_type": result.get("task_type"), "subtask_results": result.get("subtask_results", {}), "agent_id": self.config["id"]}
        except Exception as e:
            logger.error(f"Culture agent error: {e}")
            return {"response": "Lo siento, tuve un problema. Tel: 442-251-9850", "messages": messages, "error": str(e), "agent_id": self.config["id"]}

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

        initial_state: CultureAgentState = {
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
        return {"status": "healthy", "agent_id": self.config["id"], "agent_name": self.config["name"], "category_code": self.config["category_code"], "task_types": self.config["task_types"]}

_agent: CultureAgent | None = None
def get_agent() -> CultureAgent:
    global _agent
    if _agent is None: _agent = CultureAgent()
    return _agent
