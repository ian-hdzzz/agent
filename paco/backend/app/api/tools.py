"""
PACO Tools API

MCP server and tool registry management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession, OperatorUser
from app.db.models import McpServer, Tool

router = APIRouter(prefix="/tools", tags=["Tools"])


# =============================================================================
# Schemas
# =============================================================================


class McpServerResponse(BaseModel):
    """MCP Server response model."""

    id: str
    name: str
    description: Optional[str]
    transport: str
    url: Optional[str]
    proxy_url: Optional[str]
    proxy_config: Optional[Dict[str, Any]] = None
    command: Optional[str]
    status: str
    last_health_check: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class McpServerCreateRequest(BaseModel):
    """MCP Server creation request."""

    name: str
    description: Optional[str] = None
    transport: str = "http"
    url: Optional[str] = None
    proxy_url: Optional[str] = None
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    auth_config: Dict[str, Any] = {}


class McpServerUpdateRequest(BaseModel):
    """MCP Server update request."""

    name: Optional[str] = None
    description: Optional[str] = None
    transport: Optional[str] = None
    url: Optional[str] = None
    proxy_url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    auth_config: Optional[Dict[str, Any]] = None


class ToolResponse(BaseModel):
    """Tool response model."""

    id: str
    name: str
    description: Optional[str]
    mcp_server_id: Optional[str]
    mcp_server_name: Optional[str]
    input_schema: Dict[str, Any]
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ToolCreateRequest(BaseModel):
    """Tool creation request."""

    name: str
    description: Optional[str] = None
    mcp_server_id: Optional[str] = None
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}


class ToolUpdateRequest(BaseModel):
    """Tool update request."""

    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class ProxyConfig(BaseModel):
    """Proxy configuration for an MCP server or tool."""

    enabled: bool = True
    protocol: str = "http"  # http, https, socks5
    url: str
    auth: Optional[Dict[str, str]] = None  # {"username": "...", "password": "..."}
    bypass_patterns: List[str] = []


class ProxyConfigUpdateRequest(BaseModel):
    """Update proxy config for a server."""

    proxy_config: Optional[ProxyConfig] = None  # null = remove proxy


class ToolProxyOverrideRequest(BaseModel):
    """Set proxy override for a tool."""

    proxy_config: Optional[Dict[str, Any]] = None  # null = inherit from server


class ServerProxyResponse(BaseModel):
    """Full proxy config for a server including tool overrides."""

    server: Optional[Dict[str, Any]] = None
    tools: Dict[str, Optional[Dict[str, Any]]] = {}


class ProxyTestResponse(BaseModel):
    """Proxy connectivity test result."""

    success: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    proxy_ip: Optional[str] = None


# =============================================================================
# Helpers
# =============================================================================


def _server_response(server: McpServer) -> McpServerResponse:
    """Build an McpServerResponse from a model instance."""
    return McpServerResponse(
        id=str(server.id),
        name=server.name,
        description=server.description,
        transport=server.transport,
        url=server.url,
        proxy_url=server.proxy_url,
        proxy_config=server.proxy_config,
        command=server.command,
        status=server.status,
        last_health_check=server.last_health_check,
        created_at=server.created_at,
    )


def _httpx_transport(server: McpServer) -> Optional[httpx.AsyncHTTPTransport]:
    """Build an httpx transport with proxy if the server has one configured."""
    # New proxy_config takes priority
    if server.proxy_config and server.proxy_config.get("enabled") and server.proxy_config.get("url"):
        return httpx.AsyncHTTPTransport(proxy=server.proxy_config["url"])
    # Fallback to legacy proxy_url
    if server.proxy_url:
        return httpx.AsyncHTTPTransport(proxy=server.proxy_url)
    return None


# =============================================================================
# MCP Server Endpoints
# =============================================================================


@router.get("/servers", response_model=List[McpServerResponse])
async def list_mcp_servers(db: DbSession) -> List[McpServerResponse]:
    """List all MCP servers."""
    result = await db.execute(select(McpServer).order_by(McpServer.name))
    servers = result.scalars().all()

    return [_server_response(server) for server in servers]


@router.post("/servers", response_model=McpServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    request: McpServerCreateRequest,
    db: DbSession,
    _: AdminUser,
) -> McpServerResponse:
    """Create a new MCP server (admin only)."""
    # Check for duplicate name
    result = await db.execute(select(McpServer).where(McpServer.name == request.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MCP server '{request.name}' already exists",
        )

    server = McpServer(
        name=request.name,
        description=request.description,
        transport=request.transport,
        url=request.url,
        proxy_url=request.proxy_url,
        command=request.command,
        args=request.args,
        env=request.env,
        auth_config=request.auth_config,
        status="unknown",
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)

    return _server_response(server)


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: UUID,
    db: DbSession,
    _: AdminUser,
) -> None:
    """Delete an MCP server (admin only)."""
    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    await db.delete(server)
    await db.commit()


@router.put("/servers/{server_id}", response_model=McpServerResponse)
async def update_mcp_server(
    server_id: UUID,
    request: McpServerUpdateRequest,
    db: DbSession,
    _: AdminUser,
) -> McpServerResponse:
    """Update an MCP server (admin only)."""
    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    # Check for duplicate name if name is being changed
    if request.name is not None and request.name != server.name:
        dup = await db.execute(select(McpServer).where(McpServer.name == request.name))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"MCP server '{request.name}' already exists",
            )

    for field in ("name", "description", "transport", "url", "proxy_url", "command", "args", "env", "auth_config"):
        value = getattr(request, field)
        if value is not None:
            setattr(server, field, value)

    await db.commit()
    await db.refresh(server)

    return _server_response(server)


@router.post("/servers/{server_id}/health", response_model=McpServerResponse)
async def check_mcp_server_health(
    server_id: UUID,
    db: DbSession,
    _: OperatorUser,
) -> McpServerResponse:
    """Check MCP server health and update status."""
    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    # Only check HTTP transport servers
    if server.transport == "http" and server.url:
        try:
            transport = _httpx_transport(server)
            async with httpx.AsyncClient(timeout=10.0, transport=transport) as client:
                # Try to get tools list as health check
                response = await client.post(
                    f"{server.url}/tools/list",
                    json={},
                )
                if response.status_code == 200:
                    server.status = "online"
                else:
                    server.status = "error"
        except Exception:
            server.status = "offline"
    else:
        server.status = "unknown"

    server.last_health_check = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(server)

    return _server_response(server)


@router.get("/servers/{server_id}/proxy", response_model=ServerProxyResponse)
async def get_server_proxy_config(
    server_id: UUID,
    db: DbSession,
) -> ServerProxyResponse:
    """Get full proxy config for a server including tool overrides."""
    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")

    # Get tool overrides
    result = await db.execute(
        select(Tool).where(
            Tool.mcp_server_id == server_id,
            Tool.proxy_config.isnot(None),
        )
    )
    tools_with_overrides = result.scalars().all()
    tool_overrides = {t.name: t.proxy_config for t in tools_with_overrides}

    return ServerProxyResponse(
        server=server.proxy_config,
        tools=tool_overrides,
    )


@router.get("/servers/by-name/{server_name}/proxy", response_model=ServerProxyResponse)
async def get_server_proxy_config_by_name(
    server_name: str,
    db: DbSession,
) -> ServerProxyResponse:
    """Get proxy config by server name (used by MCP servers themselves)."""
    result = await db.execute(select(McpServer).where(McpServer.name == server_name))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server '{server_name}' not found")

    result = await db.execute(
        select(Tool).where(
            Tool.mcp_server_id == server.id,
            Tool.proxy_config.isnot(None),
        )
    )
    tools_with_overrides = result.scalars().all()
    tool_overrides = {t.name: t.proxy_config for t in tools_with_overrides}

    return ServerProxyResponse(
        server=server.proxy_config,
        tools=tool_overrides,
    )


@router.put("/servers/{server_id}/proxy", response_model=McpServerResponse)
async def update_server_proxy_config(
    server_id: UUID,
    request: ProxyConfigUpdateRequest,
    db: DbSession,
    _: AdminUser,
) -> McpServerResponse:
    """Update server proxy config and notify the MCP server."""
    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")

    server.proxy_config = request.proxy_config.model_dump() if request.proxy_config else None
    await db.commit()
    await db.refresh(server)

    # Notify MCP server to reload config
    if server.transport == "http" and server.url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{server.url}/reload-config")
        except Exception:
            pass  # Best-effort notification

    return _server_response(server)


@router.post("/servers/{server_id}/proxy/test", response_model=ProxyTestResponse)
async def test_server_proxy(
    server_id: UUID,
    db: DbSession,
    _: OperatorUser,
) -> ProxyTestResponse:
    """Test proxy connectivity for a server."""
    import time

    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")

    if not server.proxy_config or not server.proxy_config.get("enabled"):
        return ProxyTestResponse(success=False, error="No proxy configured")

    proxy_url = server.proxy_config.get("url", "")
    if not proxy_url:
        return ProxyTestResponse(success=False, error="No proxy URL configured")

    try:
        start = time.monotonic()
        transport = httpx.AsyncHTTPTransport(proxy=proxy_url)
        async with httpx.AsyncClient(timeout=10.0, transport=transport) as client:
            resp = await client.get("https://httpbin.org/ip")
            latency = (time.monotonic() - start) * 1000
            data = resp.json()
            return ProxyTestResponse(
                success=True,
                latency_ms=round(latency, 1),
                proxy_ip=data.get("origin"),
            )
    except Exception as e:
        return ProxyTestResponse(success=False, error=str(e))


@router.post("/servers/{server_id}/sync", response_model=List[ToolResponse])
async def sync_tools_from_server(
    server_id: UUID,
    db: DbSession,
    _: AdminUser,
) -> List[ToolResponse]:
    """Sync tools from an MCP server (admin only)."""
    result = await db.execute(select(McpServer).where(McpServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    if server.transport != "http" or not server.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only sync tools from HTTP MCP servers",
        )

    try:
        transport = _httpx_transport(server)
        async with httpx.AsyncClient(timeout=30.0, transport=transport) as client:
            response = await client.post(
                f"{server.url}/tools/list",
                json={},
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch tools from MCP server: {e}",
        )

    tools_data = data.get("tools", [])
    synced_tools = []

    for tool_data in tools_data:
        tool_name = tool_data.get("name")
        if not tool_name:
            continue

        # Check if tool exists
        result = await db.execute(
            select(Tool).where(
                Tool.name == tool_name,
                Tool.mcp_server_id == server.id,
            )
        )
        tool = result.scalar_one_or_none()

        if tool:
            # Update existing
            tool.description = tool_data.get("description")
            tool.input_schema = tool_data.get("inputSchema", {})
        else:
            # Create new
            tool = Tool(
                name=tool_name,
                description=tool_data.get("description"),
                mcp_server_id=server.id,
                input_schema=tool_data.get("inputSchema", {}),
                is_enabled=True,
            )
            db.add(tool)

        await db.commit()
        await db.refresh(tool)

        synced_tools.append(
            ToolResponse(
                id=str(tool.id),
                name=tool.name,
                description=tool.description,
                mcp_server_id=str(server.id),
                mcp_server_name=server.name,
                input_schema=tool.input_schema,
                is_enabled=tool.is_enabled,
                created_at=tool.created_at,
            )
        )

    return synced_tools


# =============================================================================
# Tool Endpoints
# =============================================================================


@router.get("", response_model=List[ToolResponse])
async def list_tools(
    db: DbSession,
    server_id: Optional[UUID] = None,
    enabled_only: bool = False,
) -> List[ToolResponse]:
    """List all tools, optionally filtered by MCP server."""
    query = select(Tool).order_by(Tool.name)

    if server_id:
        query = query.where(Tool.mcp_server_id == server_id)

    if enabled_only:
        query = query.where(Tool.is_enabled == True)

    result = await db.execute(query)
    tools = result.scalars().all()

    # Get server names
    server_ids = {t.mcp_server_id for t in tools if t.mcp_server_id}
    server_names = {}
    if server_ids:
        result = await db.execute(
            select(McpServer).where(McpServer.id.in_(server_ids))
        )
        for server in result.scalars().all():
            server_names[server.id] = server.name

    return [
        ToolResponse(
            id=str(tool.id),
            name=tool.name,
            description=tool.description,
            mcp_server_id=str(tool.mcp_server_id) if tool.mcp_server_id else None,
            mcp_server_name=server_names.get(tool.mcp_server_id),
            input_schema=tool.input_schema,
            is_enabled=tool.is_enabled,
            created_at=tool.created_at,
        )
        for tool in tools
    ]


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(tool_id: UUID, db: DbSession) -> ToolResponse:
    """Get tool details by ID."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool {tool_id} not found",
        )

    # Get server name
    server_name = None
    if tool.mcp_server_id:
        result = await db.execute(
            select(McpServer).where(McpServer.id == tool.mcp_server_id)
        )
        server = result.scalar_one_or_none()
        if server:
            server_name = server.name

    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        mcp_server_id=str(tool.mcp_server_id) if tool.mcp_server_id else None,
        mcp_server_name=server_name,
        input_schema=tool.input_schema,
        is_enabled=tool.is_enabled,
        created_at=tool.created_at,
    )


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    request: ToolCreateRequest,
    db: DbSession,
    _: AdminUser,
) -> ToolResponse:
    """Create a new tool (admin only)."""
    # Validate MCP server if provided
    mcp_server_id = None
    server_name = None
    if request.mcp_server_id:
        mcp_server_id = UUID(request.mcp_server_id)
        result = await db.execute(select(McpServer).where(McpServer.id == mcp_server_id))
        server = result.scalar_one_or_none()
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP server {request.mcp_server_id} not found",
            )
        server_name = server.name

    tool = Tool(
        name=request.name,
        description=request.description,
        mcp_server_id=mcp_server_id,
        input_schema=request.input_schema,
        output_schema=request.output_schema,
        is_enabled=True,
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)

    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        mcp_server_id=str(tool.mcp_server_id) if tool.mcp_server_id else None,
        mcp_server_name=server_name,
        input_schema=tool.input_schema,
        is_enabled=tool.is_enabled,
        created_at=tool.created_at,
    )


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    request: ToolUpdateRequest,
    db: DbSession,
    _: AdminUser,
) -> ToolResponse:
    """Update a tool (admin only)."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool {tool_id} not found",
        )

    if request.description is not None:
        tool.description = request.description

    if request.input_schema is not None:
        tool.input_schema = request.input_schema

    if request.is_enabled is not None:
        tool.is_enabled = request.is_enabled

    await db.commit()
    await db.refresh(tool)

    # Get server name
    server_name = None
    if tool.mcp_server_id:
        result = await db.execute(
            select(McpServer).where(McpServer.id == tool.mcp_server_id)
        )
        server = result.scalar_one_or_none()
        if server:
            server_name = server.name

    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        mcp_server_id=str(tool.mcp_server_id) if tool.mcp_server_id else None,
        mcp_server_name=server_name,
        input_schema=tool.input_schema,
        is_enabled=tool.is_enabled,
        created_at=tool.created_at,
    )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: UUID,
    db: DbSession,
    _: AdminUser,
) -> None:
    """Delete a tool (admin only)."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool {tool_id} not found",
        )

    await db.delete(tool)
    await db.commit()


@router.put("/{tool_id}/proxy")
async def update_tool_proxy_override(
    tool_id: UUID,
    request: ToolProxyOverrideRequest,
    db: DbSession,
    _: AdminUser,
) -> ToolResponse:
    """Set or clear proxy override for a specific tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")

    tool.proxy_config = request.proxy_config
    await db.commit()
    await db.refresh(tool)

    # Notify parent MCP server to reload
    if tool.mcp_server_id:
        result = await db.execute(select(McpServer).where(McpServer.id == tool.mcp_server_id))
        server = result.scalar_one_or_none()
        if server and server.transport == "http" and server.url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(f"{server.url}/reload-config")
            except Exception:
                pass

    server_name = None
    if tool.mcp_server_id:
        result = await db.execute(select(McpServer).where(McpServer.id == tool.mcp_server_id))
        srv = result.scalar_one_or_none()
        if srv:
            server_name = srv.name

    return ToolResponse(
        id=str(tool.id),
        name=tool.name,
        description=tool.description,
        mcp_server_id=str(tool.mcp_server_id) if tool.mcp_server_id else None,
        mcp_server_name=server_name,
        input_schema=tool.input_schema,
        is_enabled=tool.is_enabled,
        created_at=tool.created_at,
    )
