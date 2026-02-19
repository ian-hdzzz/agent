"""
Gobierno Querétaro - Shared Utilities
Common modules for all agents
"""

from .db.models import (
    Agent,
    AgentRequest,
    AgentResponse,
    CategoryCode,
    CATEGORY_DESCRIPTIONS,
    AGENT_ID_BY_CATEGORY,
    ClassificationResult,
    Conversation,
    CreateTicketRequest,
    Event,
    HealthResponse,
    Message,
    SubTask,
    Task,
    Ticket,
)
from .events.pubsub import (
    EventBus,
    EventTypes,
    get_event_bus,
    publish_handoff,
    publish_task_completed,
    publish_ticket_created,
)
from .utils.claude import (
    ClaudeClient,
    classify_intent,
    get_claude_client,
)
from .utils.http_client import (
    ResilientHTTPClient,
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    get_circuit_breaker,
    get_resilient_client,
)
from .security import (
    SecurityManager,
    PII_PATTERNS,
    PIIType,
    detect_pii,
    mask_pii,
    AuditLogger,
    AuditEvent,
    get_security_manager,
)
from .context import (
    SessionContext,
    SessionStore,
    get_session_store,
)
from .api_registry import (
    APIClientFactory,
    APIDefinition,
    get_api_client_factory,
)

__all__ = [
    # Models
    "Agent",
    "AgentRequest",
    "AgentResponse",
    "CategoryCode",
    "CATEGORY_DESCRIPTIONS",
    "AGENT_ID_BY_CATEGORY",
    "ClassificationResult",
    "Conversation",
    "CreateTicketRequest",
    "Event",
    "HealthResponse",
    "Message",
    "SubTask",
    "Task",
    "Ticket",
    # Events
    "EventBus",
    "EventTypes",
    "get_event_bus",
    "publish_handoff",
    "publish_task_completed",
    "publish_ticket_created",
    # Claude
    "ClaudeClient",
    "classify_intent",
    "get_claude_client",
    # HTTP Client
    "ResilientHTTPClient",
    "CircuitBreaker",
    "CircuitState",
    "CircuitOpenError",
    "get_circuit_breaker",
    "get_resilient_client",
    # Security
    "SecurityManager",
    "PII_PATTERNS",
    "PIIType",
    "detect_pii",
    "mask_pii",
    "AuditLogger",
    "AuditEvent",
    "get_security_manager",
    # Context
    "SessionContext",
    "SessionStore",
    "get_session_store",
    # API Registry
    "APIClientFactory",
    "APIDefinition",
    "get_api_client_factory",
]
