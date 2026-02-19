"""
PACO Processes API

Process CRUD endpoints for saving/loading process analyses to database.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, OperatorUser
from app.db.models import Process

router = APIRouter(prefix="/processes", tags=["Processes"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ProcessResponse(BaseModel):
    """Process response model."""

    id: str
    name: str
    department: str
    description: Optional[str]
    status: str
    extraction_md: Optional[str]
    as_is_analysis_md: Optional[str]
    compliance_audit_md: Optional[str]
    to_be_optimization_md: Optional[str]
    implementation_plan_md: Optional[str]
    executive_summary_md: Optional[str]
    diagram_as_is: Optional[str]
    diagram_to_be_digital: Optional[str]
    diagram_to_be_hybrid: Optional[str]
    run_metadata: Optional[Dict[str, Any]]
    model_used: Optional[str]
    source_files: Optional[List[str]]
    tags: Optional[List[str]]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProcessCreateRequest(BaseModel):
    """Process creation request."""

    name: str
    department: str
    description: Optional[str] = None
    status: str = "completed"
    extraction_md: Optional[str] = None
    as_is_analysis_md: Optional[str] = None
    compliance_audit_md: Optional[str] = None
    to_be_optimization_md: Optional[str] = None
    implementation_plan_md: Optional[str] = None
    executive_summary_md: Optional[str] = None
    diagram_as_is: Optional[str] = None
    diagram_to_be_digital: Optional[str] = None
    diagram_to_be_hybrid: Optional[str] = None
    run_metadata: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    source_files: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class ProcessUpdateRequest(BaseModel):
    """Process update request."""

    name: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


# =============================================================================
# Helper Functions
# =============================================================================


def process_to_response(process: Process) -> ProcessResponse:
    """Convert Process model to ProcessResponse."""
    return ProcessResponse(
        id=str(process.id),
        name=process.name,
        department=process.department,
        description=process.description,
        status=process.status,
        extraction_md=process.extraction_md,
        as_is_analysis_md=process.as_is_analysis_md,
        compliance_audit_md=process.compliance_audit_md,
        to_be_optimization_md=process.to_be_optimization_md,
        implementation_plan_md=process.implementation_plan_md,
        executive_summary_md=process.executive_summary_md,
        diagram_as_is=process.diagram_as_is,
        diagram_to_be_digital=process.diagram_to_be_digital,
        diagram_to_be_hybrid=process.diagram_to_be_hybrid,
        run_metadata=process.run_metadata,
        model_used=process.model_used,
        source_files=process.source_files,
        tags=process.tags,
        created_by=str(process.created_by) if process.created_by else None,
        created_at=process.created_at,
        updated_at=process.updated_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/tags", response_model=List[str])
async def list_tags(
    db: DbSession,
    user: CurrentUser,
) -> List[str]:
    """
    List all unique tags across all processes.

    Returns a flat, deduplicated list of tag strings.
    """
    result = await db.execute(
        select(Process.tags).where(Process.tags.isnot(None))
    )
    rows = result.scalars().all()

    all_tags: set[str] = set()
    for tag_list in rows:
        if isinstance(tag_list, list):
            all_tags.update(tag_list)

    return sorted(all_tags)


@router.get("", response_model=List[ProcessResponse])
async def list_processes(
    db: DbSession,
    user: CurrentUser,
    search: Optional[str] = Query(None, description="Search by name"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
) -> List[ProcessResponse]:
    """
    List all processes.

    Supports optional search by name, filter by tag, and filter by status.
    Results are ordered by updated_at descending.
    """
    query = select(Process)

    if search:
        query = query.where(Process.name.ilike(f"%{search}%"))

    if status_filter:
        query = query.where(Process.status == status_filter)

    if tag:
        # JSON array contains — works with PostgreSQL JSONB
        query = query.where(Process.tags.contains([tag]))

    query = query.order_by(Process.updated_at.desc())

    result = await db.execute(query)
    processes = result.scalars().all()

    return [process_to_response(p) for p in processes]


@router.get("/{process_id}", response_model=ProcessResponse)
async def get_process(
    process_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> ProcessResponse:
    """
    Get a single process by ID.

    Returns 404 if not found.
    """
    result = await db.execute(select(Process).where(Process.id == process_id))
    process = result.scalar_one_or_none()

    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {process_id} not found",
        )

    return process_to_response(process)


@router.post("", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
async def create_process(
    request: ProcessCreateRequest,
    db: DbSession,
    user: OperatorUser,
) -> ProcessResponse:
    """
    Create a new process.

    Requires operator or admin role.
    """
    process = Process(
        name=request.name,
        department=request.department,
        description=request.description,
        status=request.status,
        extraction_md=request.extraction_md,
        as_is_analysis_md=request.as_is_analysis_md,
        compliance_audit_md=request.compliance_audit_md,
        to_be_optimization_md=request.to_be_optimization_md,
        implementation_plan_md=request.implementation_plan_md,
        executive_summary_md=request.executive_summary_md,
        diagram_as_is=request.diagram_as_is,
        diagram_to_be_digital=request.diagram_to_be_digital,
        diagram_to_be_hybrid=request.diagram_to_be_hybrid,
        run_metadata=request.run_metadata,
        model_used=request.model_used,
        source_files=request.source_files,
        tags=request.tags,
        created_by=user.user_id,
    )
    db.add(process)
    await db.commit()
    await db.refresh(process)

    return process_to_response(process)


@router.put("/{process_id}", response_model=ProcessResponse)
async def update_process(
    process_id: UUID,
    request: ProcessUpdateRequest,
    db: DbSession,
    user: OperatorUser,
) -> ProcessResponse:
    """
    Update an existing process.

    Requires operator or admin role.
    """
    result = await db.execute(select(Process).where(Process.id == process_id))
    process = result.scalar_one_or_none()

    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {process_id} not found",
        )

    if request.name is not None:
        process.name = request.name
    if request.department is not None:
        process.department = request.department
    if request.description is not None:
        process.description = request.description
    if request.status is not None:
        process.status = request.status
    if request.tags is not None:
        process.tags = request.tags

    await db.commit()
    await db.refresh(process)

    return process_to_response(process)


@router.delete("/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process(
    process_id: UUID,
    db: DbSession,
    user: OperatorUser,
) -> None:
    """
    Delete a process.

    Requires operator or admin role.
    """
    result = await db.execute(select(Process).where(Process.id == process_id))
    process = result.scalar_one_or_none()

    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Process {process_id} not found",
        )

    await db.delete(process)
    await db.commit()
