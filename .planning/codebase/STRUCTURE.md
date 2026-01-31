# Codebase Structure

**Analysis Date:** 2026-01-31

## Directory Layout

```
agents-maria/
├── src/                         # CEA Agent Server (production agent)
│   ├── server.ts               # Express app, health/chat endpoints
│   ├── agent.ts                # Classification + specialist agents
│   ├── tools.ts                # Native tools (CEA API, database)
│   ├── context.ts              # AsyncLocalStorage for conversation context
│   ├── types.ts                # Shared type definitions
│   ├── test.ts                 # Interactive testing script
│   ├── test-api.ts             # API endpoint testing
│   ├── test-agent-flows.ts     # Agent conversation flows
│   ├── test-all-tickets.ts     # Bulk ticket testing
│   ├── test-ticket.ts          # Single ticket test
│   └── get-contract-info.ts    # Contract info utility
│
├── maria-claude/                # Maria Claude Agent (Anthropic SDK version)
│   ├── src/
│   │   ├── server.ts           # Express app with Chatwoot integration
│   │   ├── agent.ts            # Classification + skill router
│   │   ├── chatwoot.ts         # Chatwoot webhook handling
│   │   ├── media.ts            # Media/attachment processing
│   │   ├── tools.ts            # Agent tools (CEA API calls)
│   │   ├── types.ts            # AGORA-mapped type definitions
│   │   ├── index.ts            # Module exports
│   │   ├── skills/             # Skill implementations
│   │   │   ├── index.ts        # Skill registry
│   │   │   ├── base.ts         # Skill interface
│   │   │   ├── consultas.ts    # Queries (CON)
│   │   │   ├── facturacion.ts  # Billing (FAC)
│   │   │   ├── contratos.ts    # Contracts (CTR)
│   │   │   ├── convenios.ts    # Agreements (CVN)
│   │   │   ├── reportes.ts     # Service Reports (REP)
│   │   │   ├── servicios.ts    # Technical Services (SRV)
│   │   │   └── consumos.ts     # Consumption (CNS)
│   │   └── config/
│   │       ├── index.ts        # Config loader
│   │       └── response-templates.ts  # Response formatting templates
│   ├── package.json
│   ├── tsconfig.json
│   ├── ecosystem.config.cjs    # PM2 configuration
│   ├── Dockerfile
│   └── MARIA_DOCUMENTATION.md  # Comprehensive feature documentation
│
├── maria-interno/               # Internal agent (for internal staff)
│   ├── src/
│   │   ├── server.ts
│   │   ├── agent.ts
│   │   ├── tools.ts
│   │   ├── types.ts
│   │   ├── index.ts
│   │   ├── skills/
│   │   │   ├── index.ts
│   │   │   ├── base.ts
│   │   │   ├── seg.ts          # Security (SEG)
│   │   │   ├── com.ts          # Commerce (COM)
│   │   │   ├── adm.ts          # Administration (ADM)
│   │   │   ├── mnt.ts          # Maintenance (MNT)
│   │   │   ├── veh.ts          # Vehicles (VEH)
│   │   │   ├── rh.ts           # Human Resources (RH)
│   │   │   ├── ti.ts           # IT (TI)
│   │   │   ├── alm.ts          # Warehouse (ALM)
│   │   │   └── jur.ts          # Legal (JUR)
│   │   └── test.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── ecosystem.config.cjs
│   └── migrations/
│
├── proxy/                       # Proxy configuration/utilities
├── docs/                        # Documentation
├── .planning/                   # GSD planning documents (this dir)
├── package.json                 # Root workspace
└── .env.example                 # Template for environment variables
```

## Directory Purposes

**src/ (CEA Agent Server):**
- Purpose: Production-ready customer-facing chatbot for water utility (CEA Querétaro)
- Contains: Classification logic, 6 specialist agents, CEA SOAP API integration, database tools
- Key files: `server.ts` (entry point), `agent.ts` (agent definitions), `tools.ts` (API/DB layer)

**maria-claude/src/ (Maria Claude Agent):**
- Purpose: Alternative agent implementation using Anthropic Claude Agent SDK
- Contains: Skill-based routing aligned with AGORA ticketing system categories
- Key files: `server.ts` (endpoints), `agent.ts` (Claude classification), `skills/` (domain handlers)

**maria-interno/src/ (Internal Agent):**
- Purpose: Internal staff assistant for CEA operations
- Contains: Department-specific skills (HR, IT, Security, Maintenance, etc.)
- Key files: `skills/` directory with department mappings

**proxy/:**
- Purpose: Contains proxy configuration for whitelisted IP access to CEA APIs

**docs/:**
- Purpose: General documentation and guides

## Key File Locations

**Entry Points:**
- `src/server.ts`: CEA Agent REST API (port 3000 by default)
- `maria-claude/src/server.ts`: Maria Claude agent REST API
- `maria-interno/src/server.ts`: Internal agent API

