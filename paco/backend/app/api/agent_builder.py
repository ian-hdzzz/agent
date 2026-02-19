"""
PACO Agent Builder API

REST + SSE endpoints for the conversational agent builder.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import DbSession, OptionalUser
from app.db.models import Agent, AgentSkill, AgentTool, BuilderSession, Skill, Tool
from app.services.builder_agent import BuilderAgentService

router = APIRouter(prefix="/agent-builder", tags=["Agent Builder"])


# =============================================================================
# Schemas
# =============================================================================


class CreateSessionRequest(BaseModel):
    prompt: str
    template_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    status: str
    phase: str
    agent_id: Optional[str]
    total_input_tokens: int
    total_output_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionDetailResponse(SessionResponse):
    conversation_history: List[Dict[str, Any]]
    draft_config: Dict[str, Any]
    artifacts: List[Dict[str, Any]]


class SendMessageRequest(BaseModel):
    message: str


class ArtifactResponse(BaseModel):
    type: str
    id: Optional[str] = None
    name: Optional[str] = None
    data: Dict[str, Any] = {}


# =============================================================================
# Helpers
# =============================================================================


def _session_to_response(session: BuilderSession) -> SessionResponse:
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        status=session.status,
        phase=session.phase,
        agent_id=str(session.agent_id) if session.agent_id else None,
        total_input_tokens=session.total_input_tokens,
        total_output_tokens=session.total_output_tokens,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _session_to_detail(session: BuilderSession) -> SessionDetailResponse:
    return SessionDetailResponse(
        id=str(session.id),
        title=session.title,
        status=session.status,
        phase=session.phase,
        agent_id=str(session.agent_id) if session.agent_id else None,
        total_input_tokens=session.total_input_tokens,
        total_output_tokens=session.total_output_tokens,
        created_at=session.created_at,
        updated_at=session.updated_at,
        conversation_history=session.conversation_history or [],
        draft_config=session.draft_config or {},
        artifacts=session.artifacts or [],
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    db: DbSession,
    user: OptionalUser,
) -> SessionResponse:
    """Create a new Agent Builder session."""
    # Derive title from prompt
    title = request.prompt[:60].strip()
    if len(request.prompt) > 60:
        title += "..."

    session = BuilderSession(
        title=title,
        status="active",
        phase="understand",
        user_id=user.user_id if user else None,
        conversation_history=[],
        draft_config={},
        artifacts=[],
        total_input_tokens=0,
        total_output_tokens=0,
    )

    # If template provided, set initial config
    if request.template_id:
        session.draft_config = {"template": request.template_id}

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return _session_to_response(session)


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    db: DbSession,
    user: OptionalUser,
) -> List[SessionResponse]:
    """List builder sessions."""
    query = select(BuilderSession).order_by(BuilderSession.created_at.desc())
    if user:
        query = query.where(BuilderSession.user_id == user.user_id)
    result = await db.execute(query)
    sessions = result.scalars().all()
    return [_session_to_response(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    db: DbSession,
) -> SessionDetailResponse:
    """Get session details with full conversation history."""
    result = await db.execute(
        select(BuilderSession).where(BuilderSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_detail(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: DbSession,
) -> None:
    """Delete a builder session."""
    result = await db.execute(
        select(BuilderSession).where(BuilderSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: UUID,
    request: SendMessageRequest,
    db: DbSession,
):
    """Send a message to the builder agent. Returns SSE stream."""
    result = await db.execute(
        select(BuilderSession).where(BuilderSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    service = BuilderAgentService(db)

    return StreamingResponse(
        service.process_message(session, request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions/{session_id}/artifacts")
async def get_artifacts(
    session_id: UUID,
    db: DbSession,
) -> Dict[str, Any]:
    """Get all artifacts created in this session, with full details."""
    result = await db.execute(
        select(BuilderSession).where(BuilderSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response: Dict[str, Any] = {
        "agent": None,
        "tools": [],
        "skills": [],
        "mcp_servers": [],
        "process_flow": None,
        "knowledge_base": None,
    }

    if session.agent_id:
        agent_result = await db.execute(
            select(Agent)
            .where(Agent.id == session.agent_id)
            .options(
                selectinload(Agent.agent_skills).selectinload(AgentSkill.skill),
                selectinload(Agent.agent_tools).selectinload(AgentTool.tool),
            )
        )
        agent = agent_result.scalar_one_or_none()
        if agent:
            response["agent"] = {
                "id": str(agent.id),
                "name": agent.name,
                "display_name": agent.display_name,
                "description": agent.description,
                "model": agent.model,
                "status": agent.status,
                "system_prompt": agent.system_prompt,
            }

            # Tools
            for at in agent.agent_tools:
                tool = at.tool
                if tool:
                    response["tools"].append({
                        "id": str(tool.id),
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    })

            # Skills
            for ask in agent.agent_skills:
                skill = ask.skill
                if skill:
                    response["skills"].append({
                        "id": str(skill.id),
                        "code": skill.code,
                        "name": skill.name,
                        "description": skill.description,
                    })

            # Process flow and knowledge base from sdk_config
            sdk_config = agent.sdk_config or {}
            response["process_flow"] = sdk_config.get("process_flow")
            response["knowledge_base"] = sdk_config.get("knowledge_base")

    return response
