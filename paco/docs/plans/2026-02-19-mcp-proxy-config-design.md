# MCP Proxy Configuration Design

**Date:** 2026-02-19
**Status:** Approved
**Author:** Claude Opus 4.6 + Fernando

## Problem

Paco MCP servers need configurable proxy support for:
- IP whitelisting (CEA API only accepts requests from specific IPs)
- Geographic/regulatory compliance (government APIs requiring Mexican IP origin)
- Multi-proxy routing (different tools/servers through different proxies)

Current state: CEA tools read `CEA_PROXY_URL` from environment variables at container startup. Changing proxy requires Docker Compose restart. Only a flat `proxy_url` string exists on the `mcp_servers` table.

## Decision

**Approach A: Config Endpoint + API-Triggered Reload**

MCP servers expose `/reload-config` and `/proxy-config` endpoints. Backend pushes config changes to MCP servers via HTTP. Zero downtime, per-tool granularity, event-driven.

Alternatives considered:
- **PM2 Restart:** Simpler but requires process restart and has no per-tool granularity.
- **Backend Proxy Gateway:** Maximum centralization but adds latency (extra hop) and creates a single point of failure.
- **Sidecar Proxy (Envoy):** Enterprise gold standard but overkill for current scale.

## Architecture

```
UI (save config) → Backend (store in DB) → POST /reload-config on MCP server
                                           → MCP server fetches config from backend
                                           → Updates in-memory cache
                                           → Tool calls use resolved proxy
```

Config resolution: Tool-level override > Server-level config > Direct connection (no proxy).

## Data Model

### mcp_servers table changes

Replace flat `proxy_url: String(500)` with `proxy_config: JSONB`:

```json
{
  "enabled": true,
  "protocol": "http",
  "url": "http://squid:3128",
  "auth": {
    "username": "user",
    "password": "encrypted-value"
  },
  "bypass_patterns": [
    "*.internal.local",
    "10.0.0.*"
  ]
}
```

The existing `proxy_url` column is kept for backward compatibility during migration, then removed.

### tools table changes

Add `proxy_config: JSONB` (nullable, default null):

```json
// Override with custom proxy:
{
  "enabled": true,
  "protocol": "socks5",
  "url": "socks5://proxy-b:1080"
}

// Explicitly disable proxy for this tool:
{
  "enabled": false
}

// Inherit from MCP server (default):
null
```

### Resolution logic

```
function resolveProxy(toolName, serverConfig, toolOverrides):
    toolConfig = toolOverrides[toolName]
    if toolConfig is not null:
        if toolConfig.enabled == false:
            return null  // direct connection
        return toolConfig  // use tool-specific proxy
    return serverConfig  // inherit from server (may be null = direct)
```

## Backend API

### New endpoints

```
PUT  /api/tools/servers/{id}/proxy       Update server proxy config
GET  /api/tools/servers/{id}/proxy       Get resolved proxy config (server + tools)
POST /api/tools/servers/{id}/proxy/test  Test proxy connectivity
PUT  /api/tools/{id}/proxy               Set/clear tool proxy override
```

### Modified endpoints

```
PUT  /api/tools/servers/{id}             Includes proxy_config in update schema
POST /api/tools/servers/{id}/health      Uses proxy_config for health check requests
POST /api/tools/servers/{id}/sync        Uses proxy_config for tool sync requests
```

### Config push flow

1. Admin saves proxy config via `PUT /api/tools/servers/{id}/proxy`
2. Backend stores `proxy_config` in `mcp_servers` table
3. Backend calls `POST http://{mcp-server-internal-url}/reload-config`
4. MCP server fetches fresh config from `GET http://paco-backend:8000/api/tools/servers/{id}/proxy`
5. Returns success/failure to frontend

### Proxy test endpoint

`POST /api/tools/servers/{id}/proxy/test`:
- Makes a test HTTP request through the configured proxy
- Returns: latency, success/failure, visible IP at destination
- Used by UI "Test Connection" button

## MCP Server Changes

### Shared proxy module

A reusable TypeScript module importable by any MCP server:

```typescript
// packages/proxy-config/src/index.ts

interface ProxyConfig {
  enabled: boolean;
  protocol: "http" | "https" | "socks5";
  url: string;
  auth?: { username: string; password: string };
  bypass_patterns?: string[];
}

interface ServerProxyConfig {
  server: ProxyConfig | null;
  tools: Record<string, ProxyConfig | null>;
}

class ProxyConfigManager {
  private config: ServerProxyConfig;
  private backendUrl: string;
  private serverName: string;

  async initialize(): Promise<void>;
  async reload(): Promise<void>;
  getProxyForTool(toolName: string): ProxyConfig | null;
  getDispatcherForTool(toolName: string): Dispatcher | null;
}
```

### New Express endpoints on each MCP server

```
POST /reload-config  Triggers config re-fetch from backend
GET  /proxy-status   Returns current proxy config (for debugging)
```

### fetchWithRetry changes

Before (hardcoded env var):
```typescript
const PROXY_URL = process.env.CEA_PROXY_URL || null;
if (PROXY_URL && url.includes("ceaqueretaro.gob.mx")) { ... }
```

After (dynamic from ProxyConfigManager):
```typescript
const dispatcher = proxyManager.getDispatcherForTool(toolName);
if (dispatcher) {
  response = await undiciFetch(url, { ...options, dispatcher });
} else {
  response = await fetch(url, options);
}
```

### Startup sequence

1. MCP server starts, reads `PACO_BACKEND_URL` env var
2. Calls `GET {PACO_BACKEND_URL}/api/tools/servers/{name}/proxy` to fetch initial config
3. Falls back to `CEA_PROXY_URL` env var if backend is unreachable (backward compat)
4. Caches config in memory
5. Ready to serve tool calls with proxy routing

## Frontend UI

### Enhanced MCP Server modal - Proxy section

The existing MCP server create/edit modal gets a new "Proxy Configuration" section:

- Enable/disable toggle
- Protocol selector: HTTP/HTTPS or SOCKS5
- Proxy URL input with validation
- Optional auth fields (username/password)
- Bypass patterns (comma-separated)
- "Test Connection" button with latency display
- Per-tool override table showing each tool with Inherit/None/Custom dropdown

### "Save & Apply" behavior

- Saves proxy_config to DB via API
- Triggers `/reload-config` on the MCP server
- Shows success/failure toast notification
- No Docker Compose restart needed

## Migration

### Database migration (Alembic)

1. Add `proxy_config` JSONB column to `mcp_servers` (nullable, default null)
2. Add `proxy_config` JSONB column to `tools` (nullable, default null)
3. Migrate existing `proxy_url` values into new `proxy_config` format
4. Keep `proxy_url` column temporarily for rollback safety
5. Drop `proxy_url` in a follow-up migration

### MCP server backward compatibility

- If `PACO_BACKEND_URL` is not set, fall back to `CEA_PROXY_URL` env var
- Existing docker-compose env vars continue to work during transition
- New proxy module is opt-in per MCP server

## Testing

- Unit tests for proxy resolution logic (inheritance, override, bypass patterns)
- Integration test: change proxy config via API, verify MCP server picks it up
- E2E test: UI save → backend → MCP server reload → tool call uses new proxy
- Proxy test endpoint validation (latency, connectivity)

## Protocols supported

- HTTP/HTTPS proxies (Squid, nginx, etc.) via undici ProxyAgent
- SOCKS5 proxies via socks-proxy-agent package
