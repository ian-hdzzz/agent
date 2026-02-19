"""
Gobierno Querétaro - Water CEA Agent Configuration
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class WaterAgentSettings(BaseSettings):
    """Water CEA Agent configuration"""

    # Agent identity
    agent_id: str = "water-cea"
    agent_name: str = "Agente de Agua - CEA"
    category_code: str = "CEA"

    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/gobierno"
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # CEA API
    cea_api_base: str = "https://aquacis-cf.ceaqueretaro.gob.mx/Comercial/services"
    cea_proxy_url: str | None = os.getenv("CEA_PROXY_URL")

    # CEA SOAP credentials
    cea_soap_username: str = os.getenv("CEA_SOAP_USERNAME", "WSGESTIONDEUDA")
    cea_soap_password: str = os.getenv("CEA_SOAP_PASSWORD", "WSGESTIONDEUDA")

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
def get_settings() -> WaterAgentSettings:
    """Get cached settings instance"""
    return WaterAgentSettings()
