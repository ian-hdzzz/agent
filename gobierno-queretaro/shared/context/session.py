"""
Gobierno Queretaro - Session Context Management
Secure session storage with per-agent data isolation
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

import redis.asyncio as redis

logger = logging.getLogger(__name__)


ConfidentialityLevel = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]


@dataclass
class SessionContext:
    """
    Session context with secure data compartmentalization.

    Features:
    - Per-agent isolated data vault
    - Shared cross-agent data
    - Confidentiality level tracking
    - Pseudonymized citizen identification
    """

    session_id: str = field(default_factory=lambda: str(uuid4()))

    # Data compartments
    data_vault: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Per-agent isolated data. Key: agent_id, Value: agent-specific data"""

    shared_data: dict[str, Any] = field(default_factory=dict)
    """Cross-agent accessible data (non-sensitive)"""

    # Security classification
    confidentiality_level: ConfidentialityLevel = "INTERNAL"
    """Highest sensitivity level of data in this session"""

    # Citizen identification (pseudonymized)
    citizen_id_hash: str | None = None
    """SHA-256 hash of citizen CURP/RFC for linking without storing actual ID"""

    # Conversation tracking
    conversation_id: str | None = None
    contact_id: str | None = None
    current_agent_id: str | None = None

    # Agent routing history
    agent_history: list[str] = field(default_factory=list)
    """List of agent IDs that have handled this session"""

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_activity_at: datetime = field(default_factory=datetime.utcnow)

    # TTL
    ttl_seconds: int = 3600  # 1 hour default

    def get_agent_data(self, agent_id: str) -> dict[str, Any]:
        """
        Get isolated data vault for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent's isolated data dictionary
        """
        if agent_id not in self.data_vault:
            self.data_vault[agent_id] = {}
        return self.data_vault[agent_id]

    def set_agent_data(self, agent_id: str, key: str, value: Any) -> None:
        """
        Set data in agent's isolated vault.

        Args:
            agent_id: Agent identifier
            key: Data key
            value: Data value
        """
        if agent_id not in self.data_vault:
            self.data_vault[agent_id] = {}
        self.data_vault[agent_id][key] = value
        self.updated_at = datetime.utcnow()
        self.last_activity_at = datetime.utcnow()

    def get_shared(self, key: str, default: Any = None) -> Any:
        """
        Get shared data accessible by all agents.

        Args:
            key: Data key
            default: Default value if key not found

        Returns:
            Shared data value
        """
        return self.shared_data.get(key, default)

    def set_shared(self, key: str, value: Any) -> None:
        """
        Set shared data accessible by all agents.

        Args:
            key: Data key
            value: Data value
        """
        self.shared_data[key] = value
        self.updated_at = datetime.utcnow()
        self.last_activity_at = datetime.utcnow()

    def elevate_confidentiality(self, level: ConfidentialityLevel) -> None:
        """
        Elevate session confidentiality level.

        Confidentiality can only be elevated, never lowered.

        Args:
            level: New confidentiality level
        """
        levels = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
        current_idx = levels.index(self.confidentiality_level)
        new_idx = levels.index(level)

        if new_idx > current_idx:
            self.confidentiality_level = level
            self.updated_at = datetime.utcnow()
            logger.info(
                f"Session {self.session_id} elevated to {level}"
            )

    def record_agent_visit(self, agent_id: str) -> None:
        """
        Record that an agent handled this session.

        Args:
            agent_id: Agent identifier
        """
        self.current_agent_id = agent_id
        if agent_id not in self.agent_history:
            self.agent_history.append(agent_id)
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        data["last_activity_at"] = self.last_activity_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionContext":
        """Create SessionContext from dictionary."""
        # Convert ISO strings back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if isinstance(data.get("last_activity_at"), str):
            data["last_activity_at"] = datetime.fromisoformat(data["last_activity_at"])
        return cls(**data)

    def get_context_for_agent(self, agent_id: str) -> dict[str, Any]:
        """
        Get context bundle for a specific agent.

        Combines agent-specific data with appropriate shared data.

        Args:
            agent_id: Agent identifier

        Returns:
            Context dictionary for the agent
        """
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "contact_id": self.contact_id,
            "agent_data": self.get_agent_data(agent_id),
            "shared_data": self.shared_data,
            "confidentiality_level": self.confidentiality_level,
            "previous_agents": self.agent_history,
            "citizen_id_hash": self.citizen_id_hash,
        }


