# Phase 5: MCP Tool Integration - Research

**Date:** 2026-02-04
**Status:** Complete (infrastructure already exists)

## Overview

Phase 5 connects the visual builder to PACO's existing MCP server registry. The backend infrastructure is fully implemented - this phase focuses on frontend integration.

## Existing Backend Infrastructure (COMPLETE)

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tools/servers` | GET | List all MCP servers |
| `/api/tools?server_id=xxx` | GET | List tools by server |
| `/api/tools/servers/{id}/sync` | POST | Sync tools from server |
| `/api/tools/servers/{id}/health` | POST | Check server health |

### Database Models

**McpServer** (mcp_servers table):
- `id`: UUID
- `name`: string (unique)
- `description`: text
- `transport`: string (stdio/sse/http)
- `url`: string (for SSE/HTTP)
- `command`: text (for stdio)
- `args`: JSONB (for stdio)
- `env`: JSONB
- `status`: string (online/offline/error/unknown)
- `last_health_check`: timestamp

**Tool** (tools table):
- `id`: UUID
- `name`: string
- `description`: text
- `mcp_server_id`: UUID (FK)
- `input_schema`: JSONB
- `is_enabled`: boolean

### API Response Types (frontend/lib/api.ts)

```typescript
interface McpServer {
  id: string;
  name: string;
  description: string | null;
  transport: string;
  url: string | null;
  command: string | null;
  status: string;
  last_health_check: string | null;
  created_at: string;
}

interface Tool {
  id: string;
  name: string;
  description: string | null;
  mcp_server_id: string | null;
  mcp_server_name: string | null;
  input_schema: Record<string, any>;
  is_enabled: boolean;
  created_at: string;
}
```

## Existing Frontend Infrastructure

### API Client Methods (frontend/lib/api.ts)

```typescript
api.getMcpServers()                // List all servers
api.getTools(serverId?: string)    // List tools, optionally filtered
api.createMcpServer(data)          // Create new server
api.deleteMcpServer(id)            // Delete server
api.syncToolsFromServer(serverId)  // Sync tools from server
api.checkMcpServerHealth(id)       // Check health
```

### Component Library (frontend/components/builder/library.tsx)

Currently has static MCP server templates:
- Stdio Server (npx example)
- SSE Server (URL example)

**Gap:** Does not fetch from API, only shows templates.

### McpServerNode Component (frontend/components/builder/nodes.tsx)

Renders MCP server config with:
- Server type badge (STDIO/SSE)
- Command/URL display
- "Tools discovered at runtime" placeholder

**Gap:** No tool selection UI, no connection to PACO registry.

### Properties Panel (frontend/components/builder/properties-panel/index.tsx)

Currently:
- Agent nodes: Full form with AgentConfigForm
- Other nodes: Generic label/description fields

**Gap:** No MCP server properties form.

### Store (frontend/components/builder/store.tsx)

MCP server handling exists:
- `isMcpServerComponent()` type guard
- Creates standalone nodes
- Creates `mcp-connection` edges to agents
- Blue edge color for MCP connections

**Gap:** No tool selection persistence in node config.

### Type System (frontend/types/datamodel.ts)

```typescript
interface McpServerConfig {
  name?: string;
  serverType?: McpServerType;  // 'stdio' | 'sse' | 'http'
  command?: string;
  args?: string[];
  url?: string;
  headers?: Record<string, string>;
  env?: Record<string, string>;
  enabledTools?: string[];  // <-- Exists but not wired up
}
```

## What Phase 5 Builds

### Plan 05-01: Connect MCP Node to PACO Registry

1. Update library to fetch MCP servers from API
2. Create MCP server config form for properties panel
3. Wire form to node updates

### Plan 05-02: Tool Selection UI

1. Fetch tools from API for selected server
2. Tool selection checkboxes
3. Persist enabledTools in node config
4. Update node display to show selected tools

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Fetch servers in library on mount | Keep library dynamic, show actual PACO registry |
| Tool selection via checkboxes | Simple, clear UI - matches n8n pattern |
| Store tool IDs in enabledTools[] | Allows partial tool selection |
| Sync button in properties panel | Let user refresh tools from server |

## No Additional Research Needed

Backend is complete. Frontend patterns are established. Proceed with implementation.
