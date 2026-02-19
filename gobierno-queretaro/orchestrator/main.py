"""
Gobierno Queretaro - Orchestrator FastAPI Server
HTTP API for the LangGraph routing orchestrator

API versioning: Core endpoints live under /v1/. Unversioned paths are
backward-compatible aliases that delegate to the v1 implementations.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from .classifier import get_category_description
from .config import (
    get_agent_registry,
    get_settings,
    register_agent as registry_register_agent,
    agent_heartbeat as registry_heartbeat,
    run_health_sweep,
    get_agent_registry_async,
)
from .feedback import router as feedback_router
from .admin import router as admin_router
from .router import get_orchestrator

# Import security and context modules
from shared.security import SecurityManager, get_security_manager
from shared.security.audit import AuditLogger, AuditEventType, get_audit_logger
from shared.context import SessionStore, get_session_store
from shared.tracing.setup import init_tracing, shutdown_tracing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ============================================
# Rate Limiter
# ============================================

limiter = Limiter(key_func=get_remote_address)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Return a proper 429 response with Retry-After header."""
    retry_after = exc.detail.split("per")[-1].strip() if hasattr(exc, "detail") else "60"
    response = JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": str(exc.detail),
            "retry_after": retry_after,
        },
    )
    response.headers["Retry-After"] = retry_after
    return response


