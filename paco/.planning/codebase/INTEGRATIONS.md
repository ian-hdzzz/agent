# External Integrations

**Analysis Date:** 2026-02-03

## APIs & External Services

**OpenAI (GPT and Whisper):**
- Service: OpenAI API for chat completions and audio transcription
- Used for: Agent reasoning, Whisper audio transcription
- SDK/Client: openai 4.77.0
- Auth: `OPENAI_API_KEY` environment variable
- Models: gpt-4o-mini (default), gpt-4.1, gpt-4.1-mini
- Endpoints:
  - `src/agent.ts` - Classification and specialist agents
  - `maria-claude/src/media.ts` - Whisper transcription for audio attachments

**Anthropic Claude API:**
- Service: Anthropic Claude for agentic AI and reasoning
- Used for: Main agent workflow, skill-based routing, multi-turn conversations
- SDK/Client: @anthropic-ai/sdk 0.71.2
- Auth: `ANTHROPIC_API_KEY` environment variable
- Features: Messages API, tool use, vision capabilities
- Endpoints:
  - `maria-claude/src/agent.ts` - Main workflow with skill routing
  - `maria-voz/src/tools/` - Tool execution for voice agent

**CEA SOAP Web Services:**
- Service: CEA (Comisión Estatal del Agua) Querétaro legacy SOAP API
- Base URL: `https://aquacis-cf-int.ceaqueretaro.gob.mx/Comercial/services`
- Used for: Contract info, debt/balance, consumption history, water service details
- Client: undici 7.16.0 with ProxyAgent support, manual SOAP envelope builders
- Auth: WSSE UsernameToken (hardcoded: WSGESTIONDEUDA/WSGESTIONDEUDA)
- Endpoints:
  - `InterfazGenericaContratacionWS` - Contract details (get_contract_details tool)
  - `InterfazGenericaGestionDeudaWS` - Debt/balance (get_deuda tool)
  - `InterfazOficinaVirtualClientesWS` - Consumption history (get_consumo tool)
- Proxy: Optional via `CEA_PROXY_URL` for IP-whitelisted access
- Implementation: `src/tools.ts`, `maria-claude/src/tools.ts`, `maria-voz/src/tools/`

**ElevenLabs (Voice):**
- Service: Voice synthesis, speech recognition, voice agent orchestration
- Used for: Voice call handling, audio synthesis, agent webhook callbacks
- SDK/Client: Direct HTTP webhooks, ElevenLabs Agent API
- Auth: `ELEVENLABS_API_KEY`, `ELEVENLABS_WEBHOOK_SECRET` environment variables
- Webhooks:
  - `POST /webhook/:toolName` - Tool call requests from voice agent
  - Tool response format: { result: string, tool_call_id?: string }
- Features: Real-time voice conversations, transcription, synthesis
- Implementation: `maria-voz/src/server.ts`, webhook handling for agent tool calls

**Chatwoot (Customer Messaging Platform):**
- Service: Chatwoot conversation management and messaging platform
- Used for: Conversation storage, ticket linking, message display, contact management
- API Endpoints:
  - `POST ${CHATWOOT_BASE_URL}/api/v1/accounts/${accountId}/conversations/${conversationId}/messages`
  - Auth: Header `api_access_token: ${CHATWOOT_API_TOKEN}`
- Webhook: `POST /webhook/chatwoot` - Incoming customer messages
- Features: Multi-channel messaging, contact database, conversation history
- Implementation:
  - `maria-claude/src/chatwoot.ts` - Message posting, status updates
  - `maria-claude/src/server.ts` - Webhook processing

