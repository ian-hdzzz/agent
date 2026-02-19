# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Users can visually design and deploy working Claude agents in minutes, not hours
**Current focus:** Phase 7 - Code Generation

## Current Position

Phase: 7 of 8 (Code Generation)
Plan: 3 of 4 in current phase
Status: In progress
Last activity: 2026-02-04 - Completed 07-03-PLAN.md

Progress: [███████████████░] 85%

## Performance Metrics

**Velocity:**
- Total plans completed: 17
- Average duration: 12 min
- Total execution time: 3.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3 | 32 min | 10.7 min |
| 02 | 2 | 20 min | 10 min |
| 03 | 1 | 12 min | 12 min |
| 04 | 3 | 61 min | 20.3 min |
| 05 | 2 | 34 min | 17 min |
| 06 | 3 | 30 min | 10 min |
| 07 | 3 | 12 min | 4 min |

**Recent Trend:**
- Last 5 plans: 10 min, 10 min, 5 min, 3 min, 4 min
- Trend: Phase 07 plans very efficient - well-defined specs from research

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Fork AutoGen Studio** - Get canvas, Zustand store, MCP UI, undo/redo for free; MIT licensed
- **Port Gatsby to Next.js** - PACO already uses Next.js; avoid framework mixing
- **Kept AutoGen provider strings** - Type guards use AutoGen Studio provider patterns temporarily; cleanup tracked in store.tsx TODO
- **Stub validation/test components** - ValidationErrors and TestDrawer are placeholders; full implementation deferred
- **RoundRobinGroupChat default** - Simpler team type used for default builder page (no model_client required)
- **Extended type system** - Maintained PACO types while adding AutoGen compatibility layer for builder
- **Centralized PROVIDERS constant** - AutoGen provider strings in guards.ts for easy future replacement
- **Height container strategy** - h-screen on layout main, h-full on page div for React Flow canvas containment
- **Builder navigation position** - Between Dashboard and Agents (overview -> build -> manage flow)
- **MCP servers as standalone nodes** - MCP servers render as standalone nodes connected to agents via edges, not embedded in agent config
- **Blue MCP connection edges** - rgb(59, 130, 246) distinguishes MCP connections from other edge types
- **Fixed sidebar over Drawer** - Figma/n8n pattern for properties panel, allows canvas visibility while editing
- **All parameters visible** - TopP, TopK, StopSequences in visible section, not collapsed
- **Model as string type** - Allows multi-provider and custom model IDs
- **JSON in config_yaml column** - Flow model's config_yaml column stores JSON despite name; Text type works for any format
- **User-scoped workflow names** - Duplicate workflow names allowed across users (scoped uniqueness)
- **URL workflow ID** - Use /builder?id=xxx for workflow context; standard web pattern enables sharing/bookmarking
- **Modal for new save** - Modal dialog asking for name/description on first save; prevents save without name
- **30-second auto-save interval** - Balance between data safety and API load
- **Silent auto-save errors** - Auto-save failures logged but not shown to user (too noisy)
- **Import clears workflow ID** - Imported workflow treated as new to prevent accidental overwrite
- **Conditional MCP field visibility** - Command/args shown only for stdio; URL shown only for sse/http
- **Templates vs Registry distinction** - Templates have "template" label; registry servers have Database icon, blue border, status badge
- **Tool selection via checkboxes** - Antd Checkbox.Group for multi-select tool selection
- **Tool count badge in node header** - Shows count only when tools selected (e.g., "2 Tools")
- **serverId links to PACO registry** - Enables tool fetching for registered MCP servers
- **Purple knowledge connection edges** - rgb(168, 85, 247) distinguishes knowledge connections
- **Orange logic connection edges** - rgb(249, 115, 22) distinguishes logic/flow connections
- **Non-blocking validation** - Validation errors shown but save allowed (warning message)
- **Click-to-select validation errors** - Clicking error in panel selects the node
- **Jest for testing** - Configured Jest with ts-jest for frontend TDD
- **Permission mode default 'acceptEdits'** - Sensible default for generated agents
- **IR transformation pattern** - Canvas nodes/edges -> Language-agnostic IR -> Code
- **Jinja2 for Python codegen** - Backend rendering ensures proper Python formatting
- **Monaco Editor for code preview** - Industry standard VS Code editor component
- **Inline IR type in api.ts** - Avoids circular dependency with code-generation module

### Source Material

AutoGen Studio cloned to `/tmp/autogen-temp/python/packages/autogen-studio/` for reference.

Key components ported in Phase 01:
- `frontend/components/builder/store.tsx` - Zustand store (733 lines, undo/redo)
- `frontend/components/builder/builder.tsx` - Main React Flow canvas
- `frontend/components/builder/nodes.tsx` - Custom node types with PACO icons
- `frontend/components/builder/library.tsx` - Drag-drop component library
- `frontend/components/builder/toolbar.tsx` - Undo/redo, grid toggle
- `frontend/components/builder/component-editor/` - Properties panel scaffolding
- `frontend/app/builder/page.tsx` - Next.js App Router page
- `frontend/app/builder/layout.tsx` - Builder layout wrapper
- `frontend/types/datamodel.ts` - 295 lines, Claude Agent SDK-aligned types
- `frontend/types/guards.ts` - 175 lines, 19 type guard functions

