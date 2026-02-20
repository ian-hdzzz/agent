# MCP Proxy Configuration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add configurable proxy support to MCP servers with per-tool override, dynamic reload via API (no Docker restart), and full UI management.

**Architecture:** Backend stores proxy config in PostgreSQL JSONB. MCP servers expose `/reload-config` endpoint. UI changes trigger backend DB update + push notification to MCP server. ProxyConfigManager class in each MCP server resolves per-tool proxy at runtime.

**Tech Stack:** FastAPI (backend), Next.js 14 + React 18 + Tailwind (frontend), TypeScript + Express + undici (MCP servers), PostgreSQL + Alembic (database), socks-proxy-agent (SOCKS5 support)

**Design doc:** `docs/plans/2026-02-19-mcp-proxy-config-design.md`

---

### Task 1: Database Migration - Add proxy_config columns

**Files:**
- Create: `paco/backend/alembic/versions/007_add_proxy_config.py`
- Modify: `paco/backend/app/db/models.py:61-90` (McpServer model)
- Modify: `paco/backend/app/db/models.py:93-120` (Tool model)

**Step 1: Create Alembic migration**

```python
# paco/backend/alembic/versions/007_add_proxy_config.py
"""add proxy_config to mcp_servers and tools

Adds proxy_config JSONB column to both mcp_servers and tools tables.
Migrates existing proxy_url values into the new format.

Revision ID: 007_add_proxy_config
Revises: 006_add_company_messages
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "007_add_proxy_config"
down_revision = "006_add_company_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add proxy_config JSONB to mcp_servers
    op.add_column(
        "mcp_servers",
        sa.Column("proxy_config", JSONB, nullable=True),
    )

    # Add proxy_config JSONB to tools
    op.add_column(
        "tools",
        sa.Column("proxy_config", JSONB, nullable=True),
    )

    # Migrate existing proxy_url values into proxy_config
    op.execute("""
        UPDATE mcp_servers
        SET proxy_config = jsonb_build_object(
            'enabled', true,
            'protocol', 'http',
            'url', proxy_url
        )
        WHERE proxy_url IS NOT NULL AND proxy_url != ''
    """)


def downgrade() -> None:
    op.drop_column("tools", "proxy_config")
    op.drop_column("mcp_servers", "proxy_config")
```

**Step 2: Update SQLAlchemy models**

In `paco/backend/app/db/models.py`, add `proxy_config` to McpServer (after line 79):

```python
proxy_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
```

In `paco/backend/app/db/models.py`, add `proxy_config` to Tool (after line 110):

```python
proxy_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
```

**Step 3: Run migration**

```bash
cd paco/backend && alembic upgrade head
```

Expected: Migration applies successfully, both columns added.

**Step 4: Commit**

```bash
git add paco/backend/alembic/versions/007_add_proxy_config.py paco/backend/app/db/models.py
git commit -m "feat: add proxy_config JSONB columns to mcp_servers and tools"
```

---

### Task 2: Backend API - Proxy config endpoints

**Files:**
- Modify: `paco/backend/app/api/tools.py`

**Step 1: Add proxy config Pydantic schemas**

Add these schemas after `ToolUpdateRequest` (around line 104) in `paco/backend/app/api/tools.py`:

```python
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
```

**Step 2: Add proxy config endpoints**

Add these endpoints after the existing server endpoints (after line 279) in `paco/backend/app/api/tools.py`:

```python
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
```

**Step 3: Update `_server_response` helper to include proxy_config**

Modify `_server_response` in `paco/backend/app/api/tools.py` to include proxy_config in response. Update `McpServerResponse` to add:

```python
proxy_config: Optional[Dict[str, Any]] = None
```

And in `_server_response` add:

```python
proxy_config=server.proxy_config,
```

**Step 4: Update existing `_httpx_transport` to use new proxy_config**

Replace the existing `_httpx_transport` function:

