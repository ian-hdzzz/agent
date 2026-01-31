# External Integrations

**Analysis Date:** 2026-01-31

## APIs & External Services

**CEA SOAP Web Services:**
- Service: CEA (Comisión Estatal del Agua) Querétaro SOAP API
- What it's used for: Customer account information, water consumption history, outstanding debt, contract details, account status
- Endpoint: https://aquacis-cf.ceaqueretaro.gob.mx/Comercial/services
  - InterfazOficinaVirtualClientesWS - Account/contract queries
  - InterfazGenericaGestionDeudaWS - Debt/consumption information
  - InterfazGenericaContratacionWS - Contract operations
- SDK/Client: undici (HTTP with proxy support) + manual SOAP envelope construction
- Auth: WSSE Username/Password token in SOAP headers (hardcoded: Username="WSGESTIONDEUDA", Password="WSGESTIONDEUDA")
- Implementation files:
  - `src/tools.ts` - SOAP builders and fetch with retry logic
  - `maria-claude/src/tools.ts` - SOAP API integration
  - `maria-claude/src/skills/contratos.ts`, `facturacion.ts`, `consultas.ts`, `consumos.ts`

**OpenAI API:**
- Service: OpenAI (GPT models, Whisper transcription)
- What it's used for: Chat completions (gpt-4o-mini, gpt-4.1), audio transcription, image analysis
- SDK/Client: openai 4.77.0
- Auth: OPENAI_API_KEY environment variable
- Implementation files:
  - `src/agent.ts` - Agent framework integration
  - `maria-claude/src/media.ts` - Whisper transcription for audio attachments
  - Model versions used: gpt-4o-mini (cea-agent-server), gpt-4.1 (legacy gpt-4.1-mini classifier)

**Anthropic Claude API:**
- Service: Anthropic Claude API
- What it's used for: Main agent reasoning and skill classification, multi-turn conversations
- SDK/Client: @anthropic-ai/sdk 0.71.2
- Auth: ANTHROPIC_API_KEY environment variable
- Implementation files:
  - `maria-claude/src/agent.ts` - Main workflow with skill routing
  - `maria-interno/src/agent.ts` - Internal ticket agent
- Features: Messages API, tool use, vision (for image attachments)

## Data Storage

**Databases:**

**PostgreSQL - AGORA (Chatwoot):**
- Type: PostgreSQL 12+
- Purpose: Ticket storage, conversation tracking, customer/agent data (Chatwoot integration)
- Connection: Connection pooling via `pg` library
  - Config env vars: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE, PGPOOL_MAX (default 10)
  - Connection pool initialized: `const pgPool = new pg.Pool(PG_CONFIG)`
- Client: pg (node-postgres)
- ORM/Query Tool: Raw SQL queries via pg.Pool.query()
- Implementation files:
  - `src/tools.ts` - Ticket creation/updates, customer searches
  - `maria-claude/src/tools.ts` - Ticket operations, integration with Chatwoot
- Tables accessed:
  - tickets (CEA customer tickets)
  - contacts (customer contact info)
  - conversations (Chatwoot conversations)
  - messages (conversation messages)
  - agent_conversation_links (ticket-conversation mapping)

**PostgreSQL - Internal Tickets (Maria Interno):**
- Type: PostgreSQL 12+
- Purpose: Employee internal ticket system (separate schema in same database)
- Client: pg (node-postgres)
- Tables created by migration `maria-interno/migrations/001_create_internal_tickets.sql`:
  - internal_ticket_categories (9 categories: TI, RH, MNT, VEH, ALM, ADM, COM, JUR, SEG)
  - internal_ticket_subcategories (80+ subcategories)
  - employees (employee directory)
  - internal_tickets (main ticket storage with JSONB metadata)
  - Indexes on: folio, status, category_code, employee_email, created_at
- Implementation files:
  - `maria-interno/src/tools.ts` - Ticket CRUD operations

**File Storage:**
- Not explicitly implemented: Application relies on Chatwoot for file/media storage
- Media processing: Downloads attachments from Chatwoot URLs, passes to Whisper/Claude Vision

**Caching:**
- None detected in production code
- In-memory conversation store with 1-hour TTL (cleanup every 5 minutes)
  - `src/agent.ts`: conversationStore Map<string, ConversationEntry>
  - `maria-claude/src/agent.ts`: conversationStore Map<string, ConversationEntry>

## Authentication & Identity

**Auth Provider:**
- Custom / None for public APIs
- API key-based authentication (no user auth framework detected)

**Implementation:**
- CEA SOAP: Hardcoded WSSE credentials in SOAP envelope
- OpenAI: API key from environment variable
- Anthropic: API key from environment variable
- Chatwoot: API token from environment variable
- No JWT, OAuth, or session management detected

## Monitoring & Observability

**Error Tracking:**
- Not detected: No Sentry, Rollbar, or error tracking service configured

**Logs:**
- Approach: Console logging throughout codebase
  - Log levels: info, warn, error via console.log(), console.warn(), console.error()
  - Formatted with prefixes: [API], [Chatwoot], [Media], [Database], [Ticket], [Agent]
  - No log aggregation service detected
  - PM2 ecosystem config shows log files on production:
    - error_file: '/home/fcamacholombardo/logs/maria-claude-error.log'
    - out_file: '/home/fcamacholombardo/logs/maria-claude-out.log'

**Health Checks:**
- `/health` endpoint: Basic uptime check
- `/status` endpoint: Detailed system status (memory, uptime, agent health, Chatwoot connectivity)
  - Implementation: `src/server.ts`, `maria-claude/src/server.ts`

