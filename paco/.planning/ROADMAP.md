# Roadmap: PACO Visual Agent Builder

## Overview

This roadmap delivers a visual agent builder by forking and adapting Microsoft's AutoGen Studio (MIT licensed). AutoGen Studio provides a mature React Flow canvas with Zustand state management, MCP tool integration, undo/redo, and test interface. We adapt it for Claude Agent SDK (replacing AutoGen) and integrate with PACO's existing FastAPI backend.

**Key Adaptation Work:**
- Port from Gatsby to Next.js (PACO's existing frontend framework)
- Replace AutoGen data model with Claude Agent SDK data model
- Replace AutoGen backend API with PACO FastAPI
- Add code generation for Claude Agent SDK (new)
- Add channel configuration for Chatwoot/ElevenLabs (new)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Fork & Port Foundation** - Fork AutoGen Studio, port to Next.js, adapt data model
- [x] **Phase 2: Canvas Integration** - Integrate canvas with PACO layout, adapt node types for Claude
- [x] **Phase 3: Claude Agent Node** - Replace AutoGen agent config with Claude Agent SDK config
- [x] **Phase 4: Persistence** - Connect save/load to PACO workflow API
- [x] **Phase 5: MCP Tool Integration** - Connect to PACO's MCP server registry
- [x] **Phase 6: Knowledge & Validation** - Add knowledge base nodes, workflow validation
- [ ] **Phase 7: Code Generation** - Generate Claude Agent SDK code from workflow
- [ ] **Phase 8: Deployment & Channels** - Test chat, Chatwoot, ElevenLabs, deployment status

## Phase Details

### Phase 1: Fork & Port Foundation
**Goal**: AutoGen Studio frontend ported to Next.js with Claude-oriented data model
**Depends on**: Nothing (first phase)
**Requirements**: None directly (enables all subsequent phases)
**Plans**: 3 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md - Fork and extract AutoGen Studio frontend components
- [x] 01-02-PLAN.md - Port from Gatsby to Next.js App Router
- [x] 01-03-PLAN.md - Define Claude Agent SDK data model types

**Wave Structure:**
- Wave 1: 01-01 (extract components, install deps)
- Wave 2: 01-02 + 01-03 (parallel - Next.js port + data model types)

**Success Criteria** (what must be TRUE):
  1. AutoGen Studio frontend forked and extracted to frontend/components/builder/
  2. Gatsby-specific code replaced with Next.js App Router patterns
  3. Data model types updated for Claude Agent SDK (not AutoGen)
  4. Canvas renders in PACO frontend at /builder route

### Phase 2: Canvas Integration
**Goal**: Users can interact with a visual workflow canvas integrated with PACO's layout
**Depends on**: Phase 1
**Requirements**: CANVAS-01, CANVAS-02, CANVAS-03, CANVAS-04, CANVAS-05, CANVAS-06
**Plans**: 2 plans in 1 wave

Plans:
- [x] 02-01-PLAN.md - Integrate canvas with PACO layout (auth, sidebar, navigation)
- [x] 02-02-PLAN.md - Adapt node palette for Claude-oriented node types

**Wave Structure:**
- Wave 1: 02-01 + 02-02 (parallel - layout integration + node types)

**Success Criteria** (what must be TRUE):
  1. User can drag nodes from palette onto canvas (from AutoGen Studio)
  2. User can connect nodes with edges to define data flow
  3. User can pan and zoom the canvas to navigate workflows
  4. User can select a node to see its details highlighted
  5. User can delete selected nodes and edges
  6. User can undo and redo canvas actions

### Phase 3: Claude Agent Node
**Goal**: Users can configure a Claude agent's settings visually
**Depends on**: Phase 2
**Requirements**: NODE-01
**Plans**: 1 plan in 1 wave

Plans:
- [x] 03-01-PLAN.md - Fixed properties panel with agent configuration form

**Wave Structure:**
- Wave 1: 03-01 (properties panel + form infrastructure)

**Success Criteria** (what must be TRUE):
  1. User can add a Claude Agent Configuration node to the canvas
  2. User can select agent node and see properties panel on the side
  3. User can configure model (claude-sonnet-4-20250514, etc.), system prompt, temperature, max tokens
  4. Changes in properties panel update the node and persist in canvas state

### Phase 4: Persistence
**Goal**: Users can save and restore their workflow designs
**Depends on**: Phase 3
**Requirements**: PERSIST-01, PERSIST-02, PERSIST-03, PERSIST-04, PERSIST-05
**Plans**: 3 plans in 2 waves

Plans:
- [x] 04-01-PLAN.md - FastAPI workflow CRUD endpoints using existing Flow model
- [x] 04-02-PLAN.md - Connect canvas save/load to PACO API
- [x] 04-03-PLAN.md - Auto-save and import/export JSON

**Wave Structure:**
- Wave 1: 04-01 (backend API)
- Wave 2: 04-02 + 04-03 (parallel - frontend save/load + auto-save/import)

**Success Criteria** (what must be TRUE):
  1. User can save workflow with name and description to database
  2. User can see list of saved workflows and load one onto canvas
  3. Workflow auto-saves periodically while user is editing
  4. User can export current workflow as a JSON file
  5. User can import a workflow from a JSON file

### Phase 5: MCP Tool Integration
**Goal**: Users can connect MCP tools to their agents
**Depends on**: Phase 4
**Requirements**: NODE-02
**Plans**: 2 plans in 2 waves

Plans:
- [x] 05-01-PLAN.md - Connect MCP node to PACO's MCP server registry API
- [x] 05-02-PLAN.md - Tool selection UI for MCP servers

**Wave Structure:**
- Wave 1: 05-01 (MCP server form + API integration in library)
- Wave 2: 05-02 (tool fetching + selection checkboxes)

**Success Criteria** (what must be TRUE):
  1. User can add MCP Tool node and see list of PACO's registered MCP servers
  2. User can select which tools from an MCP server to make available to agent
  3. Tool nodes connect to agent nodes via edges
  4. Tool selection persists in workflow state

### Phase 6: Knowledge & Validation
**Goal**: Users can add knowledge bases and receive validation feedback
**Depends on**: Phase 5
**Requirements**: NODE-03, NODE-04, TEST-03
**Plans**: 3 plans in 2 waves

Plans:
- [x] 06-01-PLAN.md - Knowledge base node with document/URL source configuration
- [x] 06-02-PLAN.md - Logic node with condition configuration
- [x] 06-03-PLAN.md - Workflow validation and error display

**Wave Structure:**
- Wave 1: 06-01 + 06-02 (parallel - Knowledge node + Logic node)
- Wave 2: 06-03 (validation - depends on both node types existing)

**Success Criteria** (what must be TRUE):
  1. User can add Knowledge Base node with document upload option
  2. User can add Knowledge Base node with URL source option
  3. User can add Logic node for conditional branching
  4. User sees validation errors when workflow has invalid connections
  5. User sees validation errors when nodes have missing required configuration

### Phase 7: Code Generation
**Goal**: Users can preview and export deployable Claude Agent SDK code
**Depends on**: Phase 6
**Requirements**: CODEGEN-01, CODEGEN-02, CODEGEN-03
**Plans**: 4 plans in 3 waves

Plans:
- [ ] 07-01-PLAN.md - Intermediate representation (IR) types and workflow-to-IR transformation (TDD)
- [ ] 07-02-PLAN.md - TypeScript code generation from IR (TDD)
- [ ] 07-03-PLAN.md - Python code generation (Jinja2 backend) and Monaco code preview
- [ ] 07-04-PLAN.md - Export modal and builder integration

**Wave Structure:**
- Wave 1: 07-01 (IR foundation - no dependencies)
- Wave 2: 07-02 + 07-03 (parallel - TS codegen + Python codegen/Monaco)
- Wave 3: 07-04 (export UI - depends on both codegen plans)

**Success Criteria** (what must be TRUE):
  1. User can preview generated Python code before export
  2. User can preview generated TypeScript code before export
  3. User can export workflow as deployable Python file
  4. User can export workflow as deployable TypeScript file
  5. Generated code includes all configured tools, prompts, and settings from workflow

### Phase 8: Deployment & Channels
**Goal**: Users can test, deploy, and connect agents to channels
**Depends on**: Phase 7
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, TEST-01, TEST-02
**Success Criteria** (what must be TRUE):
  1. User can test agent in chat interface before deployment
  2. User can view execution trace via Langfuse integration
  3. User can configure Chatwoot inbox connection for deployed agent
  4. User can configure ElevenLabs voice agent connection
  5. User can view deployment status and logs for running agents
**Plans**: TBD

Plans:
- [ ] 08-01: Adapt AutoGen Studio test drawer for Claude agents
- [ ] 08-02: Langfuse execution trace integration
- [ ] 08-03: Chatwoot channel configuration node
- [ ] 08-04: ElevenLabs voice channel configuration node
- [ ] 08-05: Deployment status and logs UI

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Fork & Port Foundation | 3/3 | Complete | 2026-02-04 |
| 2. Canvas Integration | 2/2 | Complete | 2026-02-04 |
| 3. Claude Agent Node | 1/1 | Complete | 2026-02-03 |
| 4. Persistence | 3/3 | Complete | 2026-02-03 |
| 5. MCP Tool Integration | 2/2 | Complete | 2026-02-04 |
| 6. Knowledge & Validation | 3/3 | Complete | 2026-02-04 |
| 7. Code Generation | 0/4 | Planned | - |
| 8. Deployment & Channels | 0/5 | Not started | - |

## Source Material

**AutoGen Studio Fork:**
- Source: https://github.com/microsoft/autogen
- Package: python/packages/autogen-studio
- License: MIT
- Key Components:
  - `frontend/src/components/views/teambuilder/builder/` - Canvas and store
  - `frontend/src/components/views/teambuilder/builder/component-editor/` - Properties panel
  - `frontend/src/components/views/teambuilder/builder/component-editor/fields/workbench/` - MCP integration
  - `frontend/src/components/views/playground/chat/` - Test interface

**What We Get For Free:**
- React Flow canvas with drag-drop, pan/zoom, selection
- Zustand store with 50-entry undo/redo history
- Node/edge state management
- Properties panel architecture
- MCP tool discovery UI patterns
- Test drawer UI patterns
- Auto-layout with dagre

**What We Build:**
- Next.js port (replace Gatsby)
- Claude Agent SDK data model (replace AutoGen)
- Claude Agent SDK code generation (new)
- Chatwoot/ElevenLabs channel nodes (new)
- PACO backend integration (new)

---
*Roadmap updated: 2026-02-04 (Phase 7 planned)*
