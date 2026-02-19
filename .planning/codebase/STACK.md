# Technology Stack

**Analysis Date:** 2026-02-03

## Languages

**Primary:**
- TypeScript 5.7.2 / 5.3.3 - All application code (src/, maria-claude/, maria-voz/, paco/)
- JavaScript (Node.js) - Runtime execution and build output
- Python - PACO backend services (FastAPI)

**Secondary:**
- SQL - Database schema and queries (PostgreSQL)
- XML - SOAP API request/response handling for CEA integration
- Bash/Shell - npm scripts and deployment automation

## Runtime

**Environment:**
- Node.js >= 20.0.0 (required for TypeScript applications)
- Python 3.9+ (PACO backend)
- ES2022 compilation target (TypeScript)
- ESNext module format

**Package Manager:**
- npm - Node.js dependency management
- pip - Python package management (PACO)
- Lockfiles: package-lock.json present in each Node.js workspace

## Frameworks

**Core Web Framework:**
- Express 4.21.2 / 4.18.2 - Web server and REST API endpoints
  - Used in: `src/server.ts`, `maria-claude/src/server.ts`, `maria-voz/src/server.ts`
  - Provides: HTTP routing, middleware, health checks, webhook endpoints

**AI/Agent Frameworks:**
- @anthropic-ai/claude-agent-sdk 0.2.4 (maria-claude) - Anthropic's agent framework with skill routing and MCP
  - Primary in: `maria-claude/src/agent.ts`
  - Provides: `query()`, `createSdkMcpServer()`, tool registration
- @openai/agents 0.0.14 - OpenAI agents framework (legacy, cea-agent-server)
  - Used in: `src/agent.ts`, `src/tools.ts`
  - Provides: Agent class, AgentInputItem, Runner, withTrace

**API Clients:**
- openai 4.77.0 - OpenAI API client for GPT models
- @anthropic-ai/sdk 0.71.2 - Anthropic SDK for Claude API
- undici 7.16.0 / 7.20.0 - HTTP client with proxy support for CEA API

**Build/Dev Tools:**
- TypeScript 5.7.2 / 5.3.3 - Type checking and compilation
- tsx 4.19.2 / 4.7.0 - TypeScript execution without build step (development)
- tsc - TypeScript compiler (production builds)

**Database & ORM:**
- pg 8.16.3 / 8.11.3 - PostgreSQL client library with connection pooling
- FastAPI - Python web framework (PACO backend)
- SQLAlchemy - Python ORM (PACO backend)

**Voice & Media:**
- soap 1.0.0 - SOAP client for CEA legacy API endpoints (maria-voz)
- ElevenLabs API - Voice synthesis and agent orchestration (maria-voz)

**Observability (PACO):**
- Langfuse - LLM observability platform for tracing and monitoring
- OpenTelemetry - Telemetry collection (optional)

## Key Dependencies

**Critical:**
- @anthropic-ai/claude-agent-sdk / @openai/agents - Agent orchestration and reasoning
- pg - PostgreSQL connection pooling for AGORA database (tickets, contacts)
- zod 3.24.1 / 4.0.0 - Schema validation for API inputs/outputs
- dotenv 16.4.7 / 16.3.1 - Environment variable loading

**Infrastructure:**
- express - HTTP server for all endpoints (/api/chat, /webhook, /health, /status)
- undici - HTTP client with ProxyAgent for CEA SOAP calls through whitelisted proxy
- soap - SOAP client for legacy CEA endpoints
- FastAPI - Python backend for PACO (CEA Agent Hub)

**Voice & Media:**
- ElevenLabs API integration - Voice transcription, synthesis, agent webhooks (maria-voz)
- OpenAI Whisper - Audio transcription (optional, via openai package)

## Configuration

**Environment Variables:**

