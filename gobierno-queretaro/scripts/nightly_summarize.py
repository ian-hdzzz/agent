#!/usr/bin/env python3
"""
PACO Nightly Batch Summarization

Processes unsummarized conversation snapshots and generates per-scope
interaction summaries using Claude.

Crontab example:
    0 1 * * * cd /path/to/gobierno-queretaro && python scripts/nightly_summarize.py >> /var/log/paco-batch.log 2>&1

Safe to re-run — idempotent. Can also be triggered via admin API.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
import redis.asyncio as aioredis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [nightly-batch] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def run_summarization_batch() -> dict:
    """
    Main batch summarization logic.

    Returns dict with counts for API response.
    """
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/gobierno")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=3)
    redis_client = aioredis.from_url(redis_url, decode_responses=True)

    from shared.memory.store import MemoryStore
    from shared.memory.config import ConfigStore
    from shared.memory.summarizer import ConversationSummarizer
    from shared.memory.models import ConversationSnapshot

    store = MemoryStore(pool, redis_client)
    config_store = ConfigStore(pool)
    summarizer = ConversationSummarizer()

    global_config = await config_store.get_global_config()

    # =========================================================================
    # Step 1: Fetch unsummarized snapshots
    # =========================================================================
    snapshots = await store.get_unsummarized_snapshots(limit=200)
    logger.info(f"Found {len(snapshots)} unsummarized snapshots")

    if not snapshots:
        result = {"snapshots_processed": 0, "summaries_created": 0}
        await pool.close()
        await redis_client.close()
        return result

    # =========================================================================
    # Step 2: For each snapshot, generate per-agent summaries
    # =========================================================================
    summaries_created = 0
    snapshots_processed = 0
    errors = 0

    for snapshot in snapshots:
        try:
            if not snapshot.message_history:
                await store.mark_snapshot_summarized(snapshot.id)
                snapshots_processed += 1
                continue

            for scope_id in snapshot.agents_involved:
                # Check per-scope config
                scope_config = await config_store.get_effective_config(scope_id)
                if not scope_config.enabled or not scope_config.summarization.enabled:
                    logger.info(f"Skipping summarization for disabled scope: {scope_id}")
                    continue

                summary = summarizer.summarize(
                    messages=snapshot.message_history,
                    scope_id=scope_id,
                    config=scope_config,
                    pii_allowed=scope_config.privacy.pii_in_summaries,
                )

                if summary:
                    summary.citizen_contact_id = snapshot.contact_id
                    summary.conversation_external_id = snapshot.conversation_external_id

                    # Set expiration based on retention config
                    if scope_config.retention.summary_days:
                        summary.expires_at = datetime.now(timezone.utc) + timedelta(
                            days=scope_config.retention.summary_days
                        )

                    await store.store_summary(scope_id, snapshot.contact_id, summary)
                    summaries_created += 1
                    logger.info(
                        f"Created summary for scope={scope_id} citizen={snapshot.contact_id}"
                    )

            # =========================================================================
            # Step 3: Update citizen profile
            # =========================================================================
            profile = await store.get_citizen_profile(snapshot.contact_id)
            if profile:
                new_total = profile.total_conversations + 1
                categories = list(set(profile.frequent_categories + snapshot.categories_involved))
                await store.upsert_citizen_profile(
                    snapshot.contact_id,
                    total_conversations=new_total,
                    last_seen_at=datetime.now(timezone.utc),
                    frequent_categories=categories[:20],  # Cap at 20
                )
            else:
                await store.upsert_citizen_profile(
                    snapshot.contact_id,
                    total_conversations=1,
                    frequent_categories=snapshot.categories_involved,
                    last_seen_at=datetime.now(timezone.utc),
                )

            # Mark snapshot as summarized
            await store.mark_snapshot_summarized(snapshot.id)
            snapshots_processed += 1

        except Exception as e:
            logger.error(f"Error processing snapshot {snapshot.id}: {e}")
            errors += 1

    # =========================================================================
    # Step 4: Cleanup expired records
    # =========================================================================
    expired_deleted = await store.cleanup_expired()
    logger.info(f"Cleaned up {expired_deleted} expired records")

    # =========================================================================
    # Step 5: Anonymize stale profiles
    # =========================================================================
    anonymize_days = global_config.privacy.auto_anonymize_days
    anonymized = await store.anonymize_stale(days=anonymize_days)
    if anonymized > 0:
        logger.info(f"Anonymized {anonymized} stale profiles (>{anonymize_days} days)")

    result = {
        "snapshots_processed": snapshots_processed,
        "summaries_created": summaries_created,
        "expired_deleted": expired_deleted,
        "anonymized": anonymized,
        "errors": errors,
    }

    logger.info(f"Batch complete: {result}")

    await pool.close()
    await redis_client.close()
    return result


async def main():
    logger.info("=" * 60)
    logger.info("PACO Nightly Summarization Batch - Starting")
    logger.info(f"Time: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    result = await run_summarization_batch()

    logger.info("=" * 60)
    logger.info(f"Batch finished: {result}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