```python
def _httpx_transport(server: McpServer) -> Optional[httpx.AsyncHTTPTransport]:
    """Build an httpx transport with proxy if the server has one configured."""
    # New proxy_config takes priority
    if server.proxy_config and server.proxy_config.get("enabled") and server.proxy_config.get("url"):
        return httpx.AsyncHTTPTransport(proxy=server.proxy_config["url"])
    # Fallback to legacy proxy_url
    if server.proxy_url:
        return httpx.AsyncHTTPTransport(proxy=server.proxy_url)
    return None
```

**Step 5: Commit**

```bash
git add paco/backend/app/api/tools.py
git commit -m "feat: add proxy config API endpoints with test and per-tool override"
```

---

### Task 3: MCP Server Shared Proxy Module

**Files:**
- Create: `paco/mcp-servers/shared/proxy-config.ts`

**Step 1: Create the shared proxy config manager**

```typescript
// paco/mcp-servers/shared/proxy-config.ts

import { ProxyAgent, type Dispatcher } from "undici";

export interface ProxyConfig {
  enabled: boolean;
  protocol: "http" | "https" | "socks5";
  url: string;
  auth?: { username: string; password: string };
  bypass_patterns?: string[];
}

export interface ServerProxyConfig {
  server: ProxyConfig | null;
  tools: Record<string, ProxyConfig | null>;
}

export class ProxyConfigManager {
  private config: ServerProxyConfig = { server: null, tools: {} };
  private backendUrl: string;
  private serverName: string;

  constructor(serverName: string, backendUrl?: string) {
    this.serverName = serverName;
    this.backendUrl = backendUrl || process.env.PACO_BACKEND_URL || "http://paco-backend:8000";
  }

  /**
   * Fetch proxy config from the PACO backend.
   * Falls back to CEA_PROXY_URL env var if backend is unreachable.
   */
  async initialize(): Promise<void> {
    try {
      await this.fetchConfig();
      console.log(`[ProxyConfig] Loaded config from backend for ${this.serverName}`);
    } catch (err) {
      console.warn(`[ProxyConfig] Could not fetch from backend, checking env fallback: ${err}`);
      // Fallback to legacy env var
      const legacyUrl = process.env.CEA_PROXY_URL || null;
      if (legacyUrl) {
        this.config = {
          server: { enabled: true, protocol: "http", url: legacyUrl },
          tools: {},
        };
        console.log(`[ProxyConfig] Using legacy CEA_PROXY_URL: ${legacyUrl}`);
      }
    }
  }

  /**
   * Re-fetch config from backend. Called by POST /reload-config.
   */
  async reload(): Promise<void> {
    await this.fetchConfig();
    console.log(`[ProxyConfig] Config reloaded for ${this.serverName}`);
  }

  /**
   * Resolve proxy config for a specific tool.
   * Tool override > Server config > null (direct).
   */
  getProxyForTool(toolName: string): ProxyConfig | null {
    const toolOverride = this.config.tools[toolName];
    if (toolOverride !== undefined) {
      // Explicit override exists
      if (!toolOverride || !toolOverride.enabled) {
        return null; // Explicitly disabled
      }
      return toolOverride;
    }
    // Inherit from server
    if (this.config.server && this.config.server.enabled) {
      return this.config.server;
    }
    return null;
  }

  /**
   * Get an undici Dispatcher (ProxyAgent) for a specific tool.
   * Returns null if no proxy is configured.
   */
  getDispatcherForTool(toolName: string): Dispatcher | null {
    const proxy = this.getProxyForTool(toolName);
    if (!proxy) return null;

    let proxyUrl = proxy.url;
    // Embed auth into URL if provided
    if (proxy.auth?.username && proxy.auth?.password) {
      const urlObj = new URL(proxyUrl);
      urlObj.username = proxy.auth.username;
      urlObj.password = proxy.auth.password;
      proxyUrl = urlObj.toString();
    }

    return new ProxyAgent(proxyUrl);
  }

  /**
   * Check if a URL matches any bypass pattern.
   */
  shouldBypass(toolName: string, targetUrl: string): boolean {
    const proxy = this.getProxyForTool(toolName);
    if (!proxy?.bypass_patterns?.length) return false;

    return proxy.bypass_patterns.some((pattern) => {
      // Convert glob to regex: *.example.com -> .*\.example\.com
      const regex = new RegExp(
        "^" + pattern.replace(/\./g, "\\.").replace(/\*/g, ".*") + "$"
      );
      try {
        const hostname = new URL(targetUrl).hostname;
        return regex.test(hostname);
      } catch {
        return false;
      }
    });
  }

  /**
   * Get current config for debugging (GET /proxy-status).
   */
  getStatus(): ServerProxyConfig {
    return { ...this.config };
  }

  private async fetchConfig(): Promise<void> {
    const url = `${this.backendUrl}/api/tools/servers/by-name/${this.serverName}/proxy`;
    const response = await fetch(url, {
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    this.config = await response.json();
  }
}
```

