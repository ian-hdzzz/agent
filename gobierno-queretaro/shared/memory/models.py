"""
Pydantic models for PACO persistent memory.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
from uuid import UUID


class Memory(BaseModel):
    """A single scoped memory record."""
    id: Optional[UUID] = None
    scope_id: str
    citizen_contact_id: str
    memory_type: Literal["fact", "preference", "issue", "note"]
    content: str
    content_encrypted: bool = False
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    source_conversation_id: Optional[str] = None
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class InteractionSummary(BaseModel):
    """Conversation summary scoped to a component."""
    id: Optional[UUID] = None
    scope_id: str
    citizen_contact_id: str
    conversation_external_id: Optional[str] = None
    summary_text: str
    topics: list[str] = Field(default_factory=list)
    outcome: Optional[Literal["resolved", "pending", "escalated", "abandoned"]] = None
    sentiment: Optional[Literal["positive", "neutral", "negative", "frustrated"]] = None
    ticket_folios: list[str] = Field(default_factory=list)
    message_count: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class CitizenProfile(BaseModel):
    """High-level citizen identity used by the orchestrator."""
    contact_id: str
    citizen_id_hash: Optional[str] = None
    display_name_encrypted: Optional[str] = None
    preferred_language: str = "es"
    total_conversations: int = 0
    total_tickets: int = 0
    frequent_categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    confidentiality_level: str = "PUBLIC"
    anonymized_at: Optional[datetime] = None
    deletion_requested_at: Optional[datetime] = None


class SystemNote(BaseModel):
    """Admin observation about a citizen."""
    id: Optional[UUID] = None
    citizen_contact_id: str
    note_type: Literal["vip", "escalation_pattern", "observation", "flag"]
    content: str
    severity: Literal["info", "warning", "critical"] = "info"
    created_by: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MemoryBundle(BaseModel):
    """Collection of memories + summaries returned by recall()."""
    memories: list[Memory] = Field(default_factory=list)
    summaries: list[InteractionSummary] = Field(default_factory=list)
    profile: Optional[CitizenProfile] = None
    notes: list[SystemNote] = Field(default_factory=list)
    formatted_context: Optional[str] = None


class ConversationSnapshot(BaseModel):
    """Batch queue item for nightly summarization."""
    id: Optional[UUID] = None
    conversation_external_id: str
    contact_id: str
    message_history: list[dict] = Field(default_factory=list)
    agents_involved: list[str] = Field(default_factory=list)
    categories_involved: list[str] = Field(default_factory=list)
    summarized: bool = False
    session_ended_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