# ============================================
# Security Middleware
# ============================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for PII detection, log sanitization, and audit logging.

    Features:
    - Detects PII in incoming requests
    - Sanitizes request data before logging
    - Creates audit trail for all requests
    - Attaches security context to request state
    """

    async def dispatch(self, request: Request, call_next):
        security = get_security_manager()
        audit = get_audit_logger()

        # Get client IP
        client_ip = request.client.host if request.client else None

        # Extract request info for audit
        request_path = request.url.path
        request_method = request.method

        # Skip security processing for health checks
        if request_path == "/health":
            return await call_next(request)

        # Attach security manager to request state
        request.state.security = security
        request.state.audit = audit

        # For POST requests with JSON body, check for PII
        pii_detected = {}
        if request_method == "POST" and request.headers.get("content-type") == "application/json":
            try:
                # Read and cache body for later use
                body = await request.body()
                body_str = body.decode("utf-8")

                # Detect PII in request body
                pii_detected = security.detect_pii(body_str)

                if pii_detected:
                    # Log PII detection (sanitized)
                    await audit.log_pii_detection(
                        text_preview=security.sanitize_for_logging(body_str[:100]),
                        pii_types=list(pii_detected.keys()),
                        conversation_id=None,  # Will be extracted later
                        agent_id="orchestrator",
                    )

                    # Log sanitized version for debugging
                    sanitized_body = security.sanitize_for_logging(body_str)
                    logger.debug(f"Request body (sanitized): {sanitized_body[:200]}")

            except Exception as e:
                logger.warning(f"Failed to process request body for PII: {e}")

        # Store PII detection results in request state
        request.state.pii_detected = pii_detected

        # Log the request (sanitized)
        await audit.log(
            event_type=AuditEventType.MESSAGE_RECEIVED,
            action=f"{request_method} {request_path}",
            actor_type="user",
            actor_ip=client_ip,
            resource_type="endpoint",
            resource_id=request_path,
            details={
                "method": request_method,
                "path": request_path,
                "has_pii": bool(pii_detected),
                "pii_types": list(pii_detected.keys()) if pii_detected else [],
            },
        )

        # Process request
        response = await call_next(request)

        # Log response
        await audit.log(
            event_type=AuditEventType.MESSAGE_SENT,
            action=f"Response {response.status_code} for {request_method} {request_path}",
            actor_type="system",
            actor_ip=client_ip,
            resource_type="endpoint",
            resource_id=request_path,
            success=response.status_code < 400,
            details={
                "status_code": response.status_code,
            },
        )

        return response


# ============================================
# Request/Response Models
# ============================================

class RouteRequest(BaseModel):
    """Request to route a message"""

    message: str
    conversation_id: str | None = None
    contact_id: str | None = None
    contract_number: str | None = None
    metadata: dict[str, Any] | None = None


class RouteResponse(BaseModel):
    """Response from routing"""

    response: str
    category: str | None = None
    category_description: str | None = None
    agent_id: str | None = None
    contract_number: str | None = None
    error: str | None = None


class ClassifyRequest(BaseModel):
    """Request to classify a message (without routing)"""

    message: str
    context: str | None = None


class ClassifyResponse(BaseModel):
    """Response from classification"""

    category: str
    category_description: str
    confidence: float
    method: str


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    agents: list[str]
    agent_count: int
    rate_limits: dict[str, str] | None = None


class AgentInfo(BaseModel):
    """Information about a registered agent"""

    id: str
    name: str
    category_code: str
    description: str
    url: str


class AgentRegistrationRequest(BaseModel):
    """Request for agent self-registration"""

    agent_id: str
    name: str
    description: str = ""
    category_code: str
    endpoint: str
    version: str = "1.0.0"
    confidentiality_level: str = "INTERNAL"
    sla_tier: str = "standard"
    capabilities: dict[str, Any] | None = None


class AgentRegistrationResponse(BaseModel):
    """Response from agent registration"""

    status: str
    agent_id: str
    message: str


class HeartbeatRequest(BaseModel):
    """Agent heartbeat request"""

    agent_id: str


class HeartbeatResponse(BaseModel):
    """Agent heartbeat response"""

    status: str
    agent_id: str


# ============================================
# Lifespan Management
# ============================================

async def _health_sweep_loop():
    """Background task that periodically sweeps for stale agents."""
    import asyncio
    interval = settings.health_sweep_interval
    logger.info(f"Health sweep loop started (interval={interval}s)")
    while True:
        await asyncio.sleep(interval)
        try:
            deactivated = await run_health_sweep()
            if deactivated:
                logger.info(f"Health sweep deactivated {len(deactivated)} agents")
        except Exception as e:
            logger.error(f"Health sweep error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    import asyncio

    # Startup
    logger.info("Starting Gobierno Queretaro Orchestrator")
    orchestrator = get_orchestrator()
    registry = get_agent_registry()
    logger.info(f"Initialized with {len(registry)} agents")

    # Initialize agent-lightning tracing
    init_tracing("orchestrator")
    logger.info("Agent-Lightning tracing initialized")

    # Initialize security components
    security = get_security_manager()
    audit = get_audit_logger()
    session_store = get_session_store()

    await audit.connect()
    await session_store.connect()

    logger.info("Security and session management initialized")

    # Initialize persistent memory for orchestrator scope
    try:
        from shared.memory import get_paco_memory
        memory = get_paco_memory(scope_id="orchestrator")
        await memory.connect()
        logger.info("PacoMemory initialized for orchestrator")
    except Exception as e:
        logger.warning(f"PacoMemory init failed (memory features disabled): {e}")

    # Try to load dynamic registry from DB
    try:
        db_registry = await get_agent_registry_async()
        logger.info(f"Dynamic registry loaded: {len(db_registry)} agents from DB")
    except Exception as e:
        logger.warning(f"Dynamic registry unavailable, using static: {e}")

    # Start health sweep background task
    sweep_task = asyncio.create_task(_health_sweep_loop())

    yield

    # Shutdown
    logger.info("Shutting down orchestrator")

    # Cancel health sweep
    sweep_task.cancel()

    # Cleanup tracing
    await shutdown_tracing()

    # Disconnect memory
    try:
        from shared.memory import get_paco_memory
        memory = get_paco_memory(scope_id="orchestrator")
        await memory.disconnect()
    except Exception:
        pass

    # Cleanup security components
    await audit.disconnect()
    await session_store.disconnect()
    logger.info("Security components disconnected")


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="PACO - Gobierno Queretaro Orchestrator",
    description=(
        "LangGraph-based routing orchestrator for 13 government service agents. "
        "Routes citizen requests to the appropriate specialist agent (water, transport, "
        "education, vehicles, psychology, etc.) and returns structured responses."
    ),
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "PACO Team",
        "url": "https://github.com/gobierno-queretaro/paco",
    },
    openapi_tags=[
        {"name": "routing", "description": "Message routing and classification"},
        {"name": "agents", "description": "Agent registry and discovery"},
        {"name": "health", "description": "Health and operational endpoints"},
        {"name": "feedback", "description": "Human feedback / reward signals"},
        {"name": "admin", "description": "Admin API (requires X-Admin-Key or Paco JWT)"},
        {"name": "compat", "description": "Backward-compatible unversioned aliases"},
    ],
)

# Attach rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware (PII detection, audit logging)
app.add_middleware(SecurityMiddleware)


# ============================================
# v1 Router
# ============================================

v1 = APIRouter(prefix="/v1")


@v1.post("/route", response_model=RouteResponse, tags=["routing"])
@limiter.limit(settings.rate_limit_route)
async def route_message_v1(request: Request, body: RouteRequest):
    """
    Route a message to the appropriate specialist agent.

    This endpoint classifies the user's intent and forwards
    the request to the appropriate specialist agent, returning
    the agent's response.

    Conversation history is maintained via conversation_id.
    """
    return await _do_route(body)


@v1.post("/classify", response_model=ClassifyResponse, tags=["routing"])
@limiter.limit(settings.rate_limit_classify)
async def classify_message_v1(request: Request, body: ClassifyRequest):
    """
    Classify a message without routing to an agent.

    Useful for testing classification logic or pre-routing
    analysis.
    """
    return await _do_classify(body)


@v1.get("/agents", response_model=list[AgentInfo], tags=["agents"])
async def list_agents_v1():
    """List all registered specialist agents"""
    return await _do_list_agents()


@v1.get("/agents/{category_code}", response_model=AgentInfo, tags=["agents"])
async def get_agent_v1(category_code: str):
    """Get information about a specific agent by category code"""
    return await _do_get_agent(category_code)


@v1.get("/categories", tags=["agents"])
async def list_categories_v1():
    """List all supported categories with descriptions"""
    return await _do_list_categories()


@v1.post("/feedback", tags=["feedback"])
async def submit_feedback_v1(request: Request):
    """Submit feedback (proxied from v1 to the feedback router)."""
    # The feedback_router is included separately with its own models.
    # This endpoint exists so /v1/feedback is documented; the actual
    # handler is the one mounted at /feedback (included via feedback_router).
    raise HTTPException(status_code=307, headers={"Location": "/feedback"})


@v1.post("/register", response_model=AgentRegistrationResponse, tags=["agents"])
async def register_agent_v1(body: AgentRegistrationRequest):
    """Register or update an agent in the dynamic registry."""
    return await _do_register_agent(body)


@v1.post("/heartbeat", response_model=HeartbeatResponse, tags=["agents"])
async def heartbeat_v1(body: HeartbeatRequest):
    """Agent heartbeat to signal liveness."""
    return await _do_heartbeat(body)


# Include v1 router
app.include_router(v1)


# ============================================
# Feedback & Admin (root-level, not versioned)
# ============================================

# Feedback endpoint for human reward signals
app.include_router(feedback_router, tags=["feedback"])

# Admin API + memory management
app.include_router(admin_router)

# Serve admin dashboard static files
import os as _os
_static_dir = _os.path.join(_os.path.dirname(__file__), "static")
if _os.path.isdir(_static_dir):
    app.mount("/admin/static", StaticFiles(directory=_static_dir), name="admin-static")


# ============================================
# Operational Endpoints (root-level)
# ============================================

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    """Check orchestrator health status"""
    orchestrator = get_orchestrator()
    health = orchestrator.get_health()
    # Enrich with rate limit configuration
    health["rate_limits"] = {
        "route": settings.rate_limit_route,
        "classify": settings.rate_limit_classify,
    }
    return health


@app.get("/", tags=["health"])
async def root():
    """Root endpoint"""
    return {
        "service": "PACO - Gobierno Queretaro Orchestrator",
        "version": "1.0.0",
        "api_version": "v1",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "redoc": "/redoc",
            "v1": {
                "route": "/v1/route",
                "classify": "/v1/classify",
                "agents": "/v1/agents",
                "categories": "/v1/categories",
                "feedback": "/v1/feedback",
                "register": "/v1/register",
                "heartbeat": "/v1/heartbeat",
            },
            "admin": "/admin/ui",
        },
    }


# ============================================
# Backward-Compatible Unversioned Aliases
# ============================================

@app.post("/route", response_model=RouteResponse, tags=["compat"],
          summary="Route message (compat alias for /v1/route)")
@limiter.limit(settings.rate_limit_route)
async def route_message_compat(request: Request, body: RouteRequest):
    """Backward-compatible alias. Prefer /v1/route."""
    return await _do_route(body)


@app.post("/classify", response_model=ClassifyResponse, tags=["compat"],
          summary="Classify message (compat alias for /v1/classify)")
@limiter.limit(settings.rate_limit_classify)
async def classify_message_compat(request: Request, body: ClassifyRequest):
    """Backward-compatible alias. Prefer /v1/classify."""
    return await _do_classify(body)


@app.get("/agents", response_model=list[AgentInfo], tags=["compat"],
         summary="List agents (compat alias for /v1/agents)")
async def list_agents_compat():
    """Backward-compatible alias. Prefer /v1/agents."""
    return await _do_list_agents()


@app.get("/agents/{category_code}", response_model=AgentInfo, tags=["compat"],
         summary="Get agent (compat alias for /v1/agents/{category_code})")
async def get_agent_compat(category_code: str):
    """Backward-compatible alias. Prefer /v1/agents/{category_code}."""
    return await _do_get_agent(category_code)


@app.get("/categories", tags=["compat"],
         summary="List categories (compat alias for /v1/categories)")
async def list_categories_compat():
    """Backward-compatible alias. Prefer /v1/categories."""
    return await _do_list_categories()


@app.post("/register", response_model=AgentRegistrationResponse, tags=["compat"],
          summary="Register agent (compat alias for /v1/register)")
async def register_agent_compat(body: AgentRegistrationRequest):
    """Backward-compatible alias. Prefer /v1/register."""
    return await _do_register_agent(body)


@app.post("/heartbeat", response_model=HeartbeatResponse, tags=["compat"],
          summary="Heartbeat (compat alias for /v1/heartbeat)")
async def heartbeat_compat(body: HeartbeatRequest):
    """Backward-compatible alias. Prefer /v1/heartbeat."""
    return await _do_heartbeat(body)


# ============================================
# Shared Implementation Functions
# ============================================

async def _do_route(body: RouteRequest) -> RouteResponse:
    """Core routing logic shared by /v1/route and /route."""
    from langchain_core.messages import HumanMessage, AIMessage

    try:
        orchestrator = get_orchestrator()
        session_store = get_session_store()

        # Build metadata
        metadata = body.metadata or {}
        if body.conversation_id:
            metadata["conversation_id"] = body.conversation_id
        if body.contact_id:
            metadata["contact_id"] = body.contact_id
        if body.contract_number:
            metadata["contract_number"] = body.contract_number

        # Load conversation history from session if conversation_id provided
        conversation_history = []
        session = None
        if body.conversation_id:
            session = await session_store.get_or_create(
                conversation_id=body.conversation_id,
                contact_id=body.contact_id,
            )
            # Load message history from session shared data
            history_data = session.get_shared("message_history", [])
            for msg in history_data[-10:]:  # Last 10 messages for context
                if msg.get("role") == "user":
                    conversation_history.append(HumanMessage(content=msg["content"]))
                else:
                    conversation_history.append(AIMessage(content=msg["content"]))

        # Retrieve session context for continuity
        pending_task_type = None
        last_category = None
        if session:
            pending_task_type = session.get_shared("pending_task_type")
            last_category = session.get_shared("last_category")

        # Recall citizen profile for routing context
        if body.contact_id:
            try:
                from shared.memory import get_paco_memory
                memory = get_paco_memory(scope_id="orchestrator")
                profile = await memory.recall_citizen_profile(body.contact_id)
                if profile:
                    metadata["citizen_context"] = {
                        "total_conversations": profile.total_conversations,
                        "total_tickets": profile.total_tickets,
                        "frequent_categories": profile.frequent_categories,
                        "tags": profile.tags,
                    }
            except Exception as e:
                logger.debug(f"Memory recall skipped: {e}")

        # Route the message with conversation history
        result = await orchestrator.route(
            message=body.message,
            conversation_history=conversation_history,
            metadata={
                **metadata,
                "pending_task_type": pending_task_type,
                "last_category": last_category,
            },
        )

        # Save updated conversation history to session
        if session and body.conversation_id:
            history_data = session.get_shared("message_history", [])
            history_data.append({"role": "user", "content": body.message})
            if result.get("response"):
                history_data.append({"role": "assistant", "content": result["response"]})
            # Keep last 20 messages
            session.set_shared("message_history", history_data[-20:])
            # Track which agent handled this
            if result.get("agent_id"):
                session.record_agent_visit(result["agent_id"])
            # Store pending task type for context continuity
            if result.get("task_type"):
                session.set_shared("pending_task_type", result["task_type"])
            if result.get("category"):
                session.set_shared("last_category", result["category"])
            await session_store.update(session)

        # Snapshot conversation for nightly batch summarization
        if body.contact_id and body.conversation_id:
            try:
                from shared.memory import get_paco_memory
                memory = get_paco_memory(scope_id="orchestrator")
                history = session.get_shared("message_history", []) if session else []
                await memory.snapshot_conversation(
                    contact_id=body.contact_id,
                    conversation_id=body.conversation_id,
                    messages=history,
                    agents_involved=[result.get("agent_id")] if result.get("agent_id") else [],
                    categories_involved=[result.get("category", "ATC")],
                )
            except Exception as e:
                logger.debug(f"Snapshot save skipped: {e}")

        return RouteResponse(
            response=result.get("response", ""),
            category=result.get("category"),
            category_description=result.get("category_description"),
            agent_id=result.get("agent_id"),
            contract_number=result.get("contract_number"),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Route error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Orchestrator error: {str(e)}",
        )


async def _do_classify(body: ClassifyRequest) -> ClassifyResponse:
    """Core classification logic shared by /v1/classify and /classify."""
    from .classifier import classify_intent

    try:
        result = await classify_intent(
            message=body.message,
            context=body.context,
        )

        return ClassifyResponse(
            category=result["category"],
            category_description=get_category_description(result["category"]),
            confidence=result.get("confidence", 0.0),
            method=result.get("method", "unknown"),
        )

    except Exception as e:
        logger.error(f"Classify error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Classification error: {str(e)}",
        )


async def _do_list_agents() -> list[AgentInfo]:
    """Core agent listing logic."""
    registry = get_agent_registry()

    return [
        AgentInfo(
            id=info["id"],
            name=info["name"],
            category_code=category,
            description=info["description"],
            url=info["url"],
        )
        for category, info in registry.items()
    ]


async def _do_get_agent(category_code: str) -> AgentInfo:
    """Core get-agent logic."""
    registry = get_agent_registry()

    category_upper = category_code.upper()
    if category_upper not in registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found for category: {category_code}",
        )

    info = registry[category_upper]
    return AgentInfo(
        id=info["id"],
        name=info["name"],
        category_code=category_upper,
        description=info["description"],
        url=info["url"],
    )


async def _do_list_categories():
    """Core categories listing logic."""
    from .classifier import KEYWORD_MAP

    registry = get_agent_registry()

    return {
        category: {
            "description": get_category_description(category),
            "agent": registry.get(category, {}).get("name", "Unknown"),
            "keywords": KEYWORD_MAP.get(category, [])[:5],  # First 5 keywords
        }
        for category in [
            "CEA", "TRA", "EDU", "VEH", "PSI", "IQM", "CUL",
            "RPP", "LAB", "VIV", "APP", "SOC", "ATC",
        ]
    }


async def _do_register_agent(body: AgentRegistrationRequest) -> AgentRegistrationResponse:
    """Core agent registration logic."""
    try:
        success = await registry_register_agent(body.model_dump())
        if success:
            return AgentRegistrationResponse(
                status="registered",
                agent_id=body.agent_id,
                message=f"Agent {body.agent_id} registered successfully",
            )
        else:
            return AgentRegistrationResponse(
                status="failed",
                agent_id=body.agent_id,
                message="Registration failed (DB unavailable), agent will use static config",
            )
    except Exception as e:
        logger.error(f"Registration error for {body.agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Registration error: {str(e)}",
        )


async def _do_heartbeat(body: HeartbeatRequest) -> HeartbeatResponse:
    """Core heartbeat logic."""
    success = await registry_heartbeat(body.agent_id)
    return HeartbeatResponse(
        status="ok" if success else "failed",
        agent_id=body.agent_id,
    )


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