**Step 2: Commit**

```bash
git add paco/mcp-servers/shared/proxy-config.ts
git commit -m "feat: add shared ProxyConfigManager for MCP servers"
```

---

### Task 4: Integrate Proxy Module into CEA Tools MCP Server

**Files:**
- Modify: `paco/mcp-servers/cea-tools/src/server.ts`

**Step 1: Import and initialize ProxyConfigManager**

At the top of `server.ts`, replace the hardcoded PROXY_URL:

Before (lines 18-24):
```typescript
import { ProxyAgent, fetch as undiciFetch } from "undici";

// Configuration
const CEA_API_BASE = ...
const PROXY_URL = process.env.CEA_PROXY_URL || null;
```

After:
```typescript
import { ProxyAgent, fetch as undiciFetch } from "undici";
import { ProxyConfigManager } from "../../shared/proxy-config.js";

// Configuration
const CEA_API_BASE = ...

// Dynamic proxy config (replaces hardcoded CEA_PROXY_URL)
const proxyManager = new ProxyConfigManager("cea-tools");
```

**Step 2: Update fetchWithRetry to accept toolName and use ProxyConfigManager**

Replace the existing `fetchWithRetry` function (lines 27-75):

```typescript
async function fetchWithRetry(
  url: string,
  options: {
    method?: string;
    headers?: Record<string, string>;
    body?: string;
  },
  toolName: string,
  maxRetries = 3,
  delayMs = 1000
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      let response: Response;
      const dispatcher = proxyManager.shouldBypass(toolName, url)
        ? null
        : proxyManager.getDispatcherForTool(toolName);

      if (dispatcher) {
        response = (await undiciFetch(url, {
          method: options.method || "GET",
          headers: options.headers,
          body: options.body,
          dispatcher,
          // @ts-ignore
          signal: AbortSignal.timeout(30000),
        })) as unknown as Response;
      } else {
        response = await fetch(url, {
          ...options,
          signal: AbortSignal.timeout(30000),
        });
      }

      if (!response.ok && attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, delayMs * attempt));
        continue;
      }

      return response;
    } catch (error) {
      lastError = error as Error;
      if (attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, delayMs * attempt));
      }
    }
  }

  throw lastError || new Error("Request failed after retries");
}
```

**Step 3: Update all tool call sites to pass toolName**

In the CallToolRequestSchema handler, update each `fetchWithRetry` call to include the tool name. For example:

```typescript
// get_deuda case:
const response = await fetchWithRetry(
  `${CEA_API_BASE}/InterfazGenericaGestionDeudaWS`,
  {
    method: "POST",
    headers: { "Content-Type": "text/xml;charset=UTF-8" },
    body: buildDeudaSOAP(contrato),
  },
  "get_deuda"  // <-- add toolName
);

// get_consumo case:
const response = await fetchWithRetry(
  `${CEA_API_BASE}/InterfazOficinaVirtualClientesWS`,
  {
    method: "POST",
    headers: { "Content-Type": "text/xml;charset=UTF-8" },
    body: buildConsumoSOAP(contrato, explotacion),
  },
  "get_consumo"  // <-- add toolName
);

// get_contract_details case:
const response = await fetchWithRetry(
  `${CEA_API_BASE}/InterfazGenericaContratacionWS`,
  {
    method: "POST",
    headers: { "Content-Type": "text/xml;charset=UTF-8" },
    body: buildContratoSOAP(contrato),
  },
  "get_contract_details"  // <-- add toolName
);
```

