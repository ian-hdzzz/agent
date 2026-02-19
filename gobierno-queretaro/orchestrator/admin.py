"""
PACO Admin API — Memory management, citizen lookup, configuration, and audit.

All endpoints require admin authentication via either:
  - X-Admin-Key header (legacy)
  - Authorization: Bearer <jwt> header (Paco JWT with admin role)

Agent memory access is proxied to each agent's /memory/{contact_id} endpoint.
"""

import json
import logging
import os
import re
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger(__name__)

ADMIN_API_KEY = os.getenv("PACO_ADMIN_API_KEY", "")

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# Auth dependency
# =============================================================================

async def verify_admin_auth(request: Request):
    """
    Validate admin access via X-Admin-Key header OR Paco JWT Bearer token.

    JWT tokens must have role=admin to access admin endpoints.
    """
    # --- Try Bearer JWT first ---
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from .config import get_settings
        settings = get_settings()

        if not settings.paco_jwt_secret:
            raise HTTPException(
                status_code=503,
                detail="JWT auth not configured (PACO_JWT_SECRET missing)",
            )

        token = auth_header[7:]  # strip "Bearer "
        try:
            from shared.auth import validate_paco_jwt
            claims = validate_paco_jwt(token, settings.paco_jwt_secret)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))

        if claims["role"] != "admin":
            raise HTTPException(
                status_code=403,
                detail=f"Admin role required, got '{claims['role']}'",
            )
        return  # JWT validated with admin role

    # --- Fall back to X-Admin-Key ---
    key = request.headers.get("X-Admin-Key", "")
    if key:
        if not ADMIN_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Admin API not configured (PACO_ADMIN_API_KEY missing)",
            )
        if key == ADMIN_API_KEY:
            return  # API key matches
        raise HTTPException(status_code=401, detail="Invalid admin key")

    # --- Neither provided ---
    raise HTTPException(
        status_code=401,
        detail="Authentication required: provide Authorization Bearer token or X-Admin-Key header",
    )


# =============================================================================
# Request/Response models
# =============================================================================

class ConfigUpdateRequest(BaseModel):
    config: dict[str, Any]
    updated_by: str = "admin"


class SystemNoteRequest(BaseModel):
    note_type: str = "observation"
    content: str
    severity: str = "info"
    created_by: str = "admin"


# =============================================================================
# Helper: get PacoMemory for orchestrator scope
# =============================================================================

def _get_memory():
    from shared.memory import get_paco_memory
    return get_paco_memory(scope_id="orchestrator")


# =============================================================================
# Configuration endpoints
# =============================================================================

@router.get("/memory/config", dependencies=[Depends(verify_admin_auth)])
async def get_global_config():
    """Get global memory configuration."""
    memory = _get_memory()
    config = await memory.get_config()
    return config.model_dump()


@router.put("/memory/config", dependencies=[Depends(verify_admin_auth)])
async def update_global_config(req: ConfigUpdateRequest):
    """Update global memory configuration."""
    memory = _get_memory()
    await memory.config_store_instance.save_config("global", req.config, req.updated_by)
    return {"status": "updated", "config_id": "global"}


@router.get("/memory/scopes/{scope_id}/config", dependencies=[Depends(verify_admin_auth)])
async def get_scope_config(scope_id: str):
    """Get per-scope memory configuration."""
    memory = _get_memory()
    config = await memory.config_store_instance.get_effective_config(scope_id)
    return config.model_dump()


@router.put("/memory/scopes/{scope_id}/config", dependencies=[Depends(verify_admin_auth)])
async def update_scope_config(scope_id: str, req: ConfigUpdateRequest):
    """Update per-scope memory configuration (enable/disable, overrides)."""
    memory = _get_memory()
    await memory.config_store_instance.save_config(scope_id, req.config, req.updated_by)
    return {"status": "updated", "config_id": scope_id}


# =============================================================================
# Citizens endpoints
# =============================================================================