**Root Project (cea-agent-server):**
- `OPENAI_API_KEY` - OpenAI API key (required)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL AGORA database
- `PGPOOL_MAX` - Connection pool size (default 10)
- `PORT` - Server port (default 3000)
- `OPENAI_MODEL` - Model selection (default gpt-4o-mini)
- `CEA_PROXY_URL` - Optional proxy for CEA API
- `TEST_CONTRACT` - Test contract for validation

**Maria Claude:**
- `ANTHROPIC_API_KEY` - Anthropic API key (required)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL
- `CHATWOOT_BASE_URL` - Chatwoot instance URL
- `CHATWOOT_API_TOKEN` - Chatwoot API token
- `OPENAI_API_KEY` - OpenAI Whisper for audio transcription (optional)

**Maria Voz:**
- `PORT` - Server port (default 3001)
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` - PostgreSQL
- `CEA_PROXY_URL` - Optional proxy for CEA API
- `ELEVENLABS_WEBHOOK_SECRET` - ElevenLabs webhook authentication
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `WHATSAPP_NUMBER` - Redirect phone number for fallback

**PACO (Agent Hub):**
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - PostgreSQL setup
- `LANGFUSE_URL` - Langfuse instance (default localhost:3001)
- `LANGFUSE_NEXTAUTH_SECRET` - NextAuth secret (min 32 chars)
- `LANGFUSE_ENCRYPTION_KEY` - 64 hex characters (32 bytes)
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` - Langfuse API keys
- `PACO_SECRET_KEY` - Backend secret key (min 32 chars)
- `PACO_API_URL` - Backend API URL
- `PACO_NEXTAUTH_SECRET` - Frontend NextAuth secret
- `ANTHROPIC_API_KEY` - Anthropic Claude API
- `CHATWOOT_API_KEY` - Chatwoot integration
- `CEA_API_URL`, `CEA_API_USER`, `CEA_API_PASSWORD` - CEA SOAP API credentials

**Build Configuration:**
- `tsconfig.json` - TypeScript compiler options
  - Target: ES2022
  - Module: ESNext
  - Strict mode enabled
  - Output dir: `dist/`

**Docker Files:**
- `Dockerfile` - Multi-stage Alpine Linux build
- `docker-compose.yml` - Development environment with easypanel-whisper-api network
- `docker-compose.proxy.yml` - Alternative proxy configuration

## Platform Requirements

**Development:**
- Node.js 20.0.0+
- Python 3.9+ (for PACO)
- PostgreSQL 12+
- npm or yarn
- Unix-like shell

**Production:**
- Docker 20.10+ with Alpine Linux (node:20-alpine for Node apps)
- PostgreSQL 12+ (external service)
- Python 3.9+ with FastAPI (PACO backend)
- Container orchestration (Docker Compose, Kubernetes, or Docker Swarm)
- Memory limits: 512MB (containers)
- Non-root user execution (uid: 1001)

**API Service Dependencies:**
- CEA SOAP API (aquacis-cf-int.ceaqueretaro.gob.mx)
- OpenAI API
- Anthropic API
- ElevenLabs API
- Chatwoot instance

## Project Structure

Multi-application monorepo with independent deployment units:

1. **cea-agent-server** (`/src`) - OpenAI-based agent
   - Framework: @openai/agents
   - Entry: `src/server.ts`

2. **maria-claude** (`/maria-claude`) - Anthropic Claude agent with skills
   - Framework: @anthropic-ai/claude-agent-sdk
   - Entry: `maria-claude/src/server.ts`

3. **maria-voz** (`/maria-voz`) - Voice agent webhook for ElevenLabs
   - Framework: Express + ElevenLabs integration
   - Entry: `maria-voz/src/server.ts`

4. **11labscompanion** (`/11labscompanion`) - ElevenLabs voice companion
   - Tech: Node.js with ElevenLabs SDK

5. **paco** (`/paco`) - Agent Hub (Langfuse + Redis + PostgreSQL + FastAPI)
   - Frontend: Next.js (port 3000)
   - Backend: Python FastAPI (port 8000)
   - Observability: Langfuse (port 3001)

---

*Stack analysis: 2026-02-03*