**Step 4: Add /reload-config and /proxy-status endpoints**

In the `main()` function, add these Express routes before `app.listen`:

```typescript
// Proxy config reload endpoint
app.post("/reload-config", async (_req, res) => {
  try {
    await proxyManager.reload();
    res.json({ status: "ok", message: "Config reloaded" });
  } catch (error) {
    res.status(500).json({
      status: "error",
      message: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

// Proxy status endpoint (for debugging)
app.get("/proxy-status", (_req, res) => {
  res.json(proxyManager.getStatus());
});
```

**Step 5: Initialize ProxyConfigManager in main()**

At the beginning of the `main()` function, add:

```typescript
async function main() {
  // Initialize proxy config from backend (with fallback to env var)
  await proxyManager.initialize();

  const app = express();
  // ... rest of existing code
}
```

**Step 6: Add PACO_BACKEND_URL to docker-compose.yml**

In `paco/docker-compose.yml`, add to the `cea-tools` service environment:

```yaml
cea-tools:
  environment:
    - CEA_API_URL=${CEA_API_URL:-}
    - CEA_API_USER=${CEA_API_USER:-}
    - CEA_API_PASSWORD=${CEA_API_PASSWORD:-}
    - CEA_PROXY_URL=${CEA_PROXY_URL:-}
    - PACO_BACKEND_URL=http://paco-backend:8000
```

**Step 7: Commit**

```bash
git add paco/mcp-servers/cea-tools/src/server.ts paco/docker-compose.yml
git commit -m "feat: integrate ProxyConfigManager into CEA tools MCP server"
```

---

### Task 5: Integrate Proxy Module into AGORA Tools MCP Server

**Files:**
- Modify: `paco/mcp-servers/agora-tools/src/server.ts`
- Modify: `paco/docker-compose.yml`

Follow the same pattern as Task 4 but for agora-tools:

**Step 1:** Import ProxyConfigManager and create instance with name `"agora-tools"`
**Step 2:** Initialize in main() function
**Step 3:** Add `/reload-config` and `/proxy-status` endpoints
**Step 4:** Add `PACO_BACKEND_URL=http://paco-backend:8000` to agora-tools environment in docker-compose.yml

Note: agora-tools uses direct PostgreSQL queries (not external HTTP APIs), so the proxy is mainly for future use when external integrations are added. The endpoints still need to exist for consistency.

**Step 5: Commit**

```bash
git add paco/mcp-servers/agora-tools/src/server.ts paco/docker-compose.yml
git commit -m "feat: integrate ProxyConfigManager into AGORA tools MCP server"
```

---

### Task 6: Frontend - API client updates

**Files:**
- Modify: `paco/frontend/lib/api.ts`

**Step 1: Update McpServer interface**

Add `proxy_config` to the `McpServer` interface (around line 1195):

```typescript
export interface McpServer {
  id: string;
  name: string;
  description: string | null;
  transport: string;
  url: string | null;
  command: string | null;
  status: string;
  proxy_config: ProxyConfig | null;  // <-- add
  last_health_check: string | null;
  created_at: string;
}
```

**Step 2: Add proxy-related interfaces**

Add after `UpdateMcpServerRequest` (around line 1252):

```typescript
export interface ProxyConfig {
  enabled: boolean;
  protocol: string;
  url: string;
  auth?: { username: string; password: string };
  bypass_patterns?: string[];
}

export interface ServerProxyResponse {
  server: ProxyConfig | null;
  tools: Record<string, ProxyConfig | null>;
}

export interface ProxyTestResponse {
  success: boolean;
  latency_ms: number | null;
  error: string | null;
  proxy_ip: string | null;
}
```

**Step 3: Add proxy_config to UpdateMcpServerRequest**

```typescript
export interface UpdateMcpServerRequest {
  // ... existing fields ...
  proxy_config?: ProxyConfig | null;
}
```

