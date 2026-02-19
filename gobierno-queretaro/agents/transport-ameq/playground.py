"""
Agent Playground — SSE streaming endpoint for interactive testing.
Serves a self-contained chat + execution-timeline UI.
"""

import logging
import os
import time
from typing import Any

from fastapi import APIRouter
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playground", tags=["playground"])


# ============================================
# Models
# ============================================

class PlaygroundRunRequest(BaseModel):
    """Request to run a message through the agent with streaming."""
    message: str
    conversation_history: list[dict[str, str]] | None = None
    contact_id: str | None = None
    metadata: dict[str, Any] | None = None


class StepEvent(BaseModel):
    """A single step in the agent execution timeline."""
    step: str
    agent_id: str | None = None
    tool_name: str | None = None
    data: dict[str, Any] = {}
    timestamp: float = 0.0
    duration_ms: float | None = None


# ============================================
# Helpers
# ============================================

def _format_sse(event: StepEvent) -> str:
    """Format a StepEvent as an SSE data line."""
    return f"data: {event.model_dump_json()}\n\n"


def _make_step(step: str, **kwargs) -> StepEvent:
    """Create a StepEvent with current timestamp."""
    return StepEvent(step=step, timestamp=time.time(), **kwargs)


# ============================================
# Endpoints
# ============================================

@router.get("/ui")
async def playground_ui():
    """Serve the playground HTML interface."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    html_path = os.path.join(static_dir, "playground.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Playground UI not found")


@router.post("/run")
async def playground_run(request: PlaygroundRunRequest):
    """
    Run a message through the agent and stream execution steps as SSE events.

    Returns a StreamingResponse with text/event-stream content type.
    Each event is a JSON-encoded StepEvent.
    """
    from .agent import get_agent
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    agent = get_agent()
    agent_id = agent.config.get("id", "unknown")

    async def event_stream():
        start_time = time.time()

        yield _format_sse(_make_step(
            "agent_start",
            agent_id=agent_id,
            data={"agent_name": agent.config.get("name", ""), "message": request.message},
        ))

        try:
            history = []
            if request.conversation_history:
                for msg in request.conversation_history:
                    if msg.get("role") == "user":
                        history.append(HumanMessage(content=msg["content"]))
                    else:
                        history.append(AIMessage(content=msg["content"]))

            metadata = request.metadata or {}
            if request.contact_id:
                metadata["contact_id"] = request.contact_id

            last_task_type = None
            final_response_text = ""

            async for node_name, node_output in agent.run_streaming(
                message=request.message,
                conversation_history=history or None,
                metadata=metadata,
            ):
                if node_name == "classify":
                    task_type = node_output.get("task_type", "unknown")
                    last_task_type = task_type
                    yield _format_sse(_make_step(
                        "classify",
                        agent_id=agent_id,
                        data={"task_type": task_type},
                    ))

                elif node_name.startswith("handle_"):
                    yield _format_sse(_make_step(
                        "handler_start",
                        agent_id=agent_id,
                        data={"handler": node_name, "task_type": last_task_type or ""},
                    ))
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessage):
                            if msg.tool_calls:
                                for tc in msg.tool_calls:
                                    yield _format_sse(_make_step(
                                        "tool_call",
                                        agent_id=agent_id,
                                        tool_name=tc.get("name", ""),
                                        data={"input": tc.get("args", {})},
                                    ))
                            else:
                                # This is the final response (no tool calls)
                                if isinstance(msg.content, str):
                                    final_response_text = msg.content
                                elif isinstance(msg.content, list):
                                    final_response_text = " ".join(
                                        block.get("text", "") for block in msg.content
                                        if isinstance(block, dict) and block.get("type") == "text"
                                    )

                elif node_name == "tools":
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, ToolMessage):
                            content = msg.content
                            if isinstance(content, str) and len(content) > 500:
                                content = content[:500] + "..."
                            yield _format_sse(_make_step(
                                "tool_result",
                                agent_id=agent_id,
                                tool_name=getattr(msg, "name", ""),
                                data={"output": content},
                            ))

                elif node_name == "respond":
                    pass  # generate_response returns {} — no new data

            # Emit response event with the collected text
            duration_ms = (time.time() - start_time) * 1000
            if final_response_text:
                yield _format_sse(_make_step(
                    "response",
                    agent_id=agent_id,
                    data={"text": final_response_text, "task_type": last_task_type or ""},
                    duration_ms=round(duration_ms, 1),
                ))

            yield _format_sse(_make_step(
                "done",
                agent_id=agent_id,
                data={"total_duration_ms": round(duration_ms, 1)},
            ))

        except Exception as e:
            logger.error(f"Playground streaming error: {e}")
            yield _format_sse(_make_step(
                "error",
                agent_id=agent_id,
                data={"error": str(e)},
            ))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