## CI/CD & Deployment

**Hosting:**
- Production: PM2 process manager (Linux server)
  - Config file: `maria-claude/ecosystem.config.cjs`
  - Deployment: Faruk's server at /home/fcamacholombardo/maria-claude
  - Instance: 1 (no clustering)
  - Auto-restart: enabled
  - Max memory: 500MB
  - Logging: Merged logs to file

**CI Pipeline:**
- Not detected: No GitHub Actions, GitLab CI, or other CI/CD automation configured

**Build Process:**
- Manual: `npm run build` (tsc compilation)
- Scripts defined in each package.json:
  - dev: `tsx watch src/` (development)
  - build: `tsc` (TypeScript compilation)
  - start: `node dist/` (production start)
  - typecheck: `tsc --noEmit` (validation)

## Environment Configuration

**Required env vars (by application):**

**cea-agent-server:**
```
OPENAI_API_KEY          # Required - OpenAI API key
PGHOST                  # Required - Database host
PGPORT                  # Required - Database port (default 5432)
PGUSER                  # Required - Database user
PGPASSWORD              # Required - Database password
PGDATABASE              # Required - Database name (default agora_production)
PGPOOL_MAX              # Optional - Connection pool max (default 10)
PORT                    # Optional - Server port (default 3000)
OPENAI_MODEL            # Optional - Model (default gpt-4o-mini)
CEA_PROXY_URL           # Optional - Proxy for CEA API (e.g., http://10.128.0.7:3128)
TEST_CONTRACT           # Optional - Test contract number
```

**maria-claude:**
```
ANTHROPIC_API_KEY       # Required - Anthropic API key
PGHOST                  # Required - Database host
PGPORT                  # Required - Database port
PGUSER                  # Required - Database user
PGPASSWORD              # Required - Database password
PGDATABASE              # Required - Database name
PGPOOL_MAX              # Optional - Connection pool max (default 10)
PORT                    # Optional - Server port (default 3000)
CEA_PROXY_URL           # Optional - Proxy for CEA API
CHATWOOT_BASE_URL       # Required - Chatwoot instance URL
CHATWOOT_API_TOKEN      # Required - Chatwoot API token for posting messages
OPENAI_API_KEY          # Optional - OpenAI Whisper for audio transcription
```

**maria-interno:**
```
ANTHROPIC_API_KEY       # Required - Anthropic API key
PGHOST                  # Required - Database host
PGPORT                  # Required - Database port
PGUSER                  # Required - Database user
PGPASSWORD              # Required - Database password
PGDATABASE              # Required - Database name
PGPOOL_MAX              # Optional - Connection pool max (default 10)
PORT                    # Optional - Server port (default 3001)
CHATWOOT_API_KEY        # Optional - Chatwoot API key
CHATWOOT_BASE_URL       # Optional - Chatwoot base URL
CHATWOOT_ACCOUNT_ID     # Optional - Chatwoot account ID
CHATWOOT_INBOX_ID       # Optional - Chatwoot inbox ID
```

**Secrets location:**
- Development: `.env` files (not committed, .gitignored)
- Production: PM2 ecosystem.config.cjs (hardcoded on server, not versioned)
- Example templates: `.env.example` files in each workspace

## Webhooks & Callbacks

**Incoming Webhooks:**

**Chatwoot Webhook (maria-claude):**
- Path: `POST /webhook/chatwoot`
- Payload type: ChatwootWebhookPayload
- Processing: `maria-claude/src/chatwoot.ts` shouldProcessWebhook()
- Triggers: Incoming customer messages in Chatwoot conversations
- Message deduplication: In-memory Set<number> with 1-minute TTL
- Fields extracted: message content, attachments (audio/images), conversation ID, contact ID, account ID
- Flow: Webhook → shouldProcessWebhook() → extractMessageContent() → agent.runWorkflow() → sendToChatwoot()
- Implementation: `maria-claude/src/server.ts` line 80+

**Outgoing Callbacks:**

**Chatwoot Message Posting:**
- Endpoint: `POST ${CHATWOOT_BASE_URL}/api/v1/accounts/${accountId}/conversations/${conversationId}/messages`
- Auth: Header `api_access_token: ${CHATWOOT_API_TOKEN}`
- Payload: { content: string, message_type: "outgoing", private: false }
- Implementation: `maria-claude/src/chatwoot.ts` sendToChatwoot()
- Used to post agent responses back to customer conversations

**Conversation Status Updates:**
- Function: updateConversationStatus() in `maria-claude/src/chatwoot.ts`
- Updates: Conversation labels, resolution status after ticket creation
- Implementation: Maps to Chatwoot conversation resource

## Rate Limiting & Throttling

- Not explicitly implemented in code
- CEA API: Uses fetchWithRetry with exponential backoff
  - Max retries: 3
  - Base delay: 1000ms, increases per attempt
  - Timeout: 30 seconds per request

## Security Considerations

**API Keys:**
- Stored in environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, CHATWOOT_API_TOKEN)
- CEA SOAP credentials: Hardcoded in SOAP envelope (security concern)

**Network:**
- Optional proxy support for CEA API (for whitelisted IP access scenarios)
- HTTPS for external APIs (OpenAI, Anthropic, Chatwoot)

**Data Access:**
- Database: PostgreSQL connection pooling with configurable max connections
- No encryption at rest detected for PostgreSQL

---

*Integration audit: 2026-01-31*
