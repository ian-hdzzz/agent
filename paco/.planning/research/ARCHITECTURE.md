# Architecture: Visual Agent Builder

**Project:** PACO Visual Agent Builder
**Researched:** 2026-02-03
**Confidence:** MEDIUM

---

## System Overview

```
+------------------------------------------------------------------+
|                         PACO FRONTEND                             |
|  +----------------+    +-----------------+    +-----------------+ |
|  | Node Palette   |    | Canvas          |    | Properties      | |
|  | (drag source)  |--->| (React Flow)    |<-->| Panel           | |
|  +----------------+    +-----------------+    +-----------------+ |
|           v                       v                     v         |
|  +---------------------------------------------------------------+|
|  |              Workflow State (Zustand Store)                   ||
|  |  nodes: Node[], edges: Edge[], metadata: WorkflowMeta         ||
|  +---------------------------------------------------------------+|
+------------------------------------------------------------------+
                              |
                              | REST API
                              v
+------------------------------------------------------------------+
|                         PACO BACKEND                              |
|  +------------------+    +------------------+    +---------------+|
|  | Workflow CRUD    |    | Code Generator   |    | Deploy Orch.  ||
|  | (FastAPI)        |--->| (Jinja2)         |--->| (PM2 Client)  ||
|  +------------------+    +------------------+    +---------------+|
+------------------------------------------------------------------+
```

## Component Boundaries

### Frontend Layer

| Component | Responsibility | Interface |
|-----------|---------------|-----------|
| **Canvas (React Flow)** | Visual node/edge rendering, drag-drop | onNodesChange, onEdgesChange |
| **Node Palette** | Available node types, drag source | Drag events |
| **Properties Panel** | Node configuration UI | Node data updates |
| **Zustand Store** | Single source of truth | nodes, edges, actions |

### Backend Layer

| Component | Responsibility | Interface |
|-----------|---------------|-----------|
| **Workflow API** | CRUD for workflows | REST endpoints |
| **Code Generator** | Transform workflow JSON to SDK code | generate(workflow) -> code |
| **Deployment Orchestrator** | Manage agent lifecycle | deploy/undeploy/restart |

## Data Structures

### Node Data Model

```typescript
interface WorkflowNode {
  id: string;
  type: 'agent' | 'tool' | 'knowledge' | 'logic' | 'channel';
  position: { x: number; y: number };
  data: NodeData;
}

interface AgentNodeData {
  type: 'agent';
  name: string;
  systemPrompt: string;
  model: string;
  temperature: number;
  maxTokens: number;
}

interface ToolNodeData {
  type: 'tool';
  mcpServerId: string;
  selectedTools: string[];
}
```

### Database Schema

```sql
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft',
    deployed_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE workflow_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    definition JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Data Flow

### Save Workflow
1. Frontend serializes store to WorkflowDefinition
2. POST /api/workflows/{id} with definition JSON
3. Backend validates schema (Pydantic)
4. Backend increments version, saves to PostgreSQL
5. Returns { id, version, updatedAt }

### Deploy Workflow
1. POST /api/workflows/{id}/deploy
2. Load workflow from DB, validate
3. Code Generator transforms to SDK code
4. Write to /agents/{workflow_id}/agent.ts
5. PM2 deploys process
6. Update workflow status

## Code Generation Architecture

```
Workflow Definition (JSON)
        |
        v
+------------------+
| Template Loader  |  Load base template
+------------------+
        |
        v
+------------------+
| Node Processors  |  Process each node type
+------------------+
        |
        v
+------------------+
| Code Emitter     |  Render final code (Jinja2)
+------------------+
        |
        v
Generated TypeScript/Python code
```

## Build Order (Dependencies)

1. **Phase: Foundation** — DB schema + Zustand store + basic CRUD API
2. **Phase: Canvas Core** — React Flow + basic nodes + save/load
3. **Phase: Node Config** — Properties panel + MCP integration + validation
4. **Phase: Code Gen** — Template engine + generators + preview
5. **Phase: Deployment** — PM2 orchestration + status tracking
6. **Phase: Advanced** — Knowledge nodes, logic nodes, channels

---
*Architecture research: 2026-02-03*
