"""
PACO Backend Configuration

Loads settings from environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "PACO Agent Hub"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql://paco:paco_secret@localhost:5432/paco"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Security
    secret_key: str = "your-secret-key-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3006"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3001"

    # Agent Paths
    agents_config_path: str = "../agents"
    flows_config_path: str = "../flows"

    # Skills filesystem (source of truth for SKILL.md files)
    skills_base_path: str = "./skills"

    # PM2
    pm2_socket_path: str = "/root/.pm2/rpc.sock"

    # Anthropic API
    anthropic_api_key: str = ""

    # Infrastructure Code Generation
    generated_projects_path: str = "./generated_projects"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
