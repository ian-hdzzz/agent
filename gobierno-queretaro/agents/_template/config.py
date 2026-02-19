"""
Gobierno Querétaro - Agent Configuration
Environment-based configuration for agents
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


# Confidentiality levels for data classification
ConfidentialityLevel = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]

# PII types that agents may handle
PIIType = Literal[
    "CURP", "RFC", "PHONE_MX", "CONTRACT_CEA", "EMAIL",
    "CREDIT_CARD", "INE", "PASSPORT", "NSS", "ADDRESS",
]


class AgentCapabilities(BaseSettings):
    """
    Agent capabilities metadata for orchestrator routing decisions.

    This configuration helps the orchestrator:
    - Understand what context the agent needs
    - Know which actions require user confirmation
    - Manage handoff between agents
    - Track PII handling requirements
    - Auto-configure the classifier (keywords, hints, descriptions)
    """

    # Context requirements
    required_context: list[str] = Field(
        default_factory=lambda: ["conversation_id"],
        description="Context fields required for this agent to function",
    )
    optional_context: list[str] = Field(
        default_factory=lambda: ["contract_number", "contact_id"],
        description="Context fields that enhance agent performance but aren't required",
    )

    # Confirmation requirements
    confirmation_required_for: list[str] = Field(
        default_factory=lambda: ["create_ticket", "handoff"],
        description="Actions that require user confirmation before executing",
    )

    # Handoff configuration
    can_handoff_to: list[str] = Field(
        default_factory=lambda: ["citizen-attention", "human"],
        description="Agent IDs or 'human' that this agent can hand off to",
    )

    # Max conversation turns before suggesting handoff
    max_turns_before_handoff: int = Field(
        default=10,
        description="Suggest human handoff after this many turns without resolution",
    )

    # Classification metadata — used by orchestrator to build classifier dynamically
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords for fast keyword-based classification (lowercase)",
    )
    classification_hint: str = Field(
        default="",
        description="One-line hint for the LLM classification prompt (e.g. 'placas, multas, licencias')",
    )
    category_description: str = Field(
        default="",
        description="Human-readable category description (e.g. 'Trámites Vehiculares')",
    )

    def to_dict(self) -> dict:
        """Serialize capabilities for registration payload."""
        return {
            "required_context": self.required_context,
            "optional_context": self.optional_context,
            "confirmation_required_for": self.confirmation_required_for,
            "can_handoff_to": self.can_handoff_to,
            "max_turns_before_handoff": self.max_turns_before_handoff,
            "keywords": self.keywords,
            "classification_hint": self.classification_hint,
            "category_description": self.category_description,
        }


class AgentSettings(BaseSettings):
    """Agent configuration settings"""

    # Agent identity
    agent_id: str = os.getenv("AGENT_ID", "template-agent")
    agent_name: str = os.getenv("AGENT_NAME", "Template Agent")
    agent_description: str = os.getenv("AGENT_DESCRIPTION", "Template agent for government services")
    category_code: str = os.getenv("AGENT_CATEGORY_CODE", "ATC")

    # Versioning: <agent-id>@<major>.<minor>.<patch>
    version: str = os.getenv("AGENT_VERSION", "1.0.0")

    # SLA tier: critical (99.99%), standard (99.9%), best_effort (99%)
    sla_tier: Literal["critical", "standard", "best_effort"] = "standard"

    # Security classification
    confidentiality_level: ConfidentialityLevel = Field(
        default="INTERNAL",
        description="Data classification level for this agent's operations",
    )

    # PII handling
    handles_pii: list[str] = Field(
        default_factory=lambda: ["PHONE_MX", "EMAIL"],
        description="Types of PII this agent is authorized to handle",
    )

    # Skip audit logging for sensitive agents (e.g., IQM for crisis situations)
    skip_detailed_audit: bool = Field(
        default=False,
        description="Skip detailed audit logging for privacy-sensitive operations",
    )

    # Capabilities
    capabilities: AgentCapabilities = Field(
        default_factory=AgentCapabilities,
        description="Agent capability metadata for routing",
    )

    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/gobierno"
    )

    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Orchestrator URL for self-registration
    orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Memory
    memory_enabled: bool = Field(
        default=True,
        description="Enable persistent memory for this agent",
    )
    memory_max_in_prompt: int = Field(
        default=5,
        description="Max memories to inject into prompt",
    )

    # LLM settings
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Heartbeat interval in seconds
    heartbeat_interval: int = 60

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

    def to_info_dict(self) -> dict:
        """
        Return agent info for /info endpoint.

        Used by orchestrator to understand agent capabilities.
        """
        return {
            "id": self.agent_id,
            "name": self.agent_name,
            "description": self.agent_description,
            "version": self.version,
            "category_code": self.category_code,
            "confidentiality_level": self.confidentiality_level,
            "sla_tier": self.sla_tier,
            "handles_pii": self.handles_pii,
            "capabilities": self.capabilities.to_dict(),
        }

    def to_registration_payload(self) -> dict:
        """
        Build payload for self-registration with orchestrator.
        """
        return {
            "agent_id": self.agent_id,
            "name": self.agent_name,
            "description": self.agent_description,
            "category_code": self.category_code,
            "endpoint": f"http://{self.agent_id}:{self.port}",
            "version": self.version,
            "confidentiality_level": self.confidentiality_level,
            "sla_tier": self.sla_tier,
            "capabilities": self.capabilities.to_dict(),
        }


@lru_cache()
def get_settings() -> AgentSettings:
    """Get cached settings instance"""
    return AgentSettings()


# ============================================
# Pre-configured Agent Settings
# ============================================

def get_water_cea_config() -> dict:
    """Configuration for Water CEA agent."""
    return {
        "agent_id": "water-cea",
        "agent_name": "Agente de Agua - CEA",
        "agent_description": "Consultas de agua, fugas, consumos y deuda de agua",
        "category_code": "CEA",
        "version": "1.0.0",
        "sla_tier": "standard",
        "confidentiality_level": "INTERNAL",
        "handles_pii": ["CONTRACT_CEA", "PHONE_MX", "ADDRESS"],
        "capabilities": {
            "required_context": ["conversation_id"],
            "optional_context": ["contract_number", "contact_id"],
            "confirmation_required_for": ["create_ticket", "report_leak"],
            "can_handoff_to": ["citizen-attention", "human"],
        },
    }


def get_women_iqm_config() -> dict:
    """Configuration for Women IQM agent - highest confidentiality."""
    return {
        "agent_id": "women-iqm",
        "agent_name": "Agente de Atención a Mujeres - IQM",
        "agent_description": "Apoyo a mujeres, violencia de género, orientación legal",
        "category_code": "IQM",
        "version": "1.0.0",
        "sla_tier": "critical",
        "confidentiality_level": "SECRET",  # Highest level for crisis/violence cases
        "handles_pii": ["CURP", "RFC", "PHONE_MX", "ADDRESS", "INE"],
        "skip_detailed_audit": True,  # Privacy protection for sensitive cases
        "capabilities": {
            "required_context": ["conversation_id"],
            "optional_context": ["contact_id"],
            "confirmation_required_for": [],  # No confirmation needed for crisis
            "can_handoff_to": ["human"],  # Direct human handoff for serious cases
        },
    }


def get_citizen_attention_config() -> dict:
    """Configuration for Citizen Attention fallback agent."""
    return {
        "agent_id": "citizen-attention",
        "agent_name": "Agente de Atención Ciudadana",
        "agent_description": "Atención general, quejas, sugerencias, y fallback para otros agentes",
        "category_code": "ATC",
        "version": "1.0.0",
        "sla_tier": "best_effort",
        "confidentiality_level": "INTERNAL",
        "handles_pii": ["PHONE_MX", "EMAIL"],
        "capabilities": {
            "required_context": ["conversation_id"],
            "optional_context": ["contact_id", "original_category"],
            "confirmation_required_for": ["create_ticket", "escalate"],
            "can_handoff_to": ["human"],
        },
    }