**Step 4: Add API methods to ApiClient class**

Add these methods (around line 210, after `updateMcpServer`):

```typescript
async getServerProxyConfig(serverId: string) {
  return this.request<ServerProxyResponse>(
    `/api/tools/servers/${serverId}/proxy`
  );
}

async updateServerProxyConfig(serverId: string, proxyConfig: ProxyConfig | null) {
  return this.request<McpServer>(`/api/tools/servers/${serverId}/proxy`, {
    method: "PUT",
    body: JSON.stringify({ proxy_config: proxyConfig }),
  });
}

async testServerProxy(serverId: string) {
  return this.request<ProxyTestResponse>(
    `/api/tools/servers/${serverId}/proxy/test`,
    { method: "POST" }
  );
}

async updateToolProxyOverride(toolId: string, proxyConfig: Record<string, any> | null) {
  return this.request<Tool>(`/api/tools/${toolId}/proxy`, {
    method: "PUT",
    body: JSON.stringify({ proxy_config: proxyConfig }),
  });
}
```

**Step 5: Commit**

```bash
git add paco/frontend/lib/api.ts
git commit -m "feat: add proxy config API methods and types to frontend client"
```

---

### Task 7: Frontend - Enhanced MCP Server Modal with Proxy Section

**Files:**
- Modify: `paco/frontend/app/tools/page.tsx`

**Step 1: Add proxy state to McpServerModal**

Add these state variables to `McpServerModal` (after line 53):

```typescript
// Proxy config state
const [proxyEnabled, setProxyEnabled] = useState(false);
const [proxyProtocol, setProxyProtocol] = useState<"http" | "socks5">("http");
const [proxyServerUrl, setProxyServerUrl] = useState("");
const [proxyUsername, setProxyUsername] = useState("");
const [proxyPassword, setProxyPassword] = useState("");
const [bypassPatterns, setBypassPatterns] = useState("");
const [testResult, setTestResult] = useState<{
  success: boolean;
  latency_ms?: number | null;
  error?: string | null;
  proxy_ip?: string | null;
} | null>(null);
const [testLoading, setTestLoading] = useState(false);
```

Initialize from existing server data (add to the McpServerModal function body):

```typescript
// Initialize proxy state from server data
useState(() => {
  if (server?.proxy_config) {
    setProxyEnabled(server.proxy_config.enabled ?? false);
    setProxyProtocol(server.proxy_config.protocol === "socks5" ? "socks5" : "http");
    setProxyServerUrl(server.proxy_config.url ?? "");
    setProxyUsername(server.proxy_config.auth?.username ?? "");
    setProxyPassword(server.proxy_config.auth?.password ?? "");
    setBypassPatterns((server.proxy_config.bypass_patterns ?? []).join(", "));
  }
});
```

**Step 2: Build proxy_config in handleSubmit**

Add proxy config construction before the mutation calls in `handleSubmit`:

```typescript
// Build proxy config
const proxyConfig = proxyEnabled
  ? {
      enabled: true,
      protocol: proxyProtocol,
      url: proxyServerUrl.trim(),
      ...(proxyUsername.trim()
        ? { auth: { username: proxyUsername.trim(), password: proxyPassword } }
        : {}),
      bypass_patterns: bypassPatterns
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean),
    }
  : null;
```

Include `proxy_config: proxyConfig` in both `createMutation.mutate()` and `updateMutation.mutate()` calls.

**Step 3: Add proxy test handler**

```typescript
async function handleTestProxy() {
  if (!server?.id) return;
  setTestLoading(true);
  setTestResult(null);
  try {
    const result = await api.testServerProxy(server.id);
    setTestResult(result);
  } catch (err: any) {
    setTestResult({ success: false, error: err.detail || "Test failed" });
  } finally {
    setTestLoading(false);
  }
}
```

**Step 4: Add proxy config UI section to the form**

Add this JSX after the Proxy URL input (replace lines 225-238, the old simple proxy input):

