"""
Memory configuration with database-backed storage and caching.
"""

import json
import time
import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60


class SummarizationConfig(BaseModel):
    enabled: bool = True
    model: str = "claude-sonnet-4-5-20250929"
    max_summary_tokens: int = 300
    batch_hour: int = 1


class RetentionConfig(BaseModel):
    profile_days: int = 365
    summary_days: int = 90
    memory_days: int = 180
    max_per_citizen: int = 100


class InjectionConfig(BaseModel):
    enabled: bool = True
    max_in_prompt: int = 5
    include_summaries: bool = True
    include_memories: bool = True


class PrivacyConfig(BaseModel):
    allow_deletion: bool = True
    auto_anonymize_days: int = 730
    pii_in_summaries: bool = False


class MemoryConfig(BaseModel):
    """Full memory configuration, resolved from global + per-scope overrides."""
    enabled: bool = True
    summarization: SummarizationConfig = Field(default_factory=SummarizationConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    injection: InjectionConfig = Field(default_factory=InjectionConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    per_scope_overrides: dict = Field(default_factory=dict)


class ConfigStore:
    """Loads/saves memory config from the memory_config table with caching."""

    def __init__(self, pool):
        self._pool = pool
        self._cache: dict[str, tuple[float, dict]] = {}

    async def get_global_config(self) -> MemoryConfig:
        """Load the global memory config."""
        raw = await self._load("global")
        if raw:
            return MemoryConfig(**raw)
        return MemoryConfig()

    async def get_effective_config(self, scope_id: str) -> MemoryConfig:
        """Get config for a scope: global merged with per-scope overrides."""
        global_raw = await self._load("global") or {}
        scope_raw = await self._load(scope_id)

        config = MemoryConfig(**global_raw)

        # Apply per-scope overrides
        if scope_raw:
            if "enabled" in scope_raw:
                config.enabled = scope_raw["enabled"]
            if "injection" in scope_raw:
                for k, v in scope_raw["injection"].items():
                    setattr(config.injection, k, v)
            if "retention" in scope_raw:
                for k, v in scope_raw["retention"].items():
                    setattr(config.retention, k, v)
            if "summarization" in scope_raw:
                for k, v in scope_raw["summarization"].items():
                    setattr(config.summarization, k, v)
            if "privacy" in scope_raw:
                for k, v in scope_raw["privacy"].items():
                    setattr(config.privacy, k, v)

        return config

    async def save_config(self, config_id: str, config: dict, updated_by: str = "system"):
        """Save config to the database."""
        await self._pool.execute(
            """
            INSERT INTO memory_config (id, config, updated_by, updated_at)
            VALUES ($1, $2::jsonb, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                config = $2::jsonb,
                updated_by = $3,
                updated_at = CURRENT_TIMESTAMP
            """,
            config_id, json.dumps(config), updated_by
        )
        # Invalidate cache
        self._cache.pop(config_id, None)

    async def _load(self, config_id: str) -> Optional[dict]:
        """Load config from DB with 60-second cache."""
        now = time.time()
        if config_id in self._cache:
            cached_at, data = self._cache[config_id]
            if now - cached_at < CACHE_TTL_SECONDS:
                return data

        row = await self._pool.fetchrow(
            "SELECT config FROM memory_config WHERE id = $1",
            config_id
        )
        data = json.loads(row["config"]) if row else None
        self._cache[config_id] = (now, data)
        return data
