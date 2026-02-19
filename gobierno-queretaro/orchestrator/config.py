"""
Gobierno Querétaro - Orchestrator Configuration
Environment-based configuration with dynamic agent registry
"""

import asyncio
import logging
import os
import time
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class OrchestratorSettings(BaseSettings):
    """Orchestrator configuration settings"""

    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/gobierno"
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM settings for classification
    model: str = "claude-sonnet-4-5-20250929"
    classification_temperature: float = 0.1

    # Agent endpoints (fallback when DB unavailable)
    agent_water_url: str = os.getenv("AGENT_WATER_URL", "http://localhost:8001")
    agent_transport_url: str = os.getenv("AGENT_TRANSPORT_URL", "http://localhost:8002")
    agent_education_url: str = os.getenv("AGENT_EDUCATION_URL", "http://localhost:8003")
    agent_vehicles_url: str = os.getenv("AGENT_VEHICLES_URL", "http://localhost:8004")
    agent_psychology_url: str = os.getenv("AGENT_PSYCHOLOGY_URL", "http://localhost:8005")
    agent_women_url: str = os.getenv("AGENT_WOMEN_URL", "http://localhost:8006")
    agent_culture_url: str = os.getenv("AGENT_CULTURE_URL", "http://localhost:8007")
    agent_registry_url: str = os.getenv("AGENT_REGISTRY_URL", "http://localhost:8008")
    agent_labor_url: str = os.getenv("AGENT_LABOR_URL", "http://localhost:8009")
    agent_housing_url: str = os.getenv("AGENT_HOUSING_URL", "http://localhost:8010")
    agent_appqro_url: str = os.getenv("AGENT_APPQRO_URL", "http://localhost:8011")
    agent_social_url: str = os.getenv("AGENT_SOCIAL_URL", "http://localhost:8012")
    agent_citizen_url: str = os.getenv("AGENT_CITIZEN_URL", "http://localhost:8013")

    # Request timeout
    agent_timeout: float = 30.0

    # Registry cache TTL in seconds
    registry_cache_ttl: int = 30

    # Health sweep interval in seconds
    health_sweep_interval: int = 60

    # Paco JWT auth (shared secret for validating Paco-issued tokens)
    paco_jwt_secret: str | None = os.getenv("PACO_JWT_SECRET", None)

    # Rate limiting
    rate_limit_route: str = os.getenv("RATE_LIMIT_ROUTE", "60/minute")
    rate_limit_classify: str = os.getenv("RATE_LIMIT_CLASSIFY", "120/minute")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> OrchestratorSettings:
    """Get cached settings instance"""
    return OrchestratorSettings()


# ============================================
# Dynamic Agent Registry
# ============================================