```tsx
{/* Proxy Configuration Section */}
{transport === "http" && (
  <div className="border border-border rounded-lg p-4 space-y-4">
    <div className="flex items-center justify-between">
      <h3 className="text-sm font-semibold text-foreground">
        Proxy Configuration
      </h3>
      <button
        type="button"
        onClick={() => setProxyEnabled(!proxyEnabled)}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
          proxyEnabled ? "bg-coral-500" : "bg-foreground-muted/30"
        )}
      >
        <span
          className={cn(
            "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
            proxyEnabled ? "translate-x-6" : "translate-x-1"
          )}
        />
      </button>
    </div>

    {proxyEnabled && (
      <>
        {/* Protocol */}
        <div className="flex items-center gap-4">
          <label className="text-sm text-foreground-muted">Protocol:</label>
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="radio"
              name="proxyProtocol"
              value="http"
              checked={proxyProtocol === "http"}
              onChange={() => setProxyProtocol("http")}
              className="accent-coral-500"
            />
            HTTP/HTTPS
          </label>
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="radio"
              name="proxyProtocol"
              value="socks5"
              checked={proxyProtocol === "socks5"}
              onChange={() => setProxyProtocol("socks5")}
              className="accent-coral-500"
            />
            SOCKS5
          </label>
        </div>

        {/* Proxy URL */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Proxy URL <span className="text-error">*</span>
          </label>
          <input
            type="text"
            value={proxyServerUrl}
            onChange={(e) => setProxyServerUrl(e.target.value)}
            placeholder={
              proxyProtocol === "socks5"
                ? "socks5://proxy:1080"
                : "http://proxy:3128"
            }
            className="input w-full"
          />
        </div>

        {/* Auth */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-foreground-muted mb-1">
              Username
            </label>
            <input
              type="text"
              value={proxyUsername}
              onChange={(e) => setProxyUsername(e.target.value)}
              placeholder="Optional"
              className="input w-full"
            />
          </div>
          <div>
            <label className="block text-sm text-foreground-muted mb-1">
              Password
            </label>
            <input
              type="password"
              value={proxyPassword}
              onChange={(e) => setProxyPassword(e.target.value)}
              placeholder="Optional"
              className="input w-full"
            />
          </div>
        </div>

        {/* Bypass */}
        <div>
          <label className="block text-sm text-foreground-muted mb-1">
            Bypass Patterns (comma-separated)
          </label>
          <input
            type="text"
            value={bypassPatterns}
            onChange={(e) => setBypassPatterns(e.target.value)}
            placeholder="*.internal.local, 10.0.0.*"
            className="input w-full"
          />
        </div>

        {/* Test Connection */}
        {isEdit && (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleTestProxy}
              disabled={testLoading || !proxyServerUrl.trim()}
              className="btn-ghost px-3 py-1.5 text-sm flex items-center gap-1.5"
            >
              {testLoading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Search className="w-3.5 h-3.5" />
              )}
              Test Connection
            </button>
            {testResult && (
              <span
                className={cn(
                  "text-sm",
                  testResult.success ? "text-success" : "text-error"
                )}
              >
                {testResult.success
                  ? `Connected (${testResult.latency_ms}ms) - IP: ${testResult.proxy_ip}`
                  : testResult.error}
              </span>
            )}
          </div>
        )}
      </>
    )}
  </div>
)}
```

**Step 5: Commit**

```bash
git add paco/frontend/app/tools/page.tsx
git commit -m "feat: add proxy configuration UI to MCP server modal"
```

---

### Task 8: Frontend - Per-Tool Proxy Override UI

**Files:**
- Modify: `paco/frontend/app/tools/page.tsx`

**Step 1: Add per-tool override section to ToolModal**

In the existing `ToolModal` component, add proxy override fields. Add state:

```typescript
const [proxyOverride, setProxyOverride] = useState<"inherit" | "none" | "custom">(
  tool?.proxy_config === null || tool?.proxy_config === undefined
    ? "inherit"
    : tool?.proxy_config?.enabled === false
    ? "none"
    : "custom"
);
const [toolProxyUrl, setToolProxyUrl] = useState(
  tool?.proxy_config?.url ?? ""
);
const [toolProxyProtocol, setToolProxyProtocol] = useState(
  tool?.proxy_config?.protocol ?? "http"
);
```

