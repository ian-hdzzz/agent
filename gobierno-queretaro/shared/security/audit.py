"""
Gobierno Queretaro - Audit Logging
Secure audit trail for compliance and security monitoring
"""

import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication & Authorization
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"

    # Data Access
    DATA_READ = "data.read"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"

    # PII Handling
    PII_DETECTED = "pii.detected"
    PII_ACCESSED = "pii.accessed"
    PII_MASKED = "pii.masked"
    PII_ENCRYPTED = "pii.encrypted"

    # Agent Operations
    AGENT_CALLED = "agent.called"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"
    AGENT_HANDOFF = "agent.handoff"

    # Conversation
    CONVERSATION_START = "conversation.start"
    CONVERSATION_END = "conversation.end"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"

    # Tickets
    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"
    TICKET_RESOLVED = "ticket.resolved"

    # System
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    CONFIG_CHANGED = "config.changed"

    # Security
    SECURITY_ALERT = "security.alert"
    RATE_LIMIT_HIT = "security.rate_limit"
    SUSPICIOUS_ACTIVITY = "security.suspicious"

    # Memory
    MEMORY_CREATED = "memory.created"
    MEMORY_READ = "memory.read"
    MEMORY_DELETED = "memory.deleted"
    CITIZEN_FORGOTTEN = "memory.citizen_forgotten"
    MEMORY_CONFIG_CHANGED = "memory.config_changed"


ConfidentialityLevel = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]


class AuditEvent(BaseModel):
    """Audit event record."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: AuditEventType
    confidentiality_level: ConfidentialityLevel = "INTERNAL"

    # Actor information
    actor_type: Literal["user", "agent", "system"] = "system"
    actor_id: str | None = None
    actor_ip: str | None = None

    # Context
    session_id: str | None = None
    conversation_id: str | None = None
    agent_id: str | None = None

    # Event details
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    # Outcome
    success: bool = True
    error_message: str | None = None

    # Sanitized flag (PII removed)
    sanitized: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class AuditLogger:
    """
    Audit logger with Redis persistence and optional PostgreSQL storage.

    Features:
    - Immediate Redis stream storage for real-time access
    - Automatic PII sanitization
    - Confidentiality-aware logging
    - Batch PostgreSQL persistence (optional)
    """

    def __init__(
        self,
        redis_url: str | None = None,
        service_name: str = "gobierno-queretaro",
        max_stream_length: int = 100000,
    ):
        """
        Initialize AuditLogger.

        Args:
            redis_url: Redis connection URL
            service_name: Name of the service for identification
            max_stream_length: Maximum entries in Redis stream
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.service_name = service_name
        self.max_stream_length = max_stream_length
        self._redis: redis.Redis | None = None

        # Stream key
        self.stream_key = f"{service_name}:audit:stream"

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Audit logger connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def log(
        self,
        event_type: AuditEventType,
        action: str,
        *,
        actor_type: Literal["user", "agent", "system"] = "system",
        actor_id: str | None = None,
        actor_ip: str | None = None,
        session_id: str | None = None,
        conversation_id: str | None = None,
        agent_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
        confidentiality_level: ConfidentialityLevel = "INTERNAL",
    ) -> str:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            action: Human-readable action description
            actor_type: Type of actor (user, agent, system)
            actor_id: ID of the actor
            actor_ip: IP address if applicable
            session_id: Session identifier
            conversation_id: Related conversation
            agent_id: Related agent
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional event details
            success: Whether the action succeeded
            error_message: Error message if failed
            confidentiality_level: Classification level

        Returns:
            Event ID
        """
        await self.connect()

        event = AuditEvent(
            event_type=event_type,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_ip=actor_ip,
            session_id=session_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            success=success,
            error_message=error_message,
            confidentiality_level=confidentiality_level,
            sanitized=True,  # All logged events should be sanitized
        )

        # Sanitize details before logging
        from .manager import get_security_manager
        security = get_security_manager()
        event.details = security.sanitize_dict_for_logging(event.details)

        # Store in Redis stream
        event_data = event.model_dump_json()
        await self._redis.xadd(
            self.stream_key,
            {"data": event_data},
            maxlen=self.max_stream_length,
        )

        # Also log to Python logger for immediate visibility
        log_level = logging.WARNING if not success else logging.INFO
        logger.log(
            log_level,
            f"AUDIT [{event.event_type.value}] {action} "
            f"actor={actor_id} resource={resource_type}:{resource_id} "
            f"success={success}",
        )

        return str(event.id)

    async def log_pii_detection(
        self,
        text_preview: str,
        pii_types: list[str],
        conversation_id: str | None = None,
        agent_id: str | None = None,
    ) -> str:
        """Log PII detection event."""
        return await self.log(
            event_type=AuditEventType.PII_DETECTED,
            action=f"PII detected: {', '.join(pii_types)}",
            conversation_id=conversation_id,
            agent_id=agent_id,
            details={
                "pii_types": pii_types,
                "text_preview": text_preview[:50] + "..." if len(text_preview) > 50 else text_preview,
            },
            confidentiality_level="CONFIDENTIAL",
        )

    async def log_agent_call(
        self,
        agent_id: str,
        action: str,
        conversation_id: str | None = None,
        success: bool = True,
        error_message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Log agent call event."""
        return await self.log(
            event_type=AuditEventType.AGENT_CALLED if success else AuditEventType.AGENT_ERROR,
            action=action,
            agent_id=agent_id,
            conversation_id=conversation_id,
            resource_type="agent",
            resource_id=agent_id,
            success=success,
            error_message=error_message,
            details=details,
        )

    async def log_conversation_event(
        self,
        event_type: AuditEventType,
        conversation_id: str,
        action: str,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Log conversation-related event."""
        return await self.log(
            event_type=event_type,
            action=action,
            actor_type="user" if actor_id else "system",
            actor_id=actor_id,
            conversation_id=conversation_id,
            resource_type="conversation",
            resource_id=conversation_id,
            details=details,
        )

    async def log_security_alert(
        self,
        action: str,
        details: dict[str, Any],
        actor_ip: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Log security alert."""
        return await self.log(
            event_type=AuditEventType.SECURITY_ALERT,
            action=action,
            actor_ip=actor_ip,
            session_id=session_id,
            details=details,
            success=False,
            confidentiality_level="SECRET",
        )

    async def get_events(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        event_types: list[AuditEventType] | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """
        Retrieve audit events from Redis stream.

        Args:
            start_time: Filter events after this time
            end_time: Filter events before this time
            event_types: Filter by event types
            limit: Maximum number of events to return

        Returns:
            List of matching audit events
        """
        await self.connect()

        # Convert times to Redis stream IDs (millisecond timestamps)
        start_id = "-"
        end_id = "+"
        if start_time:
            start_id = f"{int(start_time.timestamp() * 1000)}-0"
        if end_time:
            end_id = f"{int(end_time.timestamp() * 1000)}-0"

        # Read from stream
        entries = await self._redis.xrange(
            self.stream_key,
            min=start_id,
            max=end_id,
            count=limit * 2,  # Fetch extra to account for filtering
        )

        events = []
        for entry_id, data in entries:
            try:
                event = AuditEvent.model_validate_json(data["data"])

                # Filter by event type if specified
                if event_types and event.event_type not in event_types:
                    continue

                events.append(event)

                if len(events) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Failed to parse audit event {entry_id}: {e}")

        return events


# Singleton instance
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get or create the singleton AuditLogger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
