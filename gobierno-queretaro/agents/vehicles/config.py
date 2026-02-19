"""
Gobierno Queretaro - Vehicles Agent Configuration
"""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class VehiclesAgentSettings(BaseSettings):
    """Vehicles Agent configuration"""

    # Agent identity
    agent_id: str = "vehicles"
    agent_name: str = "Agente de Vehiculos"
    category_code: str = "VEH"

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

    # LLM settings
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Company mode (per-agent heartbeat loop)
    company_mode_enabled: bool = Field(
        default=False,
        description="Enable PACO company heartbeat loop (agent manages own schedules)",
    )
    paco_api_url: str = Field(
        default="http://localhost:8000",
        description="PACO backend API URL for company heartbeat reporting",
    )
    infrastructure_id: str = Field(
        default="",
        description="PACO infrastructure ID this agent belongs to",
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> VehiclesAgentSettings:
    """Get cached settings instance"""
    return VehiclesAgentSettings()
