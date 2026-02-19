"""Gobierno Queretaro - Housing IVEQ Agent Configuration"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings

class HousingAgentSettings(BaseSettings):
    agent_id: str = "housing-iveq"
    agent_name: str = "Agente de Vivienda - IVEQ"
    category_code: str = "VIV"
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/gobierno")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    host: str = "0.0.0.0"
    port: int = 8000
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> HousingAgentSettings:
    return HousingAgentSettings()