**Langfuse (Observability):**
- Service: LLM observability and monitoring platform (PACO module)
- Used for: Trace collection, cost tracking, performance monitoring
- Auth: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` environment variables
- Configuration:
  - Base URL: `LANGFUSE_URL` (default: localhost:3001)
  - Encryption key: `LANGFUSE_ENCRYPTION_KEY` (64 hex characters)
  - NextAuth secret: `LANGFUSE_NEXTAUTH_SECRET` (min 32 chars)
- Features: Agent tracing, token counting, LLM call logging
- Implementation: PACO backend integration (paco/backend)

## Data Storage

**Databases:**

**PostgreSQL - AGORA Production (Main):**
- Type: PostgreSQL 12+
- Purpose: Ticket system, contact management, conversation history
- Connection: Pool-based via pg library
  - Config: `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGPOOL_MAX` (default 10)
  - Pool initialization: `const pgPool = new pg.Pool(PG_CONFIG)`
- Client: pg 8.16.3 / 8.11.3
- Tables:
  - `tickets` - Support tickets with fields: folio, title, status, priority, service_type, contract_number, contact_id, conversation_id
  - `contacts` - Customers/agents with: id, name, email, phone_number, identifier, custom_attributes
  - `conversations` - Chat conversations with message history
  - `messages` - Individual conversation messages
  - `agent_conversation_links` - Mapping between tickets and conversations
- Implementation: `src/tools.ts`, `maria-claude/src/tools.ts`

**PostgreSQL - PACO (Agent Hub):**
- Type: PostgreSQL 12+
- Purpose: PACO backend data storage
- Container: postgres service in docker-compose
- Configuration:
  - User: `POSTGRES_USER` (default: paco)
  - Password: `POSTGRES_PASSWORD`
  - Database: `POSTGRES_DB` (default: paco)
- Tables: Application-specific (FastAPI models)
- Implementation: PACO backend (paco/backend)

**Redis (PACO):**
- Type: In-memory key-value store
- Purpose: Session management, caching, rate limiting (PACO)
- Configuration: Default Redis settings (no auth by default)
- Optional: Can add `REDIS_PASSWORD` for authentication
- Implementation: PACO architecture (paco/docker-compose.yml)

**File Storage:**
- Local filesystem: `/output` directory for 11labscompanion voice files
- Chatwoot-managed: Media attachments stored in Chatwoot, downloaded for processing
- Temporary: Audio files downloaded from Chatwoot URLs, processed by Whisper/Claude Vision

**Caching:**
- In-memory conversation store (1-hour TTL with 5-minute cleanup)
  - `src/agent.ts`: conversationStore Map<string, ConversationEntry>
  - `maria-claude/src/agent.ts`: conversationStore Map<string, ConversationEntry>
  - Message deduplication: In-memory Set<number> with 1-minute TTL
- No external cache service (Redis is only in PACO module, not core agents)

## Authentication & Identity

**Auth Provider:**
- Custom implementation per application
- No centralized user authentication framework

**Implementation:**
- CEA SOAP: Hardcoded WSSE credentials (WSGESTIONDEUDA username/password)
- OpenAI: Environment variable `OPENAI_API_KEY`
- Anthropic: Environment variable `ANTHROPIC_API_KEY`
- Chatwoot: API token via `CHATWOOT_API_TOKEN` header
- ElevenLabs: Webhook secret via `ELEVENLABS_WEBHOOK_SECRET` header
- Langfuse: API keys `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`

**Chatwoot Context (Custom):**
- AsyncLocalStorage-based context in `src/context.ts`
- Fields: contactId, conversationId, inboxId
- Thread-safe context propagation via `runWithChatwootContext()`
- Purpose: Automatic ticket linking to customer conversations

## Monitoring & Observability

**Error Tracking:**
- Not detected in core applications
- Console logging for all errors via console.error()

**Logs:**
- Approach: Console logging throughout
- Levels: info (console.log), warn (console.warn), error (console.error)
- Formatted with prefixes: [API], [Chatwoot], [Media], [Database], [Ticket], [Agent], [webhook]
- PM2 config (production): Error and output logs
  - maria-claude: `/home/fcamacholombardo/logs/maria-claude-error.log`
  - maria-claude: `/home/fcamacholombardo/logs/maria-claude-out.log`
  - Date format: YYYY-MM-DD HH:mm:ss Z
  - Merge logs enabled

**Health Checks:**
- `GET /health` - Basic uptime status { status: "ok", timestamp, uptime }
- `GET /status` - Detailed system status (memory, uptime, agent health, Chatwoot connectivity)
- Docker healthcheck: `wget --no-verbose --tries=1 --spider http://localhost:3000/health`
- Interval: 30 seconds, Timeout: 5s, Retries: 3

**Observability (PACO):**
- Langfuse tracing for LLM calls
- OpenTelemetry optional for external collectors
- Metrics: Token usage, response times, error rates

## CI/CD & Deployment

**Hosting:**
- Docker containers (node:20-alpine for Node apps)
- PM2 process manager for production Linux servers
- Docker Compose for local development
- Kubernetes-ready (resource limits/reservations specified)

**CI Pipeline:**
- Not detected: No GitHub Actions, GitLab CI, or automated CI
- Manual build process: `npm run build` (TypeScript compilation)

**Build Process:**
- Docker: Multi-stage build (builder stage → production stage)
  - Builder: Compiles TypeScript, installs all dependencies
  - Production: Copies compiled dist/, installs only production dependencies
- Docker Compose: `docker-compose.yml` with easypanel-whisper-api network
- PM2: `ecosystem.config.cjs` for production Linux deployment

**Deployment Configuration:**
- Container resource limits: CPU 1.0, Memory 512M (limits), CPU 0.25, Memory 128M (reservations)
- Health checks: Enabled for all containers
- Network: External network `easypanel-whisper-api`
- Non-root user: nodejs (uid: 1001)

## Environment Configuration

**Required Environment Variables (by application):**

**cea-agent-server:**
```
OPENAI_API_KEY          # Required - OpenAI API access
PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE  # Required - Database
PGPOOL_MAX              # Optional - default 10
PORT                    # Optional - default 3000
OPENAI_MODEL            # Optional - default gpt-4o-mini
CEA_PROXY_URL           # Optional - proxy for CEA API
TEST_CONTRACT           # Optional - test contract
```