@router.get("/memory/citizens", dependencies=[Depends(verify_admin_auth)])
async def list_citizens(
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List citizen profiles with optional search."""
    memory = _get_memory()
    profiles, total = await memory.store_instance.list_citizens(search=search, limit=limit, offset=offset)
    return {
        "citizens": [p.model_dump(mode="json") for p in profiles],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/memory/citizens/{contact_id}", dependencies=[Depends(verify_admin_auth)])
async def get_citizen(contact_id: str):
    """Get citizen profile + system notes."""
    memory = _get_memory()
    profile = await memory.recall_citizen_profile(contact_id)
    notes = await memory.store_instance.get_system_notes(contact_id)
    return {
        "profile": profile.model_dump(mode="json") if profile else None,
        "notes": [n.model_dump(mode="json") for n in notes],
    }


@router.delete("/memory/citizens/{contact_id}", dependencies=[Depends(verify_admin_auth)])
async def forget_citizen(contact_id: str, performed_by: str = Query("admin")):
    """GDPR: forget citizen from ALL scopes. Audit logged."""
    memory = _get_memory()
    count = await memory.forget_citizen_all_scopes(contact_id, performed_by=performed_by)
    return {"status": "forgotten", "contact_id": contact_id, "total_deleted": count}


@router.post("/memory/citizens/{contact_id}/notes", dependencies=[Depends(verify_admin_auth)])
async def add_citizen_note(contact_id: str, req: SystemNoteRequest):
    """Add a system note about a citizen."""
    memory = _get_memory()
    note_id = await memory.store_instance.add_system_note(
        contact_id=contact_id,
        note_type=req.note_type,
        content=req.content,
        severity=req.severity,
        created_by=req.created_by,
    )
    return {"status": "created", "note_id": str(note_id)}


# =============================================================================
# Scope memory (proxied to agent endpoints)
# =============================================================================

@router.get("/memory/scopes/{scope_id}/citizens/{contact_id}", dependencies=[Depends(verify_admin_auth)])
async def get_scope_memories(scope_id: str, contact_id: str):
    """
    View a scope's memories for a citizen.
    Proxies to the agent's /memory/{contact_id} endpoint.
    """
    from .config import get_agent_registry

    registry = get_agent_registry()

    # Find the agent URL for this scope
    agent_url = None
    for _cat, info in registry.items():
        if info["id"] == scope_id:
            agent_url = info["url"]
            break

    if not agent_url:
        raise HTTPException(status_code=404, detail=f"Unknown scope: {scope_id}")

    try:
        from shared.utils.http_client import get_resilient_client
        client = get_resilient_client()
        response = await client.get(f"{agent_url}/memory/{contact_id}", timeout=10.0)
        return response
    except Exception as e:
        logger.error(f"Failed to proxy memory request to {scope_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Agent {scope_id} unreachable: {str(e)}")


# =============================================================================
# Statistics
# =============================================================================

@router.get("/memory/stats", dependencies=[Depends(verify_admin_auth)])
async def get_stats():
    """Global + per-scope memory statistics."""
    memory = _get_memory()
    return await memory.get_stats()


# =============================================================================
# Audit log
# =============================================================================

@router.get("/memory/audit", dependencies=[Depends(verify_admin_auth)])
async def get_audit_log(
    contact_id: Optional[str] = Query(None),
    scope_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Query memory audit log."""
    memory = _get_memory()
    entries = await memory.store_instance.get_audit_log(
        contact_id=contact_id,
        scope_id=scope_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    # Serialize UUID and datetime
    for entry in entries:
        for k, v in entry.items():
            if hasattr(v, "isoformat"):
                entry[k] = v.isoformat()
            elif hasattr(v, "hex"):
                entry[k] = str(v)
    return {"entries": entries, "limit": limit, "offset": offset}


# =============================================================================
# Maintenance
# =============================================================================

@router.post("/memory/maintenance/cleanup", dependencies=[Depends(verify_admin_auth)])
async def trigger_cleanup():
    """Trigger expired memory cleanup."""
    memory = _get_memory()
    count = await memory.store_instance.cleanup_expired()
    return {"status": "completed", "deleted": count}


@router.post("/memory/maintenance/summarize-now", dependencies=[Depends(verify_admin_auth)])
async def trigger_summarize():
    """Trigger batch summarization of pending snapshots."""
    try:
        from scripts.nightly_summarize import run_summarization_batch
        result = await run_summarization_batch()
        return {"status": "completed", **result}
    except ImportError:
        raise HTTPException(status_code=501, detail="Summarization script not available in this context")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# API Registry helper
# =============================================================================

def _get_api_registry():
    from shared.api_registry import get_api_client_factory
    return get_api_client_factory()


class APITestRequest(BaseModel):
    operation_id: str
    params: dict[str, Any] = {}


# =============================================================================
# API Registry endpoints
# =============================================================================

@router.get("/apis", dependencies=[Depends(verify_admin_auth)])
async def list_apis():
    """List all registered government APIs."""
    factory = _get_api_registry()
    apis = []
    for api_info in factory.list_apis():
        defn = factory.get_definition(api_info["id"])
        # Mask base_url: show host only
        masked_url = re.sub(r"(https?://[^/]+).*", r"\1/...", defn.base_url)
        apis.append({
            "id": defn.api_id,
            "name": defn.name,
            "protocol": defn.protocol,
            "auth_type": defn.auth_type,
            "status": defn.status,
            "operations": len(defn.operations),
            "base_url": masked_url,
        })
    return {"apis": apis, "total": len(apis)}


@router.get("/apis/{api_id}", dependencies=[Depends(verify_admin_auth)])
async def get_api_detail(api_id: str):
    """Get detailed info about a specific API including operations, schema, and circuit breaker state."""
    factory = _get_api_registry()
    try:
        defn = factory.get_definition(api_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"API '{api_id}' not found")

    operations = [
        {
            "id": op.id,
            "description": op.description,
            "input_params": op.input_params,
            "method": op.method if defn.protocol == "REST" else "POST",
            "path": op.path if defn.protocol == "REST" else op.endpoint,
        }
        for op in defn.operations
    ]

    # Load JSON schema if available
    schema = None
    schemas_dir = os.path.join(os.path.dirname(__file__), "..", "shared", "api_registry", "schemas")
    schema_path = os.path.join(schemas_dir, f"{api_id}.json")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

    # Circuit breaker state
    from shared.utils.http_client import get_circuit_breaker
    cb = get_circuit_breaker()
    circuit_breaker = cb.get_stats(api_id)

    return {
        "id": defn.api_id,
        "name": defn.name,
        "description": defn.description,
        "protocol": defn.protocol,
        "auth_type": defn.auth_type,
        "status": defn.status,
        "base_url": defn.base_url,
        "timeout_ms": defn.timeout_ms,
        "rate_limit": defn.rate_limit,
        "operations": operations,
        "schema": schema,
        "circuit_breaker": circuit_breaker,
    }


@router.get("/apis/{api_id}/health", dependencies=[Depends(verify_admin_auth)])
async def check_api_health(api_id: str):
    """Check health of an API by sending a HEAD request to its base_url."""
    factory = _get_api_registry()
    try:
        defn = factory.get_definition(api_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"API '{api_id}' not found")

    if defn.status == "planned":
        return {"api_id": api_id, "healthy": False, "status": "not-available", "latency_ms": None}

    if defn.status == "mocked":
        return {"api_id": api_id, "healthy": True, "status": "mocked", "latency_ms": 0}

    # Active API: try a HEAD request
    import httpx
    try:
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            resp = await client.head(defn.base_url)
        latency_ms = round((time.time() - start) * 1000)
        return {
            "api_id": api_id,
            "healthy": resp.status_code < 500,
            "status": "active",
            "latency_ms": latency_ms,
            "http_status": resp.status_code,
        }
    except Exception as e:
        return {
            "api_id": api_id,
            "healthy": False,
            "status": "error",
            "latency_ms": None,
            "error": str(e),
        }


@router.post("/apis/{api_id}/test", dependencies=[Depends(verify_admin_auth)])
async def test_api_operation(api_id: str, req: APITestRequest):
    """Test a specific API operation. Mocked APIs return fixture data."""
    factory = _get_api_registry()
    try:
        client = factory.get_client(api_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"API '{api_id}' not found")

    defn = factory.get_definition(api_id)
    op = client.get_operation(req.operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail=f"Operation '{req.operation_id}' not found")

    try:
        if defn.protocol == "SOAP":
            # For SOAP, load mock fixture directly (no XML input needed from UI)
            from shared.api_registry.client import _load_mock_response
            mock = _load_mock_response(api_id, req.operation_id, "SOAP")
            if mock:
                return {"success": True, "operation": req.operation_id, "result": mock, "format": "xml"}
            # If active, we'd need actual SOAP XML; for admin testing just indicate that
            if defn.status == "active":
                return {"success": False, "operation": req.operation_id, "error": "SOAP testing requires XML input; use the agent instead"}
            return {"success": False, "operation": req.operation_id, "error": "No mock fixture available"}
        else:
            # REST: separate path_params from query_params based on operation path
            path_params = {}
            query_params = {}
            json_body = None
            for key, value in req.params.items():
                if f"{{{key}}}" in op.path:
                    path_params[key] = value
                elif op.method.upper() in ("POST", "PUT", "PATCH"):
                    if json_body is None:
                        json_body = {}
                    json_body[key] = value
                else:
                    query_params[key] = value

            result = await client.call_rest(
                req.operation_id,
                path_params=path_params or None,
                query_params=query_params or None,
                json_body=json_body,
            )
            return {"success": True, "operation": req.operation_id, "result": result, "format": "json"}
    except Exception as e:
        return {"success": False, "operation": req.operation_id, "error": str(e)}


# =============================================================================
# Dashboard UI
# =============================================================================

@router.get("/ui")
async def admin_ui():
    """Serve the admin dashboard."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Admin UI not found")
