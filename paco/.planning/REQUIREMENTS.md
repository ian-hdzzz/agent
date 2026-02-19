# Requirements: PACO Visual Agent Builder

**Version:** 1.0
**Last Updated:** 2026-02-03

---

## v1 Requirements

### Canvas & Editor

- [x] **CANVAS-01**: User can drag nodes from palette onto visual canvas
- [x] **CANVAS-02**: User can connect nodes with edges to define data flow
- [x] **CANVAS-03**: User can pan and zoom canvas to navigate large workflows
- [x] **CANVAS-04**: User can select node to view/edit properties in side panel
- [x] **CANVAS-05**: User can delete selected nodes and edges
- [x] **CANVAS-06**: User can undo/redo canvas actions

### Node Types

- [ ] **NODE-01**: User can add Agent Configuration node with model, system prompt, temperature, max tokens
- [ ] **NODE-02**: User can add MCP Tool node and select tools from registered MCP servers
- [ ] **NODE-03**: User can add Knowledge Base node with document upload or URL source
- [ ] **NODE-04**: User can add Logic node for conditional branching based on agent output

### Persistence

- [ ] **PERSIST-01**: User can save workflow to database with name and description
- [ ] **PERSIST-02**: User can load saved workflow from workflow list
- [ ] **PERSIST-03**: Workflow auto-saves periodically while editing
- [ ] **PERSIST-04**: User can export workflow as JSON file
- [ ] **PERSIST-05**: User can import workflow from JSON file

### Code Generation

- [ ] **CODEGEN-01**: User can preview generated Claude Agent SDK code before export
- [ ] **CODEGEN-02**: User can export workflow as deployable Python/TypeScript code
- [ ] **CODEGEN-03**: Generated code includes all configured tools, prompts, and settings

### Deployment & Channels

- [ ] **DEPLOY-01**: User can configure Chatwoot inbox connection for deployed agent
- [ ] **DEPLOY-02**: User can configure ElevenLabs voice agent connection
- [ ] **DEPLOY-03**: User can view deployment status and logs

### Testing & Validation

- [ ] **TEST-01**: User can test agent in chat interface before deployment
- [ ] **TEST-02**: User can view execution trace via Langfuse integration
- [ ] **TEST-03**: User sees validation errors when workflow has invalid connections or missing config

---

## v2 Requirements (Deferred)

### Version Control

- [ ] **VER-01**: User can view version history of workflow changes
- [ ] **VER-02**: User can restore workflow to previous version
- [ ] **VER-03**: User can compare differences between workflow versions

### Advanced Nodes

- [ ] **ADV-01**: User can add Human Approval gate node for manual intervention
- [ ] **ADV-02**: User can add Loop node for iterative processing
- [ ] **ADV-03**: User can create reusable node groups/subflows

### Templates

- [ ] **TMPL-01**: User can start from pre-built workflow templates
- [ ] **TMPL-02**: User can save workflow as custom template

---

## Out of Scope

| Exclusion | Reasoning |
|-----------|-----------|
| Real-time collaborative editing | CRDTs for graph state are complex; single-user editing for v1 |
| Custom LLM providers | Claude-native positioning is our differentiator |
| Agent marketplace | Security/moderation complexity; internal use only |
| Mobile canvas editor | Touch-based node editing is poor UX |
| Billing/usage tracking | Langfuse provides observability; billing is separate concern |
| Direct PM2 deployment from UI | Code export + manual deployment preferred for v1 control |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CANVAS-01 | Phase 2 | Complete |
| CANVAS-02 | Phase 2 | Complete |
| CANVAS-03 | Phase 2 | Complete |
| CANVAS-04 | Phase 2 | Complete |
| CANVAS-05 | Phase 2 | Complete |
| CANVAS-06 | Phase 2 | Complete |
| NODE-01 | Phase 3 | Pending |
| NODE-02 | Phase 5 | Pending |
| NODE-03 | Phase 5 | Pending |
| NODE-04 | Phase 6 | Pending |
| PERSIST-01 | Phase 4 | Pending |
| PERSIST-02 | Phase 4 | Pending |
| PERSIST-03 | Phase 4 | Pending |
| PERSIST-04 | Phase 4 | Pending |
| PERSIST-05 | Phase 4 | Pending |
| CODEGEN-01 | Phase 7 | Pending |
| CODEGEN-02 | Phase 7 | Pending |
| CODEGEN-03 | Phase 7 | Pending |
| DEPLOY-01 | Phase 8 | Pending |
| DEPLOY-02 | Phase 8 | Pending |
| DEPLOY-03 | Phase 8 | Pending |
| TEST-01 | Phase 8 | Pending |
| TEST-02 | Phase 8 | Pending |
| TEST-03 | Phase 6 | Pending |

---
*Requirements defined: 2026-02-03*
*Traceability updated: 2026-02-03*
