"""
Gobierno Querétaro - Agent FastAPI Server
HTTP API for the LangGraph agent with self-registration
"""

import asyncio
import logging
import os as _os
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import get_agent
from .config import get_settings
from .playground import router as playground_router
from .tools import get_tools
from shared.a2a.card_builder import build_agent_card
from shared.registration import register_with_orchestrator, start_heartbeat_loop

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ============================================
# Request/Response Models
# ============================================

class QueryRequest(BaseModel):
    """Request to query the agent"""

    message: str
    conversation_id: str | None = None
    contact_id: str | None = None
    metadata: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    """Response from the agent"""

    response: str
    agent_id: str
    conversation_id: str | None = None
    task_type: str | None = None
    tools_used: list[str] = []
    ticket_folio: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    agent_id: str
    agent_name: str
    category_code: str
    task_types: list[str]


# ============================================
# Lifespan Management
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    logger.info(f"Starting agent: {settings.agent_id}")
    agent = get_agent()
    logger.info(f"Agent initialized: {agent.config['name']}")

    # Initialize persistent memory (best-effort)
    if settings.memory_enabled:
        try:
            from shared.memory import get_paco_memory
            memory = get_paco_memory(scope_id=settings.agent_id)
            await memory.connect()
            logger.info(f"PacoMemory initialized for scope '{settings.agent_id}'")
        except Exception as e:
            logger.warning(f"PacoMemory init failed (memory disabled): {e}")

    # Self-register with orchestrator (best-effort, don't block startup)
    asyncio.create_task(register_with_orchestrator(settings))

    # Start heartbeat background task
    heartbeat_task = asyncio.create_task(start_heartbeat_loop(settings))

    # Company heartbeat loop (per-agent schedule management)
    company_loop = None
    if settings.company_mode_enabled and settings.infrastructure_id:
        try:
            from shared.heartbeat import AgentHeartbeatLoop
            company_loop = AgentHeartbeatLoop(
                agent_slug=settings.agent_id,
                paco_api_url=settings.paco_api_url,
                infrastructure_id=settings.infrastructure_id,
                agent_graph=agent.graph,
            )
            await company_loop.start()
            logger.info(f"Company heartbeat loop started for {settings.agent_id}")
        except Exception as e:
            logger.warning(f"Company heartbeat loop failed to start: {e}")
            company_loop = None

    yield

    # Shutdown
    logger.info(f"Shutting down agent: {settings.agent_id}")
    heartbeat_task.cancel()

    if company_loop:
        await company_loop.stop()

    # Disconnect memory
    if settings.memory_enabled:
        try:
            from shared.memory import get_paco_memory
            memory = get_paco_memory(scope_id=settings.agent_id)
            await memory.disconnect()
        except Exception:
            pass


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title=f"Gobierno Querétaro - {settings.agent_name}",
    description="LangGraph-based government service agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Playground
app.include_router(playground_router)
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
if _os.path.isdir(_static_dir):
    app.mount("/playground/static", StaticFiles(directory=_static_dir), name="playground-static")


# ============================================
# Endpoints
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check agent health status"""
    agent = get_agent()
    return agent.get_health()


@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Query the agent with a user message.

    This endpoint accepts a user message and returns
    the agent's response after processing through
    the LangGraph workflow.
    """
    try:
        agent = get_agent()

        # Prepare metadata
        metadata = request.metadata or {}
        if request.conversation_id:
            metadata["conversation_id"] = request.conversation_id
        if request.contact_id:
            metadata["contact_id"] = request.contact_id

        # Run the agent
        result = await agent.run(
            message=request.message,
            metadata=metadata,
        )

        # Extract tools used from subtask results
        tools_used = []
        subtask_results = result.get("subtask_results", {})
        for subtask_name, subtask_data in subtask_results.items():
            if isinstance(subtask_data, dict) and subtask_data.get("status") == "completed":
                tools_used.append(subtask_name)

        # Check for ticket folio in response
        ticket_folio = None
        response_text = result.get("response", "")
        if "folio" in response_text.lower():
            # Try to extract folio (format: XXX-YYYYMMDD-XXXX)
            import re
            folio_match = re.search(r"[A-Z]{3}-\d{8}-[A-Z0-9]{4}", response_text)
            if folio_match:
                ticket_folio = folio_match.group()

        return QueryResponse(
            response=result.get("response", ""),
            agent_id=result.get("agent_id", settings.agent_id),
            conversation_id=request.conversation_id,
            task_type=result.get("task_type"),
            tools_used=tools_used,
            ticket_folio=ticket_folio,
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}",
        )


@app.get("/info")
async def agent_info():
    """Get agent configuration information"""
    return settings.to_info_dict()


@app.get("/memory/{contact_id}")
async def get_memories(contact_id: str):
    """Get this agent's memories for a citizen (admin proxy use)."""
    if not settings.memory_enabled:
        return {"memories": [], "summaries": [], "message": "Memory disabled for this agent"}
    try:
        from shared.memory import get_paco_memory
        memory = get_paco_memory(scope_id=settings.agent_id)
        bundle = await memory.recall(contact_id)
        if bundle:
            return bundle.model_dump(mode="json")
        return {"memories": [], "summaries": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory error: {str(e)}")


class PeerMessageRequest(BaseModel):
    """Request from a peer agent."""
    sender: str
    content: str
    message_type: str = "direct"
    subject: str | None = None
    metadata: dict[str, Any] | None = None


@app.post("/api/message")
async def receive_peer_message(request: PeerMessageRequest):
    """Receive urgent message from a peer agent (bypasses inbox polling)."""
    try:
        agent = get_agent()
        prompt = f"[Message from {request.sender}]: {request.content}"
        result = await agent.run(
            message=prompt,
            metadata={"message_type": "peer", "sender": request.sender},
        )
        return {
            "status": "processed",
            "response": result.get("response", ""),
        }
    except Exception as e:
        logger.error(f"Peer message error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.get("/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint (placeholder).

    Will be extended with actual Prometheus client metrics.
    """
    return {
        "agent_id": settings.agent_id,
        "version": settings.version,
        "status": "healthy",
    }


# ============================================
# A2A Agent Card
# ============================================

_agent_card_cache: dict | None = None


def _get_agent_card_dict() -> dict:
    """Build and cache the Agent Card as a dict for JSON response."""
    global _agent_card_cache
    if _agent_card_cache is None:
        tools = get_tools()
        card = build_agent_card(
            agent_id=settings.agent_id,
            agent_name=settings.agent_name,
            agent_description=getattr(settings, "agent_description", settings.agent_name),
            url=f"http://{settings.host}:{settings.port}",
            tools=tools,
            version=getattr(settings, "version", "1.0.0"),
        )
        _agent_card_cache = card.model_dump(mode="json", exclude_none=True)
    return _agent_card_cache


@app.get("/.well-known/agent.json")
async def agent_card():
    """Serve A2A Agent Card for agent discovery."""
    return _get_agent_card_dict()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Gobierno Querétaro Agent",
        "agent_id": settings.agent_id,
        "agent_name": settings.agent_name,
        "version": getattr(settings, "version", "1.0.0"),
        "status": "running",
        "endpoints": {
            "health": "/health",
            "query": "/query",
            "info": "/info",
            "metrics": "/metrics",
            "agent_card": "/.well-known/agent.json",
            "playground": "/playground/ui",
        },
    }


@app.get("/playground", include_in_schema=False)
async def playground_redirect():
    """Convenience redirect to playground UI."""
    return RedirectResponse(url="/playground/ui")


# ============================================
# Run Server (for development)
# ============================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
