# Research Summary: Visual Agent Builder

**Project:** PACO Visual Agent Builder
**Researched:** 2026-02-03

---

## Key Findings

### Stack
- **@xyflow/react** (React Flow v12+) is the clear choice for node-based workflow editors
- **Zustand** (already in stack) is recommended for canvas state management
- **JSON** for workflow serialization with PostgreSQL JSONB
- **Template-based code generation** (Jinja2) for Claude Agent SDK output

### Features
**Table Stakes:** Canvas, agent config node, tool nodes, save/load, test chat, properties panel, undo/redo

**Primary Differentiators:**
1. Claude-native with MCP — only builder for Claude Agent SDK
2. Code export — vendor independence
3. Native Chatwoot/ElevenLabs — immediate channel deployment

**Anti-Features:** No "no-code" positioning, no real-time collaboration v1, no marketplace

### Architecture
- React Flow + Zustand on frontend
- FastAPI + Jinja2 code generation on backend
- PostgreSQL for workflow storage
- PM2 for deployment (existing infrastructure)

### Critical Pitfalls
1. React Flow state collision — use fully controlled mode with Zustand
2. Serialization round-trip failures — validate schema, version migrations
3. Code generation complexity — use IR pattern, limit initial node types
4. Connection validation gap — implement from day 1
5. Deployment state machine — explicit states, disable UI during transitions

---

## Recommended Stack

| Component | Technology | Confidence |
|-----------|------------|------------|
| Canvas | @xyflow/react ^12.x | MEDIUM |
| State | Zustand (existing) | HIGH |
| Serialization | JSON/PostgreSQL JSONB | HIGH |
| Code Gen | Jinja2 templates | HIGH |
| Deployment | PM2 (existing) | HIGH |

---

## Build Order

1. **Foundation** — DB schema, Zustand store, basic CRUD API
2. **Canvas Core** — React Flow, basic nodes, save/load
3. **Node Configuration** — Properties panel, MCP integration, validation
4. **Code Generation** — Templates, IR pattern, preview
5. **Deployment** — PM2 orchestration, status tracking
6. **Advanced** — Knowledge nodes, logic nodes, channels

---

## MVP Scope

**Must Have:**
- Drag-and-drop canvas with React Flow
- Agent configuration node (model, prompt, temperature)
- MCP tool nodes (connect existing MCP servers)
- Save/load workflows to PostgreSQL
- Test chat interface
- Properties panel
- Code export (Claude Agent SDK)
- Deploy button (PM2)

**Defer:**
- Knowledge base nodes (RAG)
- Logic/conditional nodes
- Multi-agent orchestration
- Version history

---

## Risk Assessment

| Phase | Risk Level | Primary Concern |
|-------|------------|-----------------|
| Canvas Foundation | LOW | State management pattern |
| Core Nodes | MEDIUM | Connection validation |
| Persistence | LOW | Round-trip testing |
| Code Generation | HIGH | Complexity explosion |
| Deployment | MEDIUM | State machine design |

**Highest Risk:** Phase 4 (Code Generation) — allocate extra time, establish IR pattern before implementing all node types.

---
*Research complete: 2026-02-03*