Add JSX after the "Is Enabled" toggle section:

```tsx
{/* Proxy Override */}
{isEdit && (
  <div className="border border-border rounded-lg p-3 space-y-3">
    <label className="block text-sm font-semibold text-foreground">
      Proxy Override
    </label>
    <select
      value={proxyOverride}
      onChange={(e) =>
        setProxyOverride(e.target.value as "inherit" | "none" | "custom")
      }
      className="input w-full"
    >
      <option value="inherit">Inherit from MCP Server</option>
      <option value="none">No Proxy (direct connection)</option>
      <option value="custom">Custom Proxy</option>
    </select>

    {proxyOverride === "custom" && (
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="radio"
              value="http"
              checked={toolProxyProtocol === "http"}
              onChange={() => setToolProxyProtocol("http")}
              className="accent-coral-500"
            />
            HTTP
          </label>
          <label className="flex items-center gap-1.5 text-sm">
            <input
              type="radio"
              value="socks5"
              checked={toolProxyProtocol === "socks5"}
              onChange={() => setToolProxyProtocol("socks5")}
              className="accent-coral-500"
            />
            SOCKS5
          </label>
        </div>
        <input
          type="text"
          value={toolProxyUrl}
          onChange={(e) => setToolProxyUrl(e.target.value)}
          placeholder="http://proxy:3128"
          className="input w-full"
        />
      </div>
    )}
  </div>
)}
```

**Step 2: Save proxy override on submit**

In the `handleSubmit` for ToolModal, after the existing update mutation, add proxy override save:

```typescript
// Save proxy override if changed
if (isEdit && tool) {
  let proxyConfig: Record<string, any> | null = null;
  if (proxyOverride === "none") {
    proxyConfig = { enabled: false };
  } else if (proxyOverride === "custom" && toolProxyUrl.trim()) {
    proxyConfig = {
      enabled: true,
      protocol: toolProxyProtocol,
      url: toolProxyUrl.trim(),
    };
  }
  // null = inherit (default)
  await api.updateToolProxyOverride(tool.id, proxyConfig);
}
```

**Step 3: Add proxy_config to Tool interface**

In `paco/frontend/lib/api.ts`, update the `Tool` interface:

```typescript
export interface Tool {
  id: string;
  name: string;
  description: string | null;
  mcp_server_id: string | null;
  mcp_server_name: string | null;
  input_schema: Record<string, any>;
  is_enabled: boolean;
  proxy_config: Record<string, any> | null;  // <-- add
  created_at: string;
}
```

And update `ToolResponse` in the backend to include `proxy_config`.

**Step 4: Commit**

```bash
git add paco/frontend/app/tools/page.tsx paco/frontend/lib/api.ts
git commit -m "feat: add per-tool proxy override UI in tool modal"
```

---

### Task 9: Backend - Include proxy_config in Tool responses

**Files:**
- Modify: `paco/backend/app/api/tools.py`

**Step 1: Add proxy_config to ToolResponse**

```python
class ToolResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    mcp_server_id: Optional[str]
    mcp_server_name: Optional[str]
    input_schema: Dict[str, Any]
    is_enabled: bool
    proxy_config: Optional[Dict[str, Any]] = None  # <-- add
    created_at: datetime

    class Config:
        from_attributes = True
```

**Step 2: Update all ToolResponse constructions**

In every place where `ToolResponse(...)` is constructed, add `proxy_config=tool.proxy_config`. There are 5 locations:
- `sync_tools_from_server` (line ~354)
- `list_tools` (line ~403)
- `get_tool` (line ~440)
- `create_tool` (line ~485)
- `update_tool` (line ~536)

**Step 3: Commit**

```bash
git add paco/backend/app/api/tools.py
git commit -m "feat: include proxy_config in tool API responses"
```

---

### Task 10: Docker Compose - Add PACO_BACKEND_URL and production overrides

