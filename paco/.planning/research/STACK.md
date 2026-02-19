# Technology Stack: Visual Agent Builder

**Project:** PACO Visual Agent Builder
**Researched:** 2026-02-03
**Overall Confidence:** MEDIUM

---

## Executive Summary

For building a visual workflow/agent builder integrated into an existing Next.js + FastAPI stack:

- **@xyflow/react** for the node-based canvas - industry standard, mature, well-documented
- **Zustand** for workflow editor state - already in stack, perfect fit for complex editor state
- **JSON** for workflow serialization - flexible, versionable, queryable in PostgreSQL
- **Template-based code generation** with Jinja2/Handlebars for generating Claude Agent SDK code

## Recommended Stack

### Visual Canvas

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| **@xyflow/react** | ^12.x | Node-based workflow editor | MEDIUM |

**Why @xyflow/react:**
- React Flow was rebranded to XYFlow in 2024, now published as `@xyflow/react`
- De facto standard for node-based editors (used by n8n, Langflow, Flowise, BuildShip)
- Excellent TypeScript support out of the box
- Built-in features: pan/zoom, node selection, edge routing, minimap
- Active maintenance with regular releases

### State Management

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| **zustand** | ^4.5+ (existing) | Workflow editor state | HIGH |

**Why Zustand:**
- Already in your stack (`zustand: ^4.5.0` in package.json)
- Perfect for complex editor state: nodes, edges, selection, history
- React Flow examples use Zustand extensively
- Minimal boilerplate, easy to add undo/redo with middleware

### Workflow Serialization

| Format | Purpose | Confidence |
|--------|---------|------------|
| **JSON** | Workflow persistence | HIGH |

**Why JSON:**
- Native PostgreSQL JSON/JSONB support with indexing
- Easy versioning and diffing
- Direct serialization from React Flow state
- Queryable (find workflows using tool X)

### Code Generation

| Technology | Version | Purpose | Confidence |
|------------|---------|---------|------------|
| **Jinja2** | existing | Backend code generation templates | HIGH |
| **Handlebars** | ^4.7.x | Frontend code preview | MEDIUM |

**Recommended Approach: Template-Based Generation**
- Templates for 90% of generation needs
- Predictable output, easy to maintain
- Fast generation

### Supporting Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **@xyflow/react** | ^12.x | Core canvas |
| **zustand** | ^4.5.x | State management (existing) |
| **immer** | ^10.x | Immutable state helpers |
| **nanoid** | ^5.x | ID generation |
| **zod** | ^3.x | Workflow schema validation |

## What NOT to Use

| Technology | Why Avoid |
|------------|-----------|
| **react-flow-renderer** | Deprecated package name, use @xyflow/react |
| **Redux** | Overkill, Zustand already in stack |
| **GraphQL for workflow storage** | REST is simpler, no benefit |
| **MongoDB for workflows** | PostgreSQL JSONB is sufficient |
| **YAML for serialization** | JSON is superior for this use case |
| **LLM for code generation** | Unpredictable, templates are deterministic |

## Installation

```bash
cd frontend
npm install @xyflow/react nanoid zod immer
```

---
*Stack research: 2026-02-03*