**maria-claude:**
```
ANTHROPIC_API_KEY       # Required - Claude API access
PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE  # Required - Database
CHATWOOT_BASE_URL       # Required - Chatwoot instance URL
CHATWOOT_API_TOKEN      # Required - Chatwoot API access
PGPOOL_MAX              # Optional - default 10
CEA_PROXY_URL           # Optional - CEA proxy
OPENAI_API_KEY          # Optional - Whisper transcription
```

**maria-voz:**
```
PORT                    # Optional - default 3001
PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE  # Optional - Database
CEA_PROXY_URL           # Optional - CEA proxy
ELEVENLABS_WEBHOOK_SECRET  # Optional - webhook auth
ELEVENLABS_API_KEY      # Optional - ElevenLabs API
WHATSAPP_NUMBER         # Optional - fallback phone
```

**paco:**
```
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB  # Required - DB setup
LANGFUSE_URL            # Required - Langfuse instance
LANGFUSE_NEXTAUTH_SECRET  # Required - min 32 chars
LANGFUSE_ENCRYPTION_KEY # Required - 64 hex chars
LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY  # Required - Langfuse
PACO_SECRET_KEY         # Required - backend secret
PACO_NEXTAUTH_SECRET    # Required - frontend secret
ANTHROPIC_API_KEY       # Optional - Claude API
CHATWOOT_API_KEY        # Optional - Chatwoot integration
CEA_API_URL, CEA_API_USER, CEA_API_PASSWORD  # Optional - CEA
```

**Secrets Location:**
- Development: `.env` files (git-ignored, not committed)
- Production: PM2 ecosystem.config.cjs (server-side config, not versioned)
- Docker: Environment variables via docker-compose or orchestration platform

## Webhooks & Callbacks

**Incoming Webhooks:**

**Chatwoot Webhook (maria-claude):**
- Endpoint: `POST /webhook/chatwoot`
- Payload: ChatwootWebhookPayload
- Processing: `shouldProcessWebhook()` checks message type
- Deduplication: In-memory Set<number> with 1-minute TTL
- Fields extracted: content, attachments (audio/images), conversation_id, contact_id, account_id
- Flow: Webhook → shouldProcessWebhook() → extractMessageContent() → agent.runWorkflow() → sendToChatwoot()
- Implementation: `maria-claude/src/server.ts` line 80+, `maria-claude/src/chatwoot.ts`

**ElevenLabs Tool Call Webhook (maria-voz):**
- Endpoint: `POST /webhook/:toolName`
- Payload: Tool parameters in request body
- Auth: Optional header `x-elevenlabs-secret`
- Response format: { tool_call_id, result, action?, metadata? }
- Implementation: `maria-voz/src/server.ts` line 93+

**Outgoing Callbacks:**

**Chatwoot Message Posting:**
- Endpoint: `POST ${CHATWOOT_BASE_URL}/api/v1/accounts/${accountId}/conversations/${conversationId}/messages`
- Auth: Header `api_access_token: ${CHATWOOT_API_TOKEN}`
- Payload: { content: string, message_type: "outgoing", private: false }
- Implementation: `maria-claude/src/chatwoot.ts` sendToChatwoot()
- Used for: Posting agent responses back to customer conversations

**Conversation Status Updates:**
- Function: updateConversationStatus() in `maria-claude/src/chatwoot.ts`
- Updates: Conversation labels, resolution status
- Purpose: Marking tickets as created/resolved in Chatwoot

## Rate Limiting & Throttling

**CEA API (src/tools.ts):**
- fetchWithRetry implementation:
  - Max retries: 3
  - Base delay: 1000ms (increases per attempt: 1s, 2s, 3s)
  - Timeout: 30 seconds per request
  - Exponential backoff on failure

**Chatwoot Webhook:**
- Message deduplication via in-memory Set<number>
- 1-minute TTL to prevent duplicate processing
- Implementation: `maria-claude/src/server.ts`

**OpenAI/Anthropic:**
- Standard API rate limits apply (configured in API accounts)
- No client-side rate limiting detected

## Security Considerations

**API Keys:**
- Stored in environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, CHATWOOT_API_TOKEN)
- CEA SOAP credentials hardcoded in SOAP builders (security concern - should be env vars)

**Network:**
- HTTPS for all external APIs (OpenAI, Anthropic, Chatwoot, ElevenLabs)
- Optional HTTP proxy for CEA API (CEA_PROXY_URL) for IP-whitelisted access

**Data Access:**
- PostgreSQL connection pooling with configurable max connections (PGPOOL_MAX)
- No encryption at rest detected
- No SQL injection protection beyond pg parameterized queries

**Authentication:**
- WSSE UsernameToken for CEA SOAP (basic auth-like, not encrypted)
- API token-based for Chatwoot (bearer token pattern)
- ElevenLabs webhook optional secret header

---

*Integration audit: 2026-02-03*
