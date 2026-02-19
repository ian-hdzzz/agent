"""
Async PostgreSQL CRUD for PACO persistent memory.

Every method takes scope_id and all queries include WHERE scope_id = $N.
Redis caching for frequently accessed data.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import asyncpg
import redis.asyncio as aioredis

from .models import (
    Memory, InteractionSummary, CitizenProfile,
    SystemNote, MemoryBundle, ConversationSnapshot,
)

logger = logging.getLogger(__name__)

REDIS_CACHE_TTL = 300  # 5 minutes
REDIS_PREFIX = "gobierno:memory"


class MemoryStore:
    """Async PostgreSQL CRUD with Redis caching. All operations are scope-filtered."""

    def __init__(self, pool: asyncpg.Pool, redis_client: aioredis.Redis):
        self._pool = pool
        self._redis = redis_client

    # =========================================================================
    # Memory CRUD
    # =========================================================================

    async def store_memory(
        self,
        scope_id: str,
        contact_id: str,
        memory_type: str,
        content: str,
        importance: float = 0.5,
        tags: list[str] | None = None,
        source_conversation_id: str | None = None,
        expires_at: datetime | None = None,
    ) -> UUID:
        """Store a scoped memory. Returns the new memory ID."""
        row = await self._pool.fetchrow(
            """
            INSERT INTO memories (scope_id, citizen_contact_id, memory_type, content,
                                  importance, tags, source_conversation_id, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            scope_id, contact_id, memory_type, content,
            importance, tags or [], source_conversation_id, expires_at,
        )
        await self._invalidate_cache(scope_id, contact_id)
        return row["id"]

    async def recall(
        self,
        scope_id: str,
        contact_id: str,
        max_memories: int = 5,
        include_summaries: bool = True,
    ) -> MemoryBundle:
        """Recall memories and summaries for a scope + citizen."""
        cache_key = f"{REDIS_PREFIX}:{scope_id}:{contact_id}"

        # Try cache
        cached = await self._redis_get(cache_key)
        if cached:
            return MemoryBundle(**cached)

        # Fetch memories ordered by importance
        mem_rows = await self._pool.fetch(
            """
            SELECT * FROM memories
            WHERE scope_id = $1 AND citizen_contact_id = $2
              AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY importance DESC, created_at DESC
            LIMIT $3
            """,
            scope_id, contact_id, max_memories,
        )
        memories = [Memory(**dict(r)) for r in mem_rows]

        # Update access counts
        if mem_rows:
            ids = [r["id"] for r in mem_rows]
            await self._pool.execute(
                """
                UPDATE memories SET access_count = access_count + 1,
                                    last_accessed_at = CURRENT_TIMESTAMP
                WHERE id = ANY($1)
                """,
                ids,
            )

        # Fetch recent summaries
        summaries = []
        if include_summaries:
            sum_rows = await self._pool.fetch(
                """
                SELECT * FROM interaction_summaries
                WHERE scope_id = $1 AND citizen_contact_id = $2
                  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ORDER BY created_at DESC
                LIMIT 3
                """,
                scope_id, contact_id,
            )
            summaries = [InteractionSummary(**dict(r)) for r in sum_rows]

        bundle = MemoryBundle(memories=memories, summaries=summaries)

        # Cache
        await self._redis_set(cache_key, bundle.model_dump(mode="json"))

        return bundle

    async def forget_citizen_scope(self, scope_id: str, contact_id: str) -> int:
        """Delete all memories for one scope + citizen. Returns count deleted."""
        result = await self._pool.execute(
            "DELETE FROM memories WHERE scope_id = $1 AND citizen_contact_id = $2",
            scope_id, contact_id,
        )
        await self._pool.execute(
            "DELETE FROM interaction_summaries WHERE scope_id = $1 AND citizen_contact_id = $2",
            scope_id, contact_id,
        )
        await self._invalidate_cache(scope_id, contact_id)
        count = int(result.split()[-1]) if result else 0
        return count

    async def forget_citizen_all(self, contact_id: str) -> int:
        """CASCADE delete across ALL scopes. Returns total memories deleted."""
        result = await self._pool.execute(
            "DELETE FROM memories WHERE citizen_contact_id = $1", contact_id
        )
        await self._pool.execute(
            "DELETE FROM interaction_summaries WHERE citizen_contact_id = $1", contact_id
        )
        await self._pool.execute(
            "DELETE FROM citizen_profiles WHERE contact_id = $1", contact_id
        )
        await self._pool.execute(
            "DELETE FROM system_notes WHERE citizen_contact_id = $1", contact_id
        )
        await self._pool.execute(
            "DELETE FROM conversation_snapshots WHERE contact_id = $1", contact_id
        )

        # Invalidate all possible cache keys for this citizen
        pattern = f"{REDIS_PREFIX}:*:{contact_id}"
        async for key in self._redis.scan_iter(match=pattern):
            await self._redis.delete(key)

        count = int(result.split()[-1]) if result else 0
        return count

    # =========================================================================
    # Interaction Summaries
    # =========================================================================

    async def store_summary(
        self,
        scope_id: str,
        contact_id: str,
        summary: InteractionSummary,
    ) -> UUID:
        """Store a conversation summary."""
        row = await self._pool.fetchrow(
            """
            INSERT INTO interaction_summaries
                (scope_id, citizen_contact_id, conversation_external_id, summary_text,
                 topics, outcome, sentiment, ticket_folios, message_count, metadata, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11)
            RETURNING id
            """,
            scope_id, contact_id, summary.conversation_external_id,
            summary.summary_text, summary.topics, summary.outcome,
            summary.sentiment, summary.ticket_folios, summary.message_count,
            json.dumps(summary.metadata), summary.expires_at,
        )
        await self._invalidate_cache(scope_id, contact_id)
        return row["id"]

    # =========================================================================
    # Citizen Profiles (scope-independent, orchestrator use)
    # =========================================================================

    async def get_citizen_profile(self, contact_id: str) -> Optional[CitizenProfile]:
        """Get citizen profile by contact ID."""
        row = await self._pool.fetchrow(
            "SELECT * FROM citizen_profiles WHERE contact_id = $1", contact_id
        )
        if row:
            return CitizenProfile(**dict(row))
        return None

    async def upsert_citizen_profile(self, contact_id: str, **updates) -> CitizenProfile:
        """Create or update citizen profile fields."""
        existing = await self.get_citizen_profile(contact_id)
        if existing:
            set_clauses = []
            values = [contact_id]
            idx = 2
            for key, value in updates.items():
                set_clauses.append(f"{key} = ${idx}")
                values.append(value)
                idx += 1
            if set_clauses:
                await self._pool.execute(
                    f"UPDATE citizen_profiles SET {', '.join(set_clauses)} WHERE contact_id = $1",
                    *values,
                )
        else:
            columns = ["contact_id"] + list(updates.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = [contact_id] + list(updates.values())
            await self._pool.execute(
                f"INSERT INTO citizen_profiles ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                *values,
            )
        return await self.get_citizen_profile(contact_id)

    # =========================================================================
    # System Notes
    # =========================================================================

    async def get_system_notes(self, contact_id: str, active_only: bool = True) -> list[SystemNote]:
        """Get system notes for a citizen."""
        query = "SELECT * FROM system_notes WHERE citizen_contact_id = $1"
        if active_only:
            query += " AND is_active = true"
        query += " ORDER BY created_at DESC"
        rows = await self._pool.fetch(query, contact_id)
        return [SystemNote(**dict(r)) for r in rows]

    async def add_system_note(
        self,
        contact_id: str,
        note_type: str,
        content: str,
        severity: str = "info",
        created_by: str = "system",
    ) -> UUID:
        """Add an admin note about a citizen."""
        row = await self._pool.fetchrow(
            """
            INSERT INTO system_notes (citizen_contact_id, note_type, content, severity, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            contact_id, note_type, content, severity, created_by,
        )
        return row["id"]

    # =========================================================================
    # Conversation Snapshots
    # =========================================================================

    async def save_snapshot(
        self,
        conversation_id: str,
        contact_id: str,
        messages: list[dict],
        agents_involved: list[str],
        categories_involved: list[str],
    ):
        """Upsert conversation snapshot for batch summarization."""
        await self._pool.execute(
            """
            INSERT INTO conversation_snapshots
                (conversation_external_id, contact_id, message_history,
                 agents_involved, categories_involved)
            VALUES ($1, $2, $3::jsonb, $4, $5)
            ON CONFLICT (id) DO NOTHING
            """,
            conversation_id, contact_id, json.dumps(messages),
            agents_involved, categories_involved,
        )

    async def get_unsummarized_snapshots(self, limit: int = 100) -> list[ConversationSnapshot]:
        """Fetch snapshots awaiting summarization."""
        rows = await self._pool.fetch(
            """
            SELECT * FROM conversation_snapshots
            WHERE summarized = false
            ORDER BY created_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [ConversationSnapshot(**dict(r)) for r in rows]

    async def mark_snapshot_summarized(self, snapshot_id: UUID):
        """Mark a snapshot as summarized."""
        await self._pool.execute(
            "UPDATE conversation_snapshots SET summarized = true WHERE id = $1",
            snapshot_id,
        )

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def cleanup_expired(self, scope_id: str | None = None) -> int:
        """Delete expired memories and summaries."""
        total = 0

        if scope_id:
            result = await self._pool.execute(
                "DELETE FROM memories WHERE scope_id = $1 AND expires_at < CURRENT_TIMESTAMP",
                scope_id,
            )
        else:
            result = await self._pool.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"
            )
        total += int(result.split()[-1]) if result else 0

        if scope_id:
            result = await self._pool.execute(
                "DELETE FROM interaction_summaries WHERE scope_id = $1 AND expires_at < CURRENT_TIMESTAMP",
                scope_id,
            )
        else:
            result = await self._pool.execute(
                "DELETE FROM interaction_summaries WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"
            )
        total += int(result.split()[-1]) if result else 0

        return total

    async def anonymize_stale(self, days: int = 730) -> int:
        """Anonymize citizen profiles not seen in N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self._pool.execute(
            """
            UPDATE citizen_profiles
            SET display_name_encrypted = NULL,
                citizen_id_hash = NULL,
                anonymized_at = CURRENT_TIMESTAMP
            WHERE last_seen_at < $1
              AND anonymized_at IS NULL
            """,
            cutoff,
        )
        return int(result.split()[-1]) if result else 0

    async def enforce_max_per_citizen(self, scope_id: str, contact_id: str, max_count: int = 100):
        """Delete oldest low-importance memories if citizen exceeds max."""
        count = await self._pool.fetchval(
            "SELECT COUNT(*) FROM memories WHERE scope_id = $1 AND citizen_contact_id = $2",
            scope_id, contact_id,
        )
        if count > max_count:
            excess = count - max_count
            await self._pool.execute(
                """
                DELETE FROM memories WHERE id IN (
                    SELECT id FROM memories
                    WHERE scope_id = $1 AND citizen_contact_id = $2
                    ORDER BY importance ASC, created_at ASC
                    LIMIT $3
                )
                """,
                scope_id, contact_id, excess,
            )

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self, scope_id: str | None = None) -> dict:
        """Memory statistics, global or per-scope."""
        if scope_id:
            memories_count = await self._pool.fetchval(
                "SELECT COUNT(*) FROM memories WHERE scope_id = $1", scope_id
            )
            summaries_count = await self._pool.fetchval(
                "SELECT COUNT(*) FROM interaction_summaries WHERE scope_id = $1", scope_id
            )
            citizens_count = await self._pool.fetchval(
                "SELECT COUNT(DISTINCT citizen_contact_id) FROM memories WHERE scope_id = $1",
                scope_id,
            )
            return {
                "scope_id": scope_id,
                "memories": memories_count,
                "summaries": summaries_count,
                "citizens_with_memories": citizens_count,
            }
        else:
            memories_count = await self._pool.fetchval("SELECT COUNT(*) FROM memories")
            summaries_count = await self._pool.fetchval("SELECT COUNT(*) FROM interaction_summaries")
            profiles_count = await self._pool.fetchval("SELECT COUNT(*) FROM citizen_profiles")
            pending_snapshots = await self._pool.fetchval(
                "SELECT COUNT(*) FROM conversation_snapshots WHERE summarized = false"
            )
            scopes = await self._pool.fetch(
                "SELECT scope_id, COUNT(*) as count FROM memories GROUP BY scope_id ORDER BY count DESC"
            )
            return {
                "total_memories": memories_count,
                "total_summaries": summaries_count,
                "total_profiles": profiles_count,
                "pending_snapshots": pending_snapshots,
                "memories_by_scope": {r["scope_id"]: r["count"] for r in scopes},
            }

    # =========================================================================
    # Audit logging
    # =========================================================================

    async def log_audit(
        self,
        contact_id: str | None,
        scope_id: str | None,
        action: str,
        memory_type: str | None = None,
        performed_by: str = "system",
        details: dict | None = None,
    ):
        """Write to memory_audit_log."""
        await self._pool.execute(
            """
            INSERT INTO memory_audit_log
                (citizen_contact_id, scope_id, action, memory_type, performed_by, details)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            contact_id, scope_id, action, memory_type,
            performed_by, json.dumps(details or {}),
        )

    async def get_audit_log(
        self,
        contact_id: str | None = None,
        scope_id: str | None = None,
        action: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Query audit log with optional filters."""
        conditions = []
        values = []
        idx = 1

        if contact_id:
            conditions.append(f"citizen_contact_id = ${idx}")
            values.append(contact_id)
            idx += 1
        if scope_id:
            conditions.append(f"scope_id = ${idx}")
            values.append(scope_id)
            idx += 1
        if action:
            conditions.append(f"action = ${idx}")
            values.append(action)
            idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        values.extend([limit, offset])

        rows = await self._pool.fetch(
            f"""
            SELECT * FROM memory_audit_log
            {where}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *values,
        )
        return [dict(r) for r in rows]

    # =========================================================================
    # Citizens listing (for admin)
    # =========================================================================

    async def list_citizens(
        self,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CitizenProfile], int]:
        """List citizen profiles with optional search. Returns (profiles, total_count)."""
        if search:
            count = await self._pool.fetchval(
                """
                SELECT COUNT(*) FROM citizen_profiles
                WHERE contact_id ILIKE $1 OR $1 = ANY(tags)
                """,
                f"%{search}%",
            )
            rows = await self._pool.fetch(
                """
                SELECT * FROM citizen_profiles
                WHERE contact_id ILIKE $1 OR $1 = ANY(tags)
                ORDER BY last_seen_at DESC
                LIMIT $2 OFFSET $3
                """,
                f"%{search}%", limit, offset,
            )
        else:
            count = await self._pool.fetchval("SELECT COUNT(*) FROM citizen_profiles")
            rows = await self._pool.fetch(
                "SELECT * FROM citizen_profiles ORDER BY last_seen_at DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )

        profiles = [CitizenProfile(**dict(r)) for r in rows]
        return profiles, count

    # =========================================================================
    # Redis cache helpers
    # =========================================================================

    async def _redis_get(self, key: str) -> dict | None:
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            logger.debug(f"Redis cache miss for {key}")
        return None

    async def _redis_set(self, key: str, data: dict):
        try:
            await self._redis.set(key, json.dumps(data, default=str), ex=REDIS_CACHE_TTL)
        except Exception:
            logger.debug(f"Redis cache set failed for {key}")

    async def _invalidate_cache(self, scope_id: str, contact_id: str):
        try:
            await self._redis.delete(f"{REDIS_PREFIX}:{scope_id}:{contact_id}")
        except Exception:
            pass