Phase 02 updates:
- `frontend/app/builder/layout.tsx` - Now includes auth check and Sidebar
- `frontend/components/ui/Sidebar.tsx` - Added Builder navigation link
- `frontend/components/builder/library.tsx` - Claude-oriented sections (Agents, MCP Servers, Built-in Tools)
- `frontend/components/builder/nodes.tsx` - McpServerNode component, mcp-connection edge type
- `frontend/components/builder/store.tsx` - MCP server node handling
- `frontend/types/guards.ts` - isMcpServerComponent guard

Phase 03 updates:
- `frontend/components/builder/properties-panel/` - New properties panel directory
- `frontend/components/builder/properties-panel/index.tsx` - Fixed right sidebar with store integration
- `frontend/components/builder/properties-panel/agent-config-form.tsx` - React Hook Form + Zod
- `frontend/components/builder/properties-panel/schemas/agent-schema.ts` - Zod validation schema
- `frontend/components/builder/properties-panel/fields/` - Model, system prompt, parameter fields
- `frontend/components/builder/builder.tsx` - Drawer replaced with PropertiesPanel
- `frontend/types/datamodel.ts` - Extended AgentConfig with topP, topK, stopSequences

Phase 04 updates:
- `backend/app/api/workflows.py` - Workflow CRUD endpoints with Pydantic models
- `backend/app/main.py` - Workflows router registration
- `frontend/lib/api.ts` - Workflow API client methods (getWorkflows, createWorkflow, etc.)
- `frontend/components/builder/builder.tsx` - Save modal, workflowId prop, API integration, auto-save, import
- `frontend/app/builder/page.tsx` - Workflow loading from URL, Suspense boundary
- `frontend/components/builder/hooks/use-autosave.ts` - Auto-save hook with 30-second interval

Phase 05 updates:
- `frontend/components/builder/properties-panel/schemas/mcp-server-schema.ts` - Zod schema with enabledTools and serverId
- `frontend/components/builder/properties-panel/mcp-server-form.tsx` - Tool fetching, selection checkboxes, Sync button
- `frontend/components/builder/properties-panel/index.tsx` - McpServerForm with serverId prop, enabledTools persistence
- `frontend/components/builder/library.tsx` - API fetch for registered MCP servers with serverId
- `frontend/components/builder/nodes.tsx` - McpServerNode tool count badge
- `frontend/types/datamodel.ts` - serverId field in McpServerConfig

Phase 06 updates:
- `frontend/components/builder/properties-panel/schemas/knowledge-schema.ts` - Zod schema for knowledge config
- `frontend/components/builder/properties-panel/knowledge-form.tsx` - Source type selection, multi-source input
- `frontend/components/builder/properties-panel/schemas/logic-schema.ts` - Zod schema for logic config
- `frontend/components/builder/properties-panel/logic-form.tsx` - Logic type selection, condition editor
- `frontend/components/builder/properties-panel/index.tsx` - KnowledgeForm and LogicForm integration
- `frontend/components/builder/library.tsx` - Logic section with 4 templates
- `frontend/components/builder/nodes.tsx` - KnowledgeNode and LogicNode already implemented
- `frontend/components/builder/validation/` - New validation module (types, rules, index)
- `frontend/components/builder/validation-errors.tsx` - Validation errors display component
- `frontend/components/builder/builder.tsx` - Validation integration in save and validate flows

Phase 07 updates (07-01):
- `frontend/components/builder/code-generation/ir.ts` - WorkflowIR, AgentIR, McpServerIR, KnowledgeSourceIR types
- `frontend/components/builder/code-generation/workflow-to-ir.ts` - workflowToIR() transformation function
- `frontend/components/builder/code-generation/workflow-to-ir.test.ts` - 13 comprehensive TDD tests
- `frontend/components/builder/code-generation/index.ts` - Barrel export for public API
- `frontend/jest.config.js` - Jest configuration with ts-jest
- `frontend/jest.setup.ts` - Jest setup with testing-library

Phase 07 updates (07-02):
- `frontend/components/builder/code-generation/ir-to-typescript.ts` - generateTypeScriptCode() function
- `frontend/components/builder/code-generation/ir-to-typescript.test.ts` - 16 TDD tests
- `frontend/components/builder/code-generation/index.ts` - Added generateTypeScriptCode export

Phase 07 updates (07-03):
- `backend/templates/agent/python/agent.py.j2` - Jinja2 template for Python agent code
- `backend/templates/agent/python/requirements.txt.j2` - Requirements template
- `backend/app/api/codegen.py` - Python code generation API endpoint
- `backend/app/main.py` - Registered codegen router
- `backend/requirements.txt` - Added Jinja2 dependency
- `frontend/components/builder/code-generation/code-preview.tsx` - Monaco Editor component
- `frontend/lib/api.ts` - Added generatePythonCode() and getPythonRequirements() methods
- `frontend/package.json` - Added @monaco-editor/react dependency

### Pending Todos

None yet.

### Blockers/Concerns

None - Phase 07-03 complete. Python code generation with Jinja2 ready. Monaco Editor component ready. Ready for 07-04 (Export Modal).

## Session Continuity

Last session: 2026-02-04T18:10:54Z
Stopped at: Completed 07-03-PLAN.md (Python Code Generation)
Resume file: None