**Files:**
- Modify: `paco/docker-compose.yml`
- Modify: `paco/docker-compose.prod.yml` (if exists)

**Step 1: Add PACO_BACKEND_URL to all MCP servers**

In `docker-compose.yml`, add to both cea-tools and agora-tools:

```yaml
environment:
  - PACO_BACKEND_URL=http://paco-backend:8000
```

**Step 2: Add depends_on for MCP servers → backend**

Since MCP servers now fetch config from backend on startup, add:

```yaml
cea-tools:
  depends_on:
    paco-backend:
      condition: service_started
  # ... existing config

agora-tools:
  depends_on:
    postgres:
      condition: service_healthy
    paco-backend:
      condition: service_started
  # ... existing config
```

**Step 3: Commit**

```bash
git add paco/docker-compose.yml paco/docker-compose.prod.yml
git commit -m "feat: add PACO_BACKEND_URL and startup dependencies for proxy config"
```

---

### Task 11: Integration Test - End-to-end proxy config flow

**Files:**
- Create: `paco/backend/tests/test_proxy_config.py`

**Step 1: Write test**

```python
"""Integration tests for proxy config API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_and_get_proxy_config(client: AsyncClient, admin_token: str):
    """Test setting and retrieving proxy config on an MCP server."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # List servers to get an ID
    resp = await client.get("/api/tools/servers", headers=headers)
    assert resp.status_code == 200
    servers = resp.json()
    if not servers:
        pytest.skip("No MCP servers registered")

    server_id = servers[0]["id"]

    # Set proxy config
    proxy_data = {
        "proxy_config": {
            "enabled": True,
            "protocol": "http",
            "url": "http://squid:3128",
            "bypass_patterns": ["*.internal.local"],
        }
    }
    resp = await client.put(
        f"/api/tools/servers/{server_id}/proxy",
        json=proxy_data,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["proxy_config"]["enabled"] is True
    assert data["proxy_config"]["url"] == "http://squid:3128"

    # Get full proxy config
    resp = await client.get(
        f"/api/tools/servers/{server_id}/proxy",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server"]["enabled"] is True

    # Clear proxy config
    resp = await client.put(
        f"/api/tools/servers/{server_id}/proxy",
        json={"proxy_config": None},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["proxy_config"] is None


@pytest.mark.asyncio
async def test_tool_proxy_override(client: AsyncClient, admin_token: str):
    """Test per-tool proxy override."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Get a tool
    resp = await client.get("/api/tools", headers=headers)
    assert resp.status_code == 200
    tools = resp.json()
    if not tools:
        pytest.skip("No tools registered")

    tool_id = tools[0]["id"]

    # Set tool proxy override
    resp = await client.put(
        f"/api/tools/{tool_id}/proxy",
        json={"proxy_config": {"enabled": False}},
        headers=headers,
    )
    assert resp.status_code == 200

    # Clear override
    resp = await client.put(
        f"/api/tools/{tool_id}/proxy",
        json={"proxy_config": None},
        headers=headers,
    )
    assert resp.status_code == 200
```

**Step 2: Commit**

```bash
git add paco/backend/tests/test_proxy_config.py
git commit -m "test: add integration tests for proxy config API"
```

---

### Task 12: Final verification and cleanup

**Step 1: Run backend tests**

```bash
cd paco/backend && python -m pytest tests/test_proxy_config.py -v
```

**Step 2: Verify frontend builds**

```bash
cd paco/frontend && npm run build
```

**Step 3: Verify MCP server compiles**

```bash
cd paco/mcp-servers/cea-tools && npx tsc --noEmit
```

**Step 4: Test the full flow manually**

1. Start the stack: `docker-compose up -d`
2. Login to PACO UI at localhost:3006
3. Go to Tools page
4. Edit cea-tools MCP server
5. Enable proxy, enter `http://squid:3128`, save
6. Click "Test Connection"
7. Verify the MCP server received the config: `curl http://localhost:3010/proxy-status`

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete MCP proxy configuration with UI, API, and dynamic reload"
```
