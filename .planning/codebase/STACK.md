# Technology Stack

**Analysis Date:** 2026-01-31

## Languages

**Primary:**
- TypeScript 5.7.2 - All application code, agent implementations, and tooling
- JavaScript (Node.js) - Runtime execution and build output

**Secondary:**
- SQL - Database schema and migrations (PostgreSQL)
- XML - SOAP API request/response handling for CEA integration

## Runtime

**Environment:**
- Node.js >= 20.0.0 (required)
- ES2022 compilation target (TypeScript)
- ESNext module format

**Package Manager:**
- npm - Dependency management
- Lockfiles: package-lock.json present in each workspace

## Frameworks

**Core Framework:**
- Express 4.21.2 - Web server and REST API endpoints
  - Used in: `src/server.ts`, `maria-claude/src/server.ts`, `maria-interno/src/server.ts`

**AI/Agent Frameworks:**
- @anthropic-ai/claude-agent-sdk 0.2.4 (maria-claude), 0.1.0 (maria-interno) - Anthropic's agent framework with skill routing and MCP integration
  - Primary in: `maria-claude/src/agent.ts`, `maria-interno/src/agent.ts`
  - Provides: `query()`, `createSdkMcpServer()`, tool registration
- @openai/agents 0.0.14 - OpenAI agents framework (legacy, cea-agent-server only)
  - Used in: `src/agent.ts`, `src/tools.ts`
  - Provides: Agent class, AgentInputItem, Runner, withTrace

**API Clients:**
- openai 4.77.0 (cea-agent-server) - OpenAI API client for GPT models and Whisper transcription
- @anthropic-ai/sdk 0.71.2 (maria-claude) - Anthropic SDK for direct Claude API calls

**Build/Dev Tools:**
- TypeScript 5.7.2 - Type checking and compilation
- tsx 4.19.2 - TypeScript execution without build step (development)
- tsc - TypeScript compiler (production builds)

## Key Dependencies

**Critical:**
- pg 8.16.3 - PostgreSQL client library with connection pooling
  - Connection pooling configured: PGPOOL_MAX (default 10)
  - Used for ticket system and Chatwoot/AGORA database access
- zod 3.24.1 (cea-agent-server), 4.0.0 (maria-claude) - Schema validation for API inputs/outputs
- dotenv 16.4.7 - Environment variable loading from .env files

**Infrastructure:**
- undici 7.16.0 - HTTP client with proxy support
  - Used for CEA SOAP API calls with optional proxy (CEA_PROXY_URL)
  - Includes ProxyAgent for whitelisted IP-only CEA API access

## Configuration

**Environment Variables (Required):**

**Root Project (cea-agent-server):**
- `OPENAI_API_KEY` - OpenAI API key for GPT models and Whisper
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGPOOL_MAX` - PostgreSQL AGORA database
- `PORT` - Server port (default 3000)
- `OPENAI_MODEL` - Model selection (default gpt-4o-mini)
- `CEA_PROXY_URL` - Optional proxy for CEA API (e.g., http://10.128.0.7:3128)
- `TEST_CONTRACT` - Test contract for API validation

**Maria Claude (claude-agent-sdk):**
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude models
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGPOOL_MAX` - PostgreSQL AGORA database
- `CEA_PROXY_URL` - Optional proxy for CEA SOAP API
- `PORT` - Server port (default 3000)
- `CHATWOOT_BASE_URL` - Chatwoot instance URL (e.g., https://agora.humansoftware.mx)
- `CHATWOOT_API_TOKEN` - Chatwoot API token for message posting
- `OPENAI_API_KEY` - OpenAI Whisper for audio transcription

**Maria Interno (claude-agent-sdk):**
- `ANTHROPIC_API_KEY` - Anthropic API key
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGPOOL_MAX` - PostgreSQL database
- `PORT` - Server port (default 3001)
- `CHATWOOT_API_KEY` - Chatwoot API key (optional)
- `CHATWOOT_BASE_URL` - Chatwoot base URL (optional)
- `CHATWOOT_ACCOUNT_ID` - Chatwoot account ID (optional)
- `CHATWOOT_INBOX_ID` - Chatwoot inbox ID (optional)

**Build Configuration:**

- `tsconfig.json` - TypeScript compiler options
  - Target: ES2022
  - Module: ESNext
  - Strict mode enabled
  - Declaration files generated
  - Root dir: `src/`, Output dir: `dist/`

## Platform Requirements

**Development:**
- Node.js 20.0.0 or higher
- npm for package management
- TypeScript knowledge for source code modifications
- PostgreSQL 12+ for database (local development)

**Production:**
- Node.js 20.0.0 or higher
- PostgreSQL 12+ (AGORA database for Chatwoot integration)
- Chatwoot instance (optional, for conversation linkage)
- Network access to CEA SOAP API endpoints (https://aquacis-cf.ceaqueretaro.gob.mx/Comercial/services)
- Optional: HTTP proxy for whitelelist-IP-only CEA API access

**API Service Dependencies:**
- CEA SOAP Web Services (aquacis-cf.ceaqueretaro.gob.mx) - Water utility customer data
- OpenAI API - GPT-4, GPT-4-mini, Whisper transcription
- Anthropic API - Claude models
- Chatwoot API - Conversation management and message posting

## Project Structure

Three independent Node.js applications in monorepo:

1. **cea-agent-server** (`/src`) - OpenAI-based agent for CEA customer queries
   - Entry point: `src/server.ts`
   - Agent framework: @openai/agents
   - Tools: CEA SOAP API, ticket creation, database queries

2. **maria-claude** (`/maria-claude`) - Anthropic Claude agent with skill routing
   - Entry point: `maria-claude/src/server.ts` and `maria-claude/src/index.ts`
   - Agent framework: @anthropic-ai/claude-agent-sdk
   - Skills: 7+ specialized skills for CEA queries
   - Integration: Chatwoot webhook handling, media processing

3. **maria-interno** (`/maria-interno`) - Internal employee ticket system
   - Entry point: `maria-interno/src/server.ts` and `maria-interno/src/index.ts`
   - Agent framework: @anthropic-ai/claude-agent-sdk
   - Skills: 9 department-specific categories (TI, RH, MNT, VEH, ALM, ADM, COM, JUR, SEG)
   - Database: PostgreSQL with dedicated internal_tickets table

---

*Stack analysis: 2026-01-31*
