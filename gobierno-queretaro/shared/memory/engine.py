"""
PacoMemory — the main class each PACO component instantiates.

Each component (agent or orchestrator) creates its own instance with a unique
scope_id. All operations are scoped — an agent cannot access another agent's data.

Usage in an agent:
    memory = get_paco_memory(scope_id="water-cea")
    await memory.connect()
    bundle = await memory.recall(contact_id="user-123")

Usage in orchestrator:
    memory = get_paco_memory(scope_id="orchestrator")
    await memory.connect()
    profile = await memory.recall_citizen_profile(contact_id="user-123")
"""

import os
import logging
from typing import Optional

import asyncpg
import redis.asyncio as aioredis

from .config import MemoryConfig, ConfigStore
from .models import MemoryBundle, CitizenProfile, InteractionSummary
from .store import MemoryStore
from .formatter import MemoryFormatter

logger = logging.getLogger(__name__)


class PacoMemory:
    """
    PACO framework persistent memory engine.

    Each component creates its own instance with a unique scope_id.
    All operations are automatically scoped.
    """

    def __init__(self, scope_id: str, database_url: str, redis_url: str):
        self.scope_id = scope_id
        self._database_url = database_url
        self._redis_url = redis_url
        self._pool: Optional[asyncpg.Pool] = None
        self._redis: Optional[aioredis.Redis] = None
        self._store: Optional[MemoryStore] = None
        self._config_store: Optional[ConfigStore] = None
        self._connected = False

    async def connect(self):
        """Initialize database and Redis connections."""
        if self._connected:
            return

        try:
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=5,
            )
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
            )
            self._store = MemoryStore(self._pool, self._redis)
            self._config_store = ConfigStore(self._pool)
            self._connected = True
            logger.info(f"PacoMemory connected for scope '{self.scope_id}'")
        except Exception as e:
            logger.error(f"PacoMemory connection failed for scope '{self.scope_id}': {e}")
            raise

    async def disconnect(self):
        """Close connections."""
        if self._pool:
            await self._pool.close()
        if self._redis:
            await self._redis.close()
        self._connected = False
        logger.info(f"PacoMemory disconnected for scope '{self.scope_id}'")

    async def get_config(self) -> MemoryConfig:
        """Get effective config (global merged with per-scope overrides)."""
        if not self._config_store:
            return MemoryConfig()
        return await self._config_store.get_effective_config(self.scope_id)

    # =========================================================================
    # Scoped operations (agents use these)
    # =========================================================================

    async def recall(self, contact_id: str) -> Optional[MemoryBundle]:
        """
        Recall memories for this scope + citizen.
        Returns None if memory is disabled for this scope.
        """
        config = await self.get_config()
        if not config.enabled or not config.injection.enabled:
            return None

        bundle = await self._store.recall(
            scope_id=self.scope_id,
            contact_id=contact_id,
            max_memories=config.injection.max_in_prompt,
            include_summaries=config.injection.include_summaries,
        )

        # Format context string
        scope_type = "orchestrator" if self.scope_id == "orchestrator" else "agent"
        bundle.formatted_context = MemoryFormatter.format(bundle, scope_type=scope_type)

        return bundle

    async def store(
        self,
        contact_id: str,
        memory_type: str,
        content: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
        source_conversation_id: str | None = None,
    ):
        """Store a memory scoped to this component."""
        config = await self.get_config()
        if not config.enabled:
            return

        await self._store.store_memory(
            scope_id=self.scope_id,
            contact_id=contact_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            tags=tags,
            source_conversation_id=source_conversation_id,
        )

        # Enforce max per citizen
        await self._store.enforce_max_per_citizen(
            self.scope_id, contact_id, config.retention.max_per_citizen
        )

        # Audit log
        await self._store.log_audit(
            contact_id=contact_id,
            scope_id=self.scope_id,
            action="created",
            memory_type=memory_type,
            performed_by=f"agent:{self.scope_id}",
            details={"importance": importance, "tags": tags or []},
        )

    async def store_summary(self, contact_id: str, summary: InteractionSummary):
        """Store a conversation summary for this scope."""
        config = await self.get_config()
        if not config.enabled:
            return

        summary.scope_id = self.scope_id
        summary.citizen_contact_id = contact_id
        await self._store.store_summary(self.scope_id, contact_id, summary)

    async def forget(self, contact_id: str):
        """Delete all memories for this scope + citizen."""
        count = await self._store.forget_citizen_scope(self.scope_id, contact_id)
        await self._store.log_audit(
            contact_id=contact_id,
            scope_id=self.scope_id,
            action="deleted",
            performed_by=f"agent:{self.scope_id}",
            details={"count": count},
        )

    # =========================================================================
    # Orchestrator-only operations
    # =========================================================================

    async def recall_citizen_profile(self, contact_id: str) -> Optional[CitizenProfile]:
        """Get high-level citizen profile (orchestrator use)."""
        return await self._store.get_citizen_profile(contact_id)

    async def update_citizen_profile(self, contact_id: str, **updates) -> CitizenProfile:
        """Update citizen profile fields."""
        return await self._store.upsert_citizen_profile(contact_id, **updates)

    async def snapshot_conversation(
        self,
        contact_id: str,
        conversation_id: str,
        messages: list[dict],
        agents_involved: list[str],
        categories_involved: list[str],
    ):
        """Write conversation to batch queue for nightly summarization."""
        await self._store.save_snapshot(
            conversation_id=conversation_id,
            contact_id=contact_id,
            messages=messages,
            agents_involved=agents_involved,
            categories_involved=categories_involved,
        )

    # =========================================================================
    # Admin operations
    # =========================================================================

    async def forget_citizen_all_scopes(self, contact_id: str, performed_by: str) -> int:
        """GDPR: delete citizen from ALL scopes. Audit logged."""
        count = await self._store.forget_citizen_all(contact_id)
        await self._store.log_audit(
            contact_id=contact_id,
            scope_id=None,
            action="forgotten",
            performed_by=performed_by,
            details={"total_deleted": count, "all_scopes": True},
        )
        return count

    async def get_stats(self, scope_id: str | None = None) -> dict:
        """Memory statistics (global or per-scope)."""
        return await self._store.get_stats(scope_id)

    # =========================================================================
    # Expose store for admin API use
    # =========================================================================

    @property
    def store_instance(self) -> MemoryStore:
        """Direct access to MemoryStore for admin operations."""
        return self._store

    @property
    def config_store_instance(self) -> ConfigStore:
        """Direct access to ConfigStore for admin operations."""
        return self._config_store


# =============================================================================
# Singleton factory
# =============================================================================

_instances: dict[str, PacoMemory] = {}


def get_paco_memory(scope_id: str) -> PacoMemory:
    """Get or create PacoMemory instance for a scope."""
    if scope_id not in _instances:
        db_url = os.getenv("DATABASE_URL", "postgresql://gobierno:gobierno@postgres:5432/gobierno")
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _instances[scope_id] = PacoMemory(scope_id, db_url, redis_url)
    return _instances[scope_id]