class AgentRegistry:
    """
    Dynamic agent registry backed by PostgreSQL.

    Features:
    - DB-backed agent discovery with cache
    - Automatic fallback to static config if DB unavailable
    - Agent registration/deregistration
    - Health sweep to mark unreachable agents inactive
    - Dynamic classifier data built from registry (keywords, prompts, etc.)
    """

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] | None = None
        self._cache_time: float = 0
        self._db_available: bool = False
        self._classifier_data: Any | None = None  # DynamicClassifierData (lazy import)
        self._classifier_data_time: float = 0

    def _get_static_registry(self) -> dict[str, dict[str, Any]]:
        """Static fallback registry from env vars."""
        settings = get_settings()
        return {
            "CEA": {
                "id": "water-cea",
                "name": "Agente de Agua - CEA",
                "url": settings.agent_water_url,
                "description": "Agua, fugas, consumos, reconexión",
            },
            "TRA": {
                "id": "transport-ameq",
                "name": "Agente de Transporte - AMEQ",
                "url": settings.agent_transport_url,
                "description": "Rutas, horarios, autobús",
            },
            "EDU": {
                "id": "education-usebeq",
                "name": "Agente de Educación - USEBEQ",
                "url": settings.agent_education_url,
                "description": "Escuelas, inscripciones, becas",
            },
            "VEH": {
                "id": "vehicles",
                "name": "Agente de Trámites Vehiculares",
                "url": settings.agent_vehicles_url,
                "description": "Placas, multas, licencias",
            },
            "PSI": {
                "id": "psychology-sejuve",
                "name": "Agente de Psicología - SEJUVE",
                "url": settings.agent_psychology_url,
                "description": "Citas, salud mental",
            },
            "IQM": {
                "id": "women-iqm",
                "name": "Agente de Atención a Mujeres - IQM",
                "url": settings.agent_women_url,
                "description": "Apoyo, violencia de género",
            },
            "CUL": {
                "id": "culture",
                "name": "Agente de Cultura",
                "url": settings.agent_culture_url,
                "description": "Eventos, talleres, becas",
            },
            "RPP": {
                "id": "registry-rpp",
                "name": "Agente de Registro Público - RPP",
                "url": settings.agent_registry_url,
                "description": "Documentos, certificados",
            },
            "LAB": {
                "id": "labor-cclq",
                "name": "Agente de Conciliación Laboral - CCLQ",
                "url": settings.agent_labor_url,
                "description": "Trabajo, demandas",
            },
            "VIV": {
                "id": "housing-iveq",
                "name": "Agente de Vivienda - IVEQ",
                "url": settings.agent_housing_url,
                "description": "Créditos, vivienda",
            },
            "APP": {
                "id": "appqro",
                "name": "Agente de Soporte APPQRO",
                "url": settings.agent_appqro_url,
                "description": "Soporte de la app",
            },
            "SOC": {
                "id": "social-sedesoq",
                "name": "Agente de Programas Sociales - SEDESOQ",
                "url": settings.agent_social_url,
                "description": "Beneficios, ayudas",
            },
            "ATC": {
                "id": "citizen-attention",
                "name": "Agente de Atención Ciudadana",
                "url": settings.agent_citizen_url,
                "description": "Quejas, sugerencias, PQRS",
            },
        }

    async def _load_from_db(self) -> dict[str, dict[str, Any]] | None:
        """Load agent registry from PostgreSQL."""
        settings = get_settings()
        try:
            import asyncpg
            conn = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
            try:
                rows = await conn.fetch(
                    """
                    SELECT id, name, description, endpoint, category_code,
                           version, confidentiality_level, sla_tier, capabilities
                    FROM agents
                    WHERE is_active = true
                    """
                )

                registry = {}
                for row in rows:
                    registry[row["category_code"]] = {
                        "id": row["id"],
                        "name": row["name"],
                        "url": row["endpoint"],
                        "description": row["description"] or "",
                        "version": row["version"] or "1.0.0",
                        "confidentiality_level": row["confidentiality_level"] or "INTERNAL",
                        "sla_tier": row["sla_tier"] or "standard",
                        "capabilities": dict(row["capabilities"]) if row["capabilities"] else {},
                    }

                self._db_available = True
                return registry
            finally:
                await conn.close()

        except Exception as e:
            logger.warning(f"Failed to load registry from DB, using static fallback: {e}")
            self._db_available = False
            return None

    def get_registry(self) -> dict[str, dict[str, Any]]:
        """
        Get agent registry with caching.

        Returns cached DB data if fresh, otherwise falls back to static config.
        Triggers async refresh if cache is stale.
        """
        settings = get_settings()
        now = time.time()

        # Return cache if fresh
        if self._cache and (now - self._cache_time) < settings.registry_cache_ttl:
            return self._cache

        # Try async refresh in background (non-blocking for sync callers)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._refresh_cache())
        except RuntimeError:
            pass

        # Return stale cache or static fallback
        if self._cache:
            return self._cache
        return self._get_static_registry()

    async def _refresh_cache(self) -> None:
        """Refresh registry cache from DB."""
        db_registry = await self._load_from_db()
        if db_registry:
            self._cache = db_registry
            self._cache_time = time.time()
            logger.debug(f"Registry cache refreshed: {len(db_registry)} agents")

    async def refresh(self) -> dict[str, dict[str, Any]]:
        """Force refresh registry cache (async)."""
        await self._refresh_cache()
        return self.get_registry()

    def get_classifier_data(self) -> Any | None:
        """
        Build DynamicClassifierData from registry, cached alongside registry cache.

        Returns None if the registry has no agents with classification metadata
        (keywords/hints), signaling the caller to use static fallback.
        """
        settings = get_settings()
        now = time.time()

        # Return cached classifier data if fresh
        if (
            self._classifier_data is not None
            and (now - self._classifier_data_time) < settings.registry_cache_ttl
        ):
            return self._classifier_data

        # Need a registry to build from
        registry = self.get_registry()
        if not registry:
            return None

        # Check if any agent has classification metadata
        has_metadata = any(
            agent.get("capabilities", {}).get("keywords")
            or agent.get("capabilities", {}).get("classification_hint")
            for agent in registry.values()
        )
        if not has_metadata:
            return None

        # Build dynamic data (lazy import to avoid circular dependency)
        from .classifier import DynamicClassifierData

        self._classifier_data = DynamicClassifierData.build_from_registry(registry)
        self._classifier_data_time = now
        logger.debug(
            f"Classifier data rebuilt: {len(self._classifier_data.valid_categories)} categories"
        )
        return self._classifier_data

    async def register_agent(self, agent_data: dict[str, Any]) -> bool:
        """
        Register or update an agent in the DB.

        Args:
            agent_data: Agent registration payload

        Returns:
            True if registration succeeded
        """
        settings = get_settings()
        try:
            import asyncpg
            conn = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
            try:
                import json
                await conn.execute(
                    """
                    INSERT INTO agents (
                        id, name, description, category_code, endpoint,
                        version, confidentiality_level, sla_tier, capabilities,
                        is_active, last_heartbeat, registered_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, true, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        endpoint = EXCLUDED.endpoint,
                        version = EXCLUDED.version,
                        confidentiality_level = EXCLUDED.confidentiality_level,
                        sla_tier = EXCLUDED.sla_tier,
                        capabilities = EXCLUDED.capabilities,
                        is_active = true,
                        last_heartbeat = NOW(),
                        updated_at = NOW()
                    """,
                    agent_data["agent_id"],
                    agent_data["name"],
                    agent_data.get("description", ""),
                    agent_data["category_code"],
                    agent_data["endpoint"],
                    agent_data.get("version", "1.0.0"),
                    agent_data.get("confidentiality_level", "INTERNAL"),
                    agent_data.get("sla_tier", "standard"),
                    json.dumps(agent_data.get("capabilities", {})),
                )

                # Invalidate caches to pick up changes
                self._cache = None
                self._cache_time = 0
                self._classifier_data = None
                self._classifier_data_time = 0

                logger.info(f"Agent registered: {agent_data['agent_id']} ({agent_data['category_code']})")
                return True
            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"Failed to register agent {agent_data.get('agent_id')}: {e}")
            return False

    async def heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat timestamp."""
        settings = get_settings()
        try:
            import asyncpg
            conn = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
            try:
                await conn.execute(
                    "UPDATE agents SET last_heartbeat = NOW(), is_active = true WHERE id = $1",
                    agent_id,
                )
                return True
            finally:
                await conn.close()
        except Exception as e:
            logger.warning(f"Heartbeat failed for {agent_id}: {e}")
            return False

    async def health_sweep(self, stale_threshold_seconds: int = 180) -> list[str]:
        """
        Mark agents with no recent heartbeat as inactive.

        Args:
            stale_threshold_seconds: Seconds since last heartbeat to consider stale

        Returns:
            List of agent IDs marked inactive
        """
        settings = get_settings()
        try:
            import asyncpg
            conn = await asyncpg.connect(settings.database_url.replace("+asyncpg", ""))
            try:
                rows = await conn.fetch(
                    """
                    UPDATE agents
                    SET is_active = false, updated_at = NOW()
                    WHERE is_active = true
                      AND last_heartbeat IS NOT NULL
                      AND last_heartbeat < NOW() - $1 * INTERVAL '1 second'
                    RETURNING id
                    """,
                    stale_threshold_seconds,
                )
                deactivated = [row["id"] for row in rows]
                if deactivated:
                    logger.warning(f"Health sweep deactivated agents: {deactivated}")
                    self._cache = None  # Invalidate cache
                    self._classifier_data = None
                    self._classifier_data_time = 0
                return deactivated
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Health sweep failed: {e}")
            return []


# Singleton registry
_registry: AgentRegistry | None = None


def _get_registry_instance() -> AgentRegistry:
    """Get or create the singleton AgentRegistry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_agent_registry() -> dict[str, dict[str, Any]]:
    """Get agent registry (backward compatible)."""
    return _get_registry_instance().get_registry()


async def get_agent_registry_async() -> dict[str, dict[str, Any]]:
    """Get agent registry with async DB refresh."""
    registry = _get_registry_instance()
    return await registry.refresh()


async def register_agent(agent_data: dict[str, Any]) -> bool:
    """Register an agent in the dynamic registry."""
    return await _get_registry_instance().register_agent(agent_data)


async def agent_heartbeat(agent_id: str) -> bool:
    """Update agent heartbeat."""
    return await _get_registry_instance().heartbeat(agent_id)


async def run_health_sweep() -> list[str]:
    """Run health sweep to deactivate stale agents."""
    return await _get_registry_instance().health_sweep()
