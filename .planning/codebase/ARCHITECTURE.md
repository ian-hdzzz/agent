# Architecture

**Analysis Date:** 2026-01-31

## Pattern Overview

**Overall:** Multi-agent routing system with classification-driven task distribution

**Key Characteristics:**
- Classification-first pattern: incoming messages are routed to specialized agents based on intent
- Conversation state management with in-memory store and optional Redis backing
- Direct database integration to PostgreSQL (Chatwoot/AGORA) and external CEA SOAP APIs
- AsyncLocalStorage context propagation for implicit conversation/ticket linking

## Layers

**Presentation/API Layer:**
- Purpose: HTTP endpoints for chat interactions and health monitoring
- Location: `src/server.ts` (CEA Agent), `maria-claude/src/server.ts` (Maria Claude Agent)
- Contains: Express routes, request validation, response formatting
- Depends on: Agent workflow, types
- Used by: Chatwoot webhooks, external API clients

**Classification Layer:**
- Purpose: Determine user intent and route to appropriate agent
- Location: `src/agent.ts` (lines 116-145, classificationAgent)
- Contains: Classification agent instance, schema validation (Zod)
- Depends on: OpenAI API (gpt-4.1-mini), conversation history
- Used by: Workflow router to select specialist agent

**Specialist Agent Layer:**
- Purpose: Handle domain-specific conversations using specialized prompts and tools
- Location: `src/agent.ts` (informacionAgent, pagosAgent, consumosAgent, fugasAgent, contratosAgent, ticketsAgent)
- Contains: 6 independent agents, each with custom system prompts and tool sets
- Depends on: Tools layer, conversation state
- Used by: Workflow dispatcher after classification

**Tools Layer (Native):**
- Purpose: Provide reliable, production-ready tools for agents
- Location: `src/tools.ts`
- Contains: 8 native tools with retry logic, error handling, proxy support
- Depends on: PostgreSQL driver (pg), undici fetch with proxy, Zod validation
- Used by: Specialist agents

**External Integration Layer:**
- Purpose: Connect to CEA SOAP API and Chatwoot database
- Location: `src/tools.ts` (fetchWithRetry, parseXMLValue functions), `maria-claude/src/chatwoot.ts`
- Contains: CEA API calls, XML response parsing, PostgreSQL connection pool
- Depends on: Environment variables (proxy, database credentials), HTTP client
- Used by: Tools layer

**Context Management Layer:**
- Purpose: Thread context through async operations without explicit passing
- Location: `src/context.ts`
- Contains: AsyncLocalStorage for Chatwoot conversation/contact IDs
- Depends on: Node.js async_hooks
- Used by: Tools (createTicketDirect) to link tickets automatically

**Conversation State Layer:**
- Purpose: Maintain message history and extracted metadata across requests
- Location: `src/agent.ts` (lines 39-75, conversationStore)
- Contains: In-memory Map of conversation entries with 1-hour TTL
- Depends on: None (in-memory only)
- Used by: Workflow to maintain context across multi-turn interactions

## Data Flow

**Primary Flow - Chat Request:**

1. HTTP POST to `/api/chat` with `{message, conversationId, contactId}`
2. Server validates input, extracts Chatwoot context
3. Classification agent analyzes message intent → returns category + confidence
4. Specialist agent selected based on classification
5. Specialist agent runs with conversation history + extracted tools
6. Tool calls execute against CEA API and/or PostgreSQL
7. Response aggregated from agent output
8. Conversation history updated with new messages and context

**Ticket Creation Flow:**

1. User intent classified as requiring ticket creation (fuga, recibo_digital, aclaraciones, etc.)
2. Specialist agent collects information through multi-turn conversation
3. Agent calls createTicketTool with CreateTicketInput
4. Tool retrieves Chatwoot context from AsyncLocalStorage
5. Creates ticket in PostgreSQL with automatic linking to conversation_id and contact_id
6. Returns ticket folio to agent for confirmation message

**API Data Flow (CEA SOAP):**

1. Tool (e.g., getDeudaTool) constructs SOAP request
2. fetchWithRetry with ProxyAgent (if CEA_PROXY_URL configured)
3. CEA API returns XML response
4. parseXMLValue extracts nested fields
5. Response validated against Zod schema
6. Data returned to agent formatted as readable text

## Key Abstractions

**Agent:**
- Purpose: Encapsulates a specialized conversational capability
- Examples: `pagosAgent`, `fugasAgent`, `contratosAgent` in `src/agent.ts`
- Pattern: OpenAI Agents SDK - stateless functions with tool access, instructions, and model config

**Tool:**
- Purpose: Represents a discrete action agents can invoke (CEA API query, database write, etc.)
- Examples: `getDeudaTool`, `createTicketTool`, `getConsumoTool` in `src/tools.ts`
- Pattern: Tool wrapper from @openai/agents with input schema (Zod), execution function, and auto-approval

**Conversation Entry:**
- Purpose: Tracks state for one conversation session
- Location: `src/agent.ts` interface ConversationEntry
- Fields: message history, last access time, extracted contract number, classification, Chatwoot IDs
- Pattern: Plain object with typed interfaces

**Skill (Maria Claude system):**
- Purpose: Maps AGORA category to agent capabilities
- Examples: `consultasSkill`, `facturacionSkill`, `contratosSkill` in `maria-claude/src/skills/*.ts`
- Pattern: Object containing code, system prompt, available tools, subcategories

## Entry Points

**CEA Agent Server:**
- Location: `src/server.ts`
- Triggers: HTTP POST /api/chat, /webhook, or legacy /chat endpoints
- Responsibilities: Request validation, error handling, response formatting, health/status reporting

**Maria Claude Server:**
- Location: `maria-claude/src/server.ts`
- Triggers: HTTP POST /api/chat, Chatwoot webhooks
- Responsibilities: Message classification, skill routing, Chatwoot integration

**Workflow Execution:**
- Location: `src/agent.ts` function `runWorkflow(input: WorkflowInput)`
- Triggers: Called by server handlers
- Responsibilities: Classification → routing → agent execution → response assembly

## Error Handling

**Strategy:** Try-catch at workflow level with graceful degradation

**Patterns:**
- fetchWithRetry: 3 attempts with exponential backoff for network calls
- Tool validation: Zod schemas catch invalid inputs before execution
- Agent errors: Caught in try-catch, return user-friendly Spanish messages
- Missing contract: Agents prompt for contract number rather than failing
- API timeout: 30-second AbortSignal on all fetch operations
- Server errors: Return 500 with error details in development, generic message in production

## Cross-Cutting Concerns

**Logging:**
- Request ID generated per request, threaded through console.log calls
- Tool invocations logged with [API] prefix
- Agent classification and output logged at workflow level

**Validation:**
- Input message length capped at 10,000 characters
- Conversation ID optional, generated if missing
- Tool inputs validated against Zod schemas before execution
- Contract numbers extracted via regex pattern (6+ digits)

**Authentication:**
- OPENAI_API_KEY required at startup (validated in server.ts lines 21-27)
- PostgreSQL credentials from environment variables
- No explicit auth for API endpoints (webhook model, rate limiting not enforced)

**Database Connections:**
- PostgreSQL connection pool with configurable max connections (default 10)
- Connection reused across requests, not closed per-request
- Ticket inserts include automatic timestamp fields from database

---

*Architecture analysis: 2026-01-31*
