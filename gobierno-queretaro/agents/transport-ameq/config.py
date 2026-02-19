"""
Gobierno Queretaro - Transport AMEQ Agent Configuration
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class TransportAgentSettings(BaseSettings):
    """Transport AMEQ Agent configuration"""

    # Agent identity
    agent_id: str = "transport-ameq"
    agent_name: str = "Agente de Transporte - AMEQ"
    category_code: str = "TRA"

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

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> TransportAgentSettings:
    """Get cached settings instance"""
    return TransportAgentSettings()