**Agent Logic:**
- `src/agent.ts`: Classification + 6 specialist agents (informacion, pagos, consumos, fuga, contratos, tickets)
- `maria-claude/src/agent.ts`: Claude-based classifier + skill router

**External Integration:**
- `src/tools.ts`: CEA SOAP API calls, PostgreSQL database operations
- `maria-claude/src/chatwoot.ts`: Chatwoot webhook handling and context building
- `maria-claude/src/tools.ts`: Chatwoot-aware tool implementations

**Type Definitions:**
- `src/types.ts`: Chat types, ticket types, API response interfaces
- `maria-claude/src/types.ts`: AGORA category system, workflow types

**Configuration:**
- `src/context.ts`: AsyncLocalStorage context management
- `maria-claude/src/config/response-templates.ts`: Response format templates
- `.env.example`: Required environment variables

**Testing:**
- `src/test.ts`: Interactive test harness
- `src/test-api.ts`: HTTP endpoint testing
- `maria-claude/MARIA_DOCUMENTATION.md`: Feature documentation with examples

## Naming Conventions

**Files:**
- Entry point: `server.ts` (Express app)
- Agent logic: `agent.ts` (OpenAI/Claude agents)
- External integration: `tools.ts` (tool implementations), `chatwoot.ts` (webhook handler)
- Data types: `types.ts` (interfaces and enums)
- Utilities: `context.ts`, `config/`, `media.ts`
- Skills: Individual files per skill (`consultas.ts`, `facturacion.ts`, etc.) in `skills/`

**Directories:**
- Feature domains: `skills/` (one skill per file)
- Configuration: `config/` (config files and templates)
- Package organization: Each major agent in separate directory (`src/`, `maria-claude/`, `maria-interno/`)

**Functions and Classes:**
- Agents: camelCase with Agent suffix (`classificationAgent`, `pagosAgent`)
- Tools: camelCase with Tool suffix (`getDeudaTool`, `createTicketTool`)
- Utilities: camelCase prefixed with action (`fetchWithRetry`, `parseXMLValue`)
- Exports: Named exports for tools, default export for modules with single primary export

**Types and Interfaces:**
- PascalCase for all types (`ChatRequest`, `ChatResponse`, `Classification`)
- Enum-like types use union: `"fuga" | "pagos"` (not enum keyword)
- Schema validation uses Zod: `z.object({...})`

## Where to Add New Code

**New Specialist Agent (CEA Agent):**
- Implement agent instance in `src/agent.ts` (follow pagosAgent pattern)
- Add to `agentMap` router
- Add classification type to `Classification` union in `types.ts`
- Implement tools in `src/tools.ts` if needed
- Example: `const newAgent = new Agent({ name, model, instructions, tools, ... })`

**New Skill (Maria Claude):**
- Create new file `maria-claude/src/skills/[code].ts` (e.g., `newskill.ts`)
- Implement Skill interface from `base.ts`
- Export and register in `maria-claude/src/skills/index.ts` SKILL_REGISTRY
- Add to CategoryCode type in `maria-claude/src/types.ts`

**New Tool:**
- Add to `src/tools.ts` or `maria-claude/src/tools.ts`
- Use `tool()` wrapper from @openai/agents
- Define input schema with Zod
- Export with Tool suffix: `export const newTool = tool({ ... })`
- Add to appropriate agent's tools array

**New Test Script:**
- Create in `src/test-[feature].ts`
- Use existing test patterns (import agent, create runner, execute)
- Run with: `npm run test` or `tsx src/test-[feature].ts`

**API Endpoint:**
- Add route to `server.ts`: `app.post('/api/[endpoint]', handler)`
- Implement handler with request validation
- Return typed responses from `types.ts`

**Utilities:**
- Shared functions: `src/tools.ts` (utilities section)
- Context management: Add to `src/context.ts`
- Configuration: Add to `maria-claude/src/config/index.ts`

## Special Directories

**node_modules:**
- Purpose: Installed dependencies
- Generated: Yes
- Committed: No (excluded via .gitignore)

**dist/**
- Purpose: Compiled JavaScript output from TypeScript
- Generated: Yes (via `npm run build`)
- Committed: No

**migrations/**
- Purpose: Database migration scripts (maria-interno)
- Generated: No
- Committed: Yes

**.planning/codebase/**
- Purpose: GSD analysis documents
- Generated: Yes (by GSD mappers)
- Committed: Yes (for team reference)

## Import Patterns

**Internal imports use relative paths:**
```typescript
import { tool } from "@openai/agents";
import type { WorkflowInput } from "./types.js";
import { runWithChatwootContext } from "./context.js";
```

**External package imports grouped at top:**
```typescript
import express from "express";
import { config } from "dotenv";
import pg from "pg";
```

**Tools imported collectively:**
```typescript
import {
    getDeudaTool,
    getConsumoTool,
    createTicketTool
} from "./tools.js";
```

**Type imports use type keyword:**
```typescript
import type { ChatRequest, ChatResponse } from "./types.js";
```

---

*Structure analysis: 2026-01-31*
