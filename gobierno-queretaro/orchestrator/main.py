"""
Gobierno Querétaro - Orchestrator FastAPI Server
HTTP API for the LangGraph routing orchestrator
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

from .classifier import get_category_description
from .config import get_agent_registry, get_settings
from .router import get_orchestrator

# Import security and context modules
from shared.security import SecurityManager, get_security_manager
from shared.security.audit import AuditLogger, AuditEventType, get_audit_logger
from shared.context import SessionStore, get_session_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

settings = get_settings()


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


class AgentInfo(BaseModel):
    """Information about a registered agent"""

    id: str
    name: str
    category_code: str
    description: str
    url: str


# ============================================
# Lifespan Management
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    logger.info("Starting Gobierno Querétaro Orchestrator")
    orchestrator = get_orchestrator()
    registry = get_agent_registry()
    logger.info(f"Initialized with {len(registry)} agents")

    # Initialize security components
    security = get_security_manager()
    audit = get_audit_logger()
    session_store = get_session_store()

    await audit.connect()
    await session_store.connect()

    logger.info("Security and session management initialized")

    yield

    # Shutdown
    logger.info("Shutting down orchestrator")

    # Cleanup security components
    await audit.disconnect()
    await session_store.disconnect()
    logger.info("Security components disconnected")


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="Gobierno Querétaro - Orchestrator",
    description="LangGraph-based routing orchestrator for 13 government service agents",
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

# Security middleware (PII detection, audit logging)
app.add_middleware(SecurityMiddleware)


# ============================================
# Endpoints
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check orchestrator health status"""
    orchestrator = get_orchestrator()
    return orchestrator.get_health()


@app.post("/route", response_model=RouteResponse)
async def route_message(request: RouteRequest):
    """
    Route a message to the appropriate specialist agent.

    This endpoint classifies the user's intent and forwards
    the request to the appropriate specialist agent, returning
    the agent's response.

    Conversation history is maintained via conversation_id.
    """
    from langchain_core.messages import HumanMessage, AIMessage

    try:
        orchestrator = get_orchestrator()
        session_store = get_session_store()

        # Build metadata
        metadata = request.metadata or {}
        if request.conversation_id:
            metadata["conversation_id"] = request.conversation_id
        if request.contact_id:
            metadata["contact_id"] = request.contact_id
        if request.contract_number:
            metadata["contract_number"] = request.contract_number

        # Load conversation history from session if conversation_id provided
        conversation_history = []
        session = None
        if request.conversation_id:
            session = await session_store.get_or_create(
                conversation_id=request.conversation_id,
                contact_id=request.contact_id,
            )
            # Load message history from session shared data
            history_data = session.get_shared("message_history", [])
            for msg in history_data[-10:]:  # Last 10 messages for context
                if msg.get("role") == "user":
                    conversation_history.append(HumanMessage(content=msg["content"]))
                else:
                    conversation_history.append(AIMessage(content=msg["content"]))

        # Retrieve pending task type from session for context continuity
        pending_task_type = None
        if session:
            pending_task_type = session.get_shared("pending_task_type")

        # Route the message with conversation history
        result = await orchestrator.route(
            message=request.message,
            conversation_history=conversation_history,
            metadata={
                **metadata,
                "pending_task_type": pending_task_type,
            },
        )

        # Save updated conversation history to session
        if session and request.conversation_id:
            history_data = session.get_shared("message_history", [])
            history_data.append({"role": "user", "content": request.message})
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


@app.post("/classify", response_model=ClassifyResponse)
async def classify_message(request: ClassifyRequest):
    """
    Classify a message without routing to an agent.

    Useful for testing classification logic or pre-routing
    analysis.
    """
    from .classifier import classify_intent

    try:
        result = await classify_intent(
            message=request.message,
            context=request.context,
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


@app.get("/agents", response_model=list[AgentInfo])
async def list_agents():
    """List all registered specialist agents"""
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


@app.get("/agents/{category_code}", response_model=AgentInfo)
async def get_agent(category_code: str):
    """Get information about a specific agent by category code"""
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


@app.get("/categories")
async def list_categories():
    """List all supported categories with descriptions"""
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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Gobierno Querétaro Orchestrator",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "route": "/route",
            "classify": "/classify",
            "agents": "/agents",
            "categories": "/categories",
        },
    }


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
