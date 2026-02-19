"""Gobierno Queretaro - Citizen Attention Agent FastAPI Server"""
import os as _os

import logging, re, sys
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage
from .agent import get_agent
from .config import get_settings
from .playground import router as playground_router
from .tools import get_tools
from shared.a2a.card_builder import build_agent_card

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)
settings = get_settings()

class QueryRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    contact_id: str | None = None
    conversation_history: list[dict[str, str]] | None = None
    metadata: dict[str, Any] | None = None

class QueryResponse(BaseModel):
    response: str
    agent_id: str
    conversation_id: str | None = None
    task_type: str | None = None
    tools_used: list[str] = []
    ticket_folio: str | None = None
    error: str | None = None

class HealthResponse(BaseModel):
    status: str
    agent_id: str
    agent_name: str
    category_code: str
    task_types: list[str]

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Citizen Attention Agent: {settings.agent_id}")
    agent = get_agent()
    logger.info(f"Agent initialized: {agent.config['name']}")
    yield
    logger.info(f"Shutting down: {settings.agent_id}")

app = FastAPI(title="Gobierno Queretaro - Citizen Attention Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Playground
app.include_router(playground_router)
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
if _os.path.isdir(_static_dir):
    app.mount("/playground/static", StaticFiles(directory=_static_dir), name="playground-static")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return get_agent().get_health()

@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    try:
        agent = get_agent()
        metadata = request.metadata or {}
        if request.conversation_id: metadata["conversation_id"] = request.conversation_id
        if request.contact_id: metadata["contact_id"] = request.contact_id
        history_messages = []
        if request.conversation_history:
            for msg in request.conversation_history:
                if msg.get("role") == "user":
                    history_messages.append(HumanMessage(content=msg["content"]))
                else:
                    history_messages.append(AIMessage(content=msg["content"]))
        result = await agent.run(message=request.message, conversation_history=history_messages, metadata=metadata)
        tools_used = list(result.get("subtask_results", {}).keys())
        ticket_folio = None
        response_text = result.get("response", "")
        folio_match = re.search(r"ATC-\d{8}-[A-Z0-9]{4}", response_text)
        if folio_match: ticket_folio = folio_match.group()
        return QueryResponse(response=result.get("response", ""), agent_id=result.get("agent_id", settings.agent_id), conversation_id=request.conversation_id, task_type=result.get("task_type"), tools_used=tools_used, ticket_folio=ticket_folio, error=result.get("error"))
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

@app.get("/info")
async def agent_info():
    agent = get_agent()
    return {"agent_id": agent.config["id"], "agent_name": agent.config["name"], "category_code": agent.config["category_code"], "task_types": agent.config["task_types"]}

_agent_card_cache: dict | None = None

def _get_agent_card_dict() -> dict:
    global _agent_card_cache
    if _agent_card_cache is None:
        tools = get_tools()
        card = build_agent_card(
            agent_id=settings.agent_id,
            agent_name=getattr(settings, "agent_name", settings.agent_id),
            agent_description=getattr(settings, "agent_description", settings.agent_id),
            url=f"http://{settings.host}:{settings.port}",
            tools=tools,
            version=getattr(settings, "version", "1.0.0"),
        )
        _agent_card_cache = card.model_dump(mode="json", exclude_none=True)
    return _agent_card_cache

@app.get("/.well-known/agent.json")
async def agent_card():
    return _get_agent_card_dict()


@app.get("/")
async def root():
    return {"service": "Gobierno Queretaro - Citizen Attention Agent", "agent_id": settings.agent_id, "status": "running", "endpoints": {"agent_card": "/.well-known/agent.json", "playground": "/playground/ui"}}

@app.get("/playground", include_in_schema=False)
async def playground_redirect():
    """Convenience redirect to playground UI."""
    return RedirectResponse(url="/playground/ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
