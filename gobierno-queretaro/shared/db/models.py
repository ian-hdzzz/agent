"""
Gobierno Querétaro - Database Models
Shared Pydantic models for all agents
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================
# Category Definitions
# ============================================

CategoryCode = Literal[
    "CEA",  # Water - CEA
    "TRA",  # Transport - AMEQ
    "EDU",  # Education - USEBEQ
    "VEH",  # Vehicles
    "PSI",  # Psychology - SEJUVE
    "IQM",  # Women - IQM
    "CUL",  # Culture
    "RPP",  # Registry - RPP
    "LAB",  # Labor - CCLQ
    "VIV",  # Housing - IVEQ
    "APP",  # APPQRO
    "SOC",  # Social - SEDESOQ
    "ATC",  # Citizen Attention
    "EXIT", # Exit conversation
]

CATEGORY_DESCRIPTIONS = {
    "CEA": "Agua CEA - agua, fugas, deuda de agua, consumos",
    "TRA": "Transporte AMEQ - rutas, horarios, autobús",
    "EDU": "Educación USEBEQ - escuelas, inscripciones, becas",
    "VEH": "Vehículos - placas, multas, registro vehicular",
    "PSI": "Psicología SEJUVE - citas, salud mental",
    "IQM": "Atención a Mujeres IQM - apoyo, violencia de género",
    "CUL": "Cultura - eventos, talleres, becas culturales",
    "RPP": "Registro Público RPP - documentos, certificados",
    "LAB": "Conciliación Laboral CCLQ - trabajo, demandas",
    "VIV": "Vivienda IVEQ - créditos, programas de vivienda",
    "APP": "APPQRO - soporte técnico de la app",
    "SOC": "Programas Sociales SEDESOQ - beneficios, ayudas",
    "ATC": "Atención Ciudadana - quejas, sugerencias, PQRS",
    "EXIT": "Salir del asistente",
}

AGENT_ID_BY_CATEGORY = {
    "CEA": "water-cea",
    "TRA": "transport-ameq",
    "EDU": "education-usebeq",
    "VEH": "vehicles",
    "PSI": "psychology-sejuve",
    "IQM": "women-iqm",
    "CUL": "culture",
    "RPP": "registry-rpp",
    "LAB": "labor-cclq",
    "VIV": "housing-iveq",
    "APP": "appqro",
    "SOC": "social-sedesoq",
    "ATC": "citizen-attention",
}


# ============================================
# Agent Models
# ============================================

class Agent(BaseModel):
    """Agent registry entry"""

    id: str
    name: str
    description: str | None = None
    endpoint: str | None = None
    category_code: CategoryCode
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ============================================
# Conversation Models
# ============================================

class Conversation(BaseModel):
    """Conversation state"""

    id: UUID
    external_id: str | None = None  # Chatwoot conversation ID
    contact_id: str | None = None
    current_agent_id: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Message(BaseModel):
    """Message in conversation history"""

    id: UUID | None = None
    conversation_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    agent_id: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


# ============================================
# Task Models
# ============================================

TaskStatus = Literal["pending", "in_progress", "completed", "failed"]


class SubTask(BaseModel):
    """Subtask within a task"""

    name: str
    status: TaskStatus = "pending"
    result: dict[str, Any] | None = None
    error: str | None = None


class Task(BaseModel):
    """Multi-step task"""

    id: UUID | None = None
    conversation_id: UUID
    agent_id: str
    task_type: str
    status: TaskStatus = "pending"
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    subtasks: list[SubTask] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None


# ============================================
# Event Models
# ============================================

class Event(BaseModel):
    """Event for pub/sub"""

    id: UUID | None = None
    event_type: str
    source_agent_id: str | None = None
    target_agent_id: str | None = None
    conversation_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    processed: bool = False
    created_at: datetime | None = None


# ============================================
# Ticket Models
# ============================================

TicketStatus = Literal["open", "in_progress", "resolved", "closed", "cancelled"]
TicketPriority = Literal["low", "medium", "high", "urgent"]


class Ticket(BaseModel):
    """Government service ticket"""

    id: UUID | None = None
    folio: str | None = None
    conversation_id: UUID | None = None
    agent_id: str | None = None
    category_code: CategoryCode
    subcategory_code: str | None = None
    title: str
    description: str | None = None
    status: TicketStatus = "open"
    priority: TicketPriority = "medium"
    contact_info: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None


class CreateTicketRequest(BaseModel):
    """Request to create a ticket"""

    category_code: CategoryCode
    subcategory_code: str | None = None
    title: str
    description: str | None = None
    priority: TicketPriority = "medium"
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    contract_number: str | None = None
    location: str | None = None


# ============================================
# API Request/Response Models
# ============================================

class AgentRequest(BaseModel):
    """Request to an agent"""

    message: str
    conversation_id: str | None = None
    contact_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from an agent"""

    response: str
    agent_id: str
    conversation_id: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    task_id: str | None = None
    ticket_folio: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Enhanced fields for orchestration
    actions_taken: list[str] = Field(
        default_factory=list,
        description="List of actions performed by the agent",
    )
    context_updates: dict[str, Any] = Field(
        default_factory=dict,
        description="Data to add to session context for other agents",
    )
    next_agent: str | None = Field(
        default=None,
        description="Suggested next agent for handoff (agent ID or category code)",
    )
    handoff_to_human: bool = Field(
        default=False,
        description="Whether to escalate to human operator",
    )
    handoff_reason: str | None = Field(
        default=None,
        description="Reason for human handoff or agent-to-agent handoff",
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether the action requires user confirmation before proceeding",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in the response (0-1)",
    )


class ClassificationResult(BaseModel):
    """Result of intent classification"""

    category: CategoryCode
    confidence: float = 0.0
    extracted_data: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    agent_id: str
    agent_name: str
    version: str = "1.0.0"
