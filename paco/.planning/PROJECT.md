# PACO Visual Agent Builder

## What This Is

A production-ready visual agent builder for Claude Agent SDK, integrated into the PACO control plane. Users design AI agent workflows using a drag-and-drop canvas (like OpenAI's AgentKit), generate deployable code, and run agents with channel integrations (Chatwoot, ElevenLabs voice). Built for developers and operators who need to create, deploy, and manage Claude-powered agents without writing code from scratch.

## Core Value

Users can visually design and deploy working Claude agents in minutes, not hours — with full control over tools, knowledge bases, and multi-step workflows.

## Requirements

### Validated

- ✓ FastAPI backend with agent management API — existing
- ✓ Next.js frontend with dashboard UI — existing
- ✓ PostgreSQL database for persistence — existing
- ✓ PM2-based agent deployment infrastructure — existing
- ✓ Chatwoot webhook integration (maria-claude) — existing
- ✓ ElevenLabs voice integration (maria-voz) — existing
- ✓ MCP server registry and tool management — existing

### Active

- [ ] Visual workflow canvas using React Flow
- [ ] Agent configuration node (system prompt, model, temperature, max tokens)
- [ ] MCP tool nodes (connect registered MCP servers, configure tool access)
- [ ] Knowledge base nodes (document upload, URL scraping, RAG integration)
- [ ] Logic nodes (conditional branching, loops, human approval gates)
- [ ] Workflow persistence (save/load workflows to database)
- [ ] Code generation (export to Python/TypeScript Claude Agent SDK)
- [ ] Workflow deployment (generate agent config, deploy via PM2)
- [ ] Preview/test chat interface (test agent before deployment)
- [ ] Channel configuration (connect Chatwoot inbox, ElevenLabs agent)
- [ ] Workflow templates (pre-built starting points)
- [ ] Version history (track workflow changes)

### Out of Scope

- Mobile app — web-first, responsive design sufficient
- Real-time collaborative editing — single-user editing for v1
- Custom LLM providers — Claude only via Anthropic API
- Marketplace for agents — internal use only
- Billing/usage tracking — use existing Langfuse for observability

## Context

**Existing codebase (brownfield):**
- PACO already has a working control plane (FastAPI + Next.js)
- Agent management exists but uses YAML config files
- MCP server registry exists but tools aren't visually configurable
- maria-claude and maria-voz are reference implementations of deployed agents
- Langfuse integration provides observability for agent executions

**Reference platforms studied:**
- OpenAI AgentKit — visual workflow builder with nodes, properties panel, preview
- ElevenLabs Agent Builder — voice-focused, simpler configuration
- CrewAI Studio — multi-agent orchestration patterns

**Technical approach:**
- Fork Microsoft AutoGen Studio (MIT licensed) as foundation
- Port from Gatsby to Next.js (PACO's existing frontend framework)
- Replace AutoGen data model with Claude Agent SDK data model
- Leverage existing canvas, Zustand store, undo/redo, MCP UI from fork
- Store workflows as JSON in PostgreSQL (similar to agent configs)
- Generate Claude Agent SDK code from workflow definition
- Deploy using existing PM2 infrastructure, architect for Docker migration

## Constraints

- **Tech Stack**: Must extend existing Next.js/FastAPI codebase — no new frameworks
- **Deployment**: PM2 for v1, must be architecturally ready for Docker/K8s
- **AI Provider**: Claude API only — no OpenAI, local models, etc.
- **Authentication**: Use existing PACO auth (JWT, role-based)
- **Database**: PostgreSQL only — use existing schema patterns

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fork AutoGen Studio | Gets canvas, Zustand store, MCP UI, undo/redo for free; MIT licensed | Decided |
| Port Gatsby to Next.js | PACO already uses Next.js; avoid framework mixing | Decided |
| React Flow for canvas | AutoGen Studio uses it; most mature, best docs | Decided |
| Extend PACO vs new app | Reuse auth, database, agent management infra | Decided |
| JSON workflow storage | Flexible, versionable, exportable | Decided |
| PM2 first, Docker later | Ship faster with existing infra | Decided |

---
*Last updated: 2026-02-03 after initialization*