class SessionStore:
    """
    Redis-backed session storage with TTL support.

    Features:
    - Automatic session expiration
    - Atomic operations
    - Session recovery
    """

    def __init__(self, redis_url: str | None = None, key_prefix: str = "gobierno:session"):
        """
        Initialize SessionStore.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for session keys
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.key_prefix = key_prefix
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            logger.info("SessionStore connected to Redis")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}:{session_id}"

    def _conversation_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation-to-session mapping."""
        return f"{self.key_prefix}:conv:{conversation_id}"

    async def create(
        self,
        conversation_id: str | None = None,
        contact_id: str | None = None,
        citizen_id_hash: str | None = None,
        ttl_seconds: int = 3600,
    ) -> SessionContext:
        """
        Create a new session.

        Args:
            conversation_id: External conversation ID
            contact_id: External contact ID
            citizen_id_hash: Pseudonymized citizen ID
            ttl_seconds: Session TTL in seconds

        Returns:
            New SessionContext
        """
        await self.connect()

        session = SessionContext(
            conversation_id=conversation_id,
            contact_id=contact_id,
            citizen_id_hash=citizen_id_hash,
            ttl_seconds=ttl_seconds,
        )

        # Store session
        session_key = self._session_key(session.session_id)
        await self._redis.setex(
            session_key,
            ttl_seconds,
            json.dumps(session.to_dict()),
        )

        # Create conversation mapping if provided
        if conversation_id:
            conv_key = self._conversation_key(conversation_id)
            await self._redis.setex(conv_key, ttl_seconds, session.session_id)

        logger.info(f"Created session {session.session_id}")
        return session

    async def get(self, session_id: str) -> SessionContext | None:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionContext or None if not found
        """
        await self.connect()

        session_key = self._session_key(session_id)
        data = await self._redis.get(session_key)

        if not data:
            return None

        try:
            return SessionContext.from_dict(json.loads(data))
        except Exception as e:
            logger.error(f"Failed to deserialize session {session_id}: {e}")
            return None

    async def get_by_conversation(self, conversation_id: str) -> SessionContext | None:
        """
        Get session by conversation ID.

        Args:
            conversation_id: External conversation ID

        Returns:
            SessionContext or None if not found
        """
        await self.connect()

        conv_key = self._conversation_key(conversation_id)
        session_id = await self._redis.get(conv_key)

        if not session_id:
            return None

        return await self.get(session_id)

    async def get_or_create(
        self,
        conversation_id: str,
        contact_id: str | None = None,
        citizen_id_hash: str | None = None,
        ttl_seconds: int = 3600,
    ) -> SessionContext:
        """
        Get existing session or create new one.

        Args:
            conversation_id: External conversation ID
            contact_id: External contact ID
            citizen_id_hash: Pseudonymized citizen ID
            ttl_seconds: Session TTL in seconds

        Returns:
            Existing or new SessionContext
        """
        session = await self.get_by_conversation(conversation_id)

        if session:
            # Refresh TTL
            await self.refresh(session.session_id)
            return session

        return await self.create(
            conversation_id=conversation_id,
            contact_id=contact_id,
            citizen_id_hash=citizen_id_hash,
            ttl_seconds=ttl_seconds,
        )

    async def update(self, session: SessionContext) -> None:
        """
        Update session in storage.

        Args:
            session: SessionContext to update
        """
        await self.connect()

        session.updated_at = datetime.utcnow()

        session_key = self._session_key(session.session_id)
        ttl = await self._redis.ttl(session_key)

        # Preserve existing TTL or use session's default
        if ttl < 0:
            ttl = session.ttl_seconds

        await self._redis.setex(
            session_key,
            ttl,
            json.dumps(session.to_dict()),
        )

    async def refresh(self, session_id: str, ttl_seconds: int | None = None) -> bool:
        """
        Refresh session TTL.

        Args:
            session_id: Session identifier
            ttl_seconds: New TTL (uses original if None)

        Returns:
            True if session exists and was refreshed
        """
        await self.connect()

        session_key = self._session_key(session_id)
        session = await self.get(session_id)

        if not session:
            return False

        ttl = ttl_seconds or session.ttl_seconds
        await self._redis.expire(session_key, ttl)

        # Also refresh conversation mapping
        if session.conversation_id:
            conv_key = self._conversation_key(session.conversation_id)
            await self._redis.expire(conv_key, ttl)

        return True

    async def delete(self, session_id: str) -> bool:
        """
        Delete session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        await self.connect()

        session = await self.get(session_id)
        session_key = self._session_key(session_id)

        deleted = await self._redis.delete(session_key)

        # Also delete conversation mapping
        if session and session.conversation_id:
            conv_key = self._conversation_key(session.conversation_id)
            await self._redis.delete(conv_key)

        if deleted:
            logger.info(f"Deleted session {session_id}")

        return deleted > 0

    async def set_agent_data(
        self,
        session_id: str,
        agent_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """
        Set agent-specific data in session.

        Args:
            session_id: Session identifier
            agent_id: Agent identifier
            key: Data key
            value: Data value

        Returns:
            True if successful
        """
        session = await self.get(session_id)
        if not session:
            return False

        session.set_agent_data(agent_id, key, value)
        await self.update(session)
        return True

    async def set_shared_data(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """
        Set shared data in session.

        Args:
            session_id: Session identifier
            key: Data key
            value: Data value

        Returns:
            True if successful
        """
        session = await self.get(session_id)
        if not session:
            return False

        session.set_shared(key, value)
        await self.update(session)
        return True


# Singleton instance
_session_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    """Get or create the singleton SessionStore instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
