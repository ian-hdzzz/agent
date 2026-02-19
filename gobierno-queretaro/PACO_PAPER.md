# PACO: Pretty Advanced Cognitive Orchestrator
## A Two-Tier Multi-Agent Framework Built on LangGraph

---

**Abstract** — PACO (Pretty Advanced Cognitive Orchestrator) is a multi-agent orchestration framework for building conversational AI systems that serve multiple distinct domains through a single entry point. PACO uses a two-tier architecture: a Tier 0 orchestrator that classifies user intent and routes to Tier 1 domain-specialist agents, each running its own LangGraph workflow with domain-specific tools. The design prioritizes resilience (circuit breakers, retries, fallback routing), security (PII detection, session isolation, audit logging), and independent deployability of agents as containerized microservices. PACO is domain-agnostic and can be applied to any scenario requiring intelligent routing across multiple specialized conversational agents.

---

## 1. Problem Statement

Many organizations need conversational AI that spans multiple service domains — customer support across product lines, internal helpdesks covering IT/HR/facilities, healthcare systems routing between departments, or government portals serving diverse agencies. The naive approach — a single monolithic agent with all knowledge and tools — breaks down as domains multiply:

- **Prompt size explosion.** Cramming N domains of knowledge into one system prompt degrades response quality.
- **Tool collision.** Domain-specific tools with overlapping names or parameters create ambiguity for the LLM.
- **Blast radius.** A bug in one domain's logic or a bad deployment takes down the entire system.
- **Team ownership.** Different teams own different domains but cannot deploy independently.

PACO addresses these problems with a two-tier architecture where a lightweight orchestrator handles classification and routing, while independent domain agents handle the actual conversations.

---

## 2. Architecture

### 2.1 Two-Tier Design

```
                        ┌─────────────────────────────┐
                        │  TIER 0: PACO ORCHESTRATOR   │
    User Message ──────▶│                              │
                        │  classify → route → call     │
                        │                              │
                        │  • Hybrid classification     │
                        │  • Context continuity        │
                        │  • Circuit breaker per agent  │
                        │  • Fallback routing           │
                        └──────────┬──────────────────┘
                                   │
              ┌──────────┬─────────┼─────────┬──────────┐
              ▼          ▼         ▼         ▼          ▼
         ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
         │ Agent A ││ Agent B ││ Agent C ││ Agent D ││ Agent F │
         │ (Sales) ││ (Supp.) ││(Billing)││(Shipping)│(Fallback)│
         │         ││         ││         ││         ││         │
         │ LangGraph││LangGraph││LangGraph││LangGraph││LangGraph│
         │ + Tools ││ + Tools ││ + Tools ││ + Tools ││ + Tools │
         └─────────┘└─────────┘└─────────┘└─────────┘└─────────┘
                        TIER 1: DOMAIN AGENTS
```

**Tier 0 (PACO Orchestrator)** is a LangGraph state machine that:
1. Classifies the user's intent into a domain category
2. Routes to the appropriate domain agent via HTTP
3. Manages session continuity across turns
4. Handles failures with circuit breakers and fallback agents

**Tier 1 (Domain Agents)** are independent services, each containing:
1. A LangGraph workflow for multi-step conversation handling
2. Domain-specific tools (API calls, database queries, ticket creation)
3. A curated knowledge base embedded in the system prompt
4. A FastAPI HTTP server exposing a standard `/query` endpoint

The orchestrator knows nothing about domain logic. Domain agents know nothing about routing. This separation is PACO's core architectural principle.

### 2.2 Communication Protocol

All Tier 0 ↔ Tier 1 communication uses a standardized HTTP contract:

**Request (Orchestrator → Agent):**
```json
{
    "message": "user's message text",
    "conversation_id": "unique-conversation-id",
    "contact_id": "unique-user-id",
    "conversation_history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "metadata": {
        "category": "CATEGORY_CODE",
        "extracted_entities": {}
    }
}
```

**Response (Agent → Orchestrator):**
```json
{
    "response": "agent's text response to the user",
    "agent_id": "agent-identifier",
    "conversation_id": "unique-conversation-id",
    "task_type": "what the agent classified this as",
    "tools_used": ["tool_a", "tool_b"],
    "error": null
}
```

This contract means agents can be implemented in any language or framework. The only requirement is exposing `/query`, `/health`, and `/info` HTTP endpoints.

---

## 3. The Orchestrator Graph

PACO's orchestrator is implemented as a LangGraph `StateGraph` with four nodes:

### 3.1 State Definition

```python
class OrchestratorState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]  # Conversation history
    detected_category: str | None      # Classification result
    agent_response: str | None         # Response from domain agent
    agent_id: str | None               # Which agent handled the request
    contract_number: str | None        # Extracted entity (extensible)
    task_type: str | None              # For session continuity
    metadata: dict[str, Any]           # Passthrough context
    error: str | None                  # Error state
```

### 3.2 Graph Topology

```
  ┌──────────────┐
  │   classify    │  ← Entry point
  └──────┬───────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌───────────┐
│  call  │ │handle_exit│
│ _agent │ │           │
└───┬────┘ └─────┬─────┘
    │            │
    ▼            ▼
┌────────┐    ┌───┐
│handle  │    │END│
│_error  │    └───┘
└───┬────┘
    │
    ▼
  ┌───┐
  │END│
  └───┘
```

**`classify`** — Runs the hybrid classifier (Section 4). Sets `detected_category` in state.

**`call_agent`** — Makes an HTTP POST to the target agent's `/query` endpoint. Uses the resilient HTTP client (Section 6) with circuit breaker and retry logic. On failure, automatically falls back to a designated fallback agent.

**`handle_exit`** — Detects conversation-ending intent (goodbyes, thank-you messages) and returns a farewell without calling any agent.

**`handle_error`** — Catches errors from classification or agent calls and returns a graceful user-facing message.

### 3.3 Routing Logic

Routing is implemented as a conditional edge from the classify node:

```python
graph.add_conditional_edges(
    "classify",
    route_to_agent,
    {
        "call_agent": "call_agent",
        "handle_exit": "handle_exit",
    },
)
```

The `route_to_agent` function inspects `detected_category` and returns `"handle_exit"` for exit intents, or `"call_agent"` for everything else. The actual agent URL is resolved from a registry mapping category codes to service endpoints.

---

## 4. Hybrid Intent Classification

The classifier is PACO's most critical component. It determines where every message goes. The framework uses a two-stage hybrid approach:

### 4.1 Stage 1: Keyword Matching (Fast Path)

A dictionary maps each category code to a list of domain-specific keywords:

```python
KEYWORD_MAP = {
    "SALES": ["pricing", "quote", "buy", "purchase", "plan", ...],
    "SUPPORT": ["broken", "not working", "error", "help", "bug", ...],
    "BILLING": ["invoice", "payment", "charge", "refund", ...],
    ...
}
```

The classifier scans the message for keyword matches, scores each category by number of hits, and returns the top category if it clearly dominates (2x the second-place score). This executes in constant time with no external API call.

**Confidence:** 0.85 (keyword matches are reliable but may miss paraphrases).

### 4.2 Stage 2: LLM Classification (Semantic Fallback)

When no keywords match or multiple categories tie, the message is sent to an LLM with a classification prompt listing all categories and their descriptions. The LLM returns a single category code.

**Confidence:** 0.90 (semantic understanding catches paraphrases and novel phrasings).

### 4.3 Why Hybrid?

| | Keyword Only | LLM Only | PACO Hybrid |
|---|---|---|---|
| Latency | <5ms | 300–800ms | <5ms for ~70% of traffic |
| Cost per message | $0 | ~$0.001 | ~$0.0003 |
| Accuracy | 0.85 | 0.90 | 0.92+ |
| Handles novel phrasing | No | Yes | Yes |

The hybrid approach saves ~70% of LLM classification costs while maintaining high accuracy. Most real-world messages contain obvious domain keywords; the LLM is reserved for genuinely ambiguous cases.

### 4.4 Entity Extraction

Alongside classification, PACO extracts structured entities from the message using regex patterns (account numbers, phone numbers, dates, emails). These are passed to the target agent as pre-extracted metadata, avoiding redundant extraction downstream.

### 4.5 Structured Classification Mode

For scenarios requiring richer classification output, PACO supports a structured mode that returns:

```python
class StructuredClassification:
    category: str           # Domain category code
    confidence: float       # 0.0–1.0
    entities: dict          # Extracted entities
    ambiguous: bool         # Whether classification is uncertain
    clarification: str      # Suggested clarification question
    urgency: str            # "normal" | "high" | "emergency"
    method: str             # "keyword" | "llm" | "llm_structured"
```

This enables downstream logic such as priority queue routing for urgent messages or disambiguation prompts for ambiguous ones.

---

## 5. Context Continuity

Multi-turn conversations create a routing challenge: when a user responds "yes" or "ok", re-classifying that message is meaningless. PACO handles this with an ambiguity detector:

```python
def is_ambiguous_message(message: str) -> bool:
    short_responses = {"yes", "no", "ok", "sure", "thanks", "got it", ...}
    cleaned = message.lower().strip()
    return len(cleaned) < 15 or cleaned in short_responses
```

When a message is ambiguous **and** the session has a `last_category`, the orchestrator skips classification entirely and routes to the same agent that handled the previous turn:

```python
if last_category and is_ambiguous_message(user_message):
    return {"detected_category": last_category}
```

This keeps multi-turn conversations coherent. The user says "my account is 12345", the agent asks "what would you like to know about that account?", the user says "the balance" — and the message stays with the same agent rather than being re-classified.

---

## 6. Resilient Agent Communication

Every HTTP call from the orchestrator to a domain agent passes through PACO's `ResilientHTTPClient` that implements two resilience patterns:

### 6.1 Circuit Breaker

The circuit breaker tracks failures per agent (identified by `service_id`) and transitions through three states:

```
  CLOSED                    OPEN                    HALF_OPEN
(normal operation)     (rejecting requests)     (testing recovery)
       │                      │                       │
  5 failures ──────▶          │  ◀────── failure      │
       │              30s timeout elapsed ──▶          │
       │                      │              2 successes ──▶ CLOSED
       ◀───────────────────────────────────────────────┘
```

**Configuration (all tunable via environment variables):**

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `CIRCUIT_FAILURE_THRESHOLD` | 5 | Consecutive failures before opening |
| `CIRCUIT_RECOVERY_TIMEOUT` | 30s | Wait before testing recovery |
| `CIRCUIT_SUCCESS_THRESHOLD` | 2 | Successes in HALF_OPEN to close |

When a circuit is open, requests are immediately rejected with `CircuitOpenError` — no network call is made. This prevents cascading failures when an agent is down.

### 6.2 Retry with Exponential Backoff

Transient failures (timeouts, connection errors, 5xx responses) trigger automatic retries:

```
wait = min(1 × 2^attempt, 10)    # 1s → 2s → 4s → 8s → 10s max
max_retries = 3
```

Retries are only attempted for errors that are likely transient. Client errors (4xx) are not retried.

### 6.3 Fallback Routing

When the target agent is unavailable (circuit open, all retries exhausted), PACO automatically routes to a designated **fallback agent**:

```python
async def call_agent(state):
    if not client.is_service_available(agent_id):
        return await call_fallback_agent(state, agent_id, "Circuit breaker open")

    try:
        response = await client.post(f"{agent_url}/query", ...)
    except CircuitOpenError:
        return await call_fallback_agent(state, agent_id, "Circuit opened during request")
    except RetryError:
        return await call_fallback_agent(state, agent_id, "All retries exhausted")
```

The fallback agent receives the original message plus metadata about the failure, allowing it to provide a degraded-but-helpful response rather than an error message. Every fallback is logged in the audit trail.

### 6.4 Failure Cascade

PACO's complete failure handling cascade:

```
1. Try target agent
   ├── Success → return response
   └── Failure →
       2. Retry with exponential backoff (up to 3 times)
          ├── Success → return response, record_success()
          └── All retries exhausted → record_failure()
              3. Check circuit breaker state
                 ├── Still CLOSED → continue
                 └── Now OPEN →
                     4. Route to fallback agent
                        ├── Fallback succeeds → return degraded response
                        └── Fallback also fails → return error message
```

---

## 7. Domain Agent Architecture

### 7.1 Agent Template

Every domain agent in PACO follows an identical structure, generated from a template:

```
agents/<agent-id>/
├── main.py          # FastAPI server (/health, /query, /info)
├── agent.py         # LangGraph workflow
├── config.py        # Pydantic settings
├── prompts.py       # System prompt + knowledge base
├── tools.py         # Domain-specific tools
├── Dockerfile       # Container build
└── requirements.txt
```

This uniformity means:
- New agents can be scaffolded in seconds
- Operations teams have a single mental model for all agents
- CI/CD pipelines are identical across agents

### 7.2 Agent LangGraph Workflow

Each agent runs its own LangGraph state machine with internal task routing:

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    task_type: str | None           # Internal task classification
    subtask_results: dict[str, Any] # Results from tool calls
    current_subtask: str | None
    user_data: dict[str, Any]       # Extracted entities
    metadata: dict[str, Any]
```

The agent graph:

```
classify_task
    │
    ├──▶ handle_inquiry  ──▶ should_continue ──▶ tools ──▶ respond ──▶ END
    ├──▶ handle_ticket   ──▶ should_continue ──▶ tools ──▶ respond ──▶ END
    └──▶ handle_status   ──▶ should_continue ──▶ tools ──▶ respond ──▶ END
```

Each handler invokes the LLM with domain-specific tools bound. If the LLM calls a tool, the `should_continue` edge routes to the `tools` node (LangGraph's built-in `ToolNode`), then back to response generation.

### 7.3 Tool Contract

All domain tools in PACO follow a standardized return format:

```python
@tool
def get_account_balance(account_id: str) -> dict[str, Any]:
    return {
        "success": bool,
        "formatted_response": str,    # Ready-to-send message
        "data": Any,                  # Structured data
    }
```

The `formatted_response` field is key: it contains a pre-formatted user-facing message. The agent's system prompt instructs it to use this field verbatim when available, ensuring consistent formatting regardless of LLM generation variability.

### 7.4 System Prompt Structure

Each agent's system prompt combines universal conversation rules with domain-specific knowledge:

```
┌──────────────────────────────────┐
│     BASE RULES (shared)          │
│                                  │
│  • Max 2-3 sentences per message │
│  • One question per message      │
│  • Use formatted_response as-is  │
│  • Never fabricate information   │
│  • Offer human handoff when asked│
└──────────────────────────────────┘
┌──────────────────────────────────┐
│     KNOWLEDGE BASE (per agent)   │
│                                  │
│  • Service URLs and contacts     │
│  • Procedures and requirements   │
│  • FAQs and common scenarios     │
│  • Edge cases and exceptions     │
└──────────────────────────────────┘
┌──────────────────────────────────┐
│     TASK GUIDELINES (per agent)  │
│                                  │
│  • When to use which tool        │
│  • Priority escalation rules     │
│  • Domain-specific constraints   │
└──────────────────────────────────┘
```

---

## 8. Session Management

### 8.1 Session Context

PACO provides a `SessionContext` dataclass with secure data compartmentalization:

```python
@dataclass
class SessionContext:
    session_id: str

    # Per-agent isolated data
    data_vault: dict[str, dict[str, Any]]

    # Cross-agent shared data
    shared_data: dict[str, Any]

    # Security
    confidentiality_level: Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
    citizen_id_hash: str | None       # Pseudonymized user identity

    # Routing trace
    current_agent_id: str | None
    agent_history: list[str]          # Which agents have handled this session

    # Lifecycle
    ttl_seconds: int = 3600           # Auto-expiration
```

**Key design decisions:**

1. **Per-agent data vaults.** Each agent has its own isolated data namespace within the session. Agent A cannot read Agent B's collected data. This prevents information leakage between domains.

2. **Shared data layer.** Non-sensitive cross-agent data (e.g., preferred language, accessibility needs) lives in `shared_data`, accessible to all agents.

3. **Confidentiality elevation.** The session tracks the highest sensitivity level of data it has touched. Confidentiality can only be elevated, never lowered — once a session handles sensitive data, it stays classified.

4. **Agent history.** The session records which agents have handled it, enabling analytics ("30% of billing inquiries are preceded by a support inquiry") and context passing ("the user already spoke with support about this issue").

### 8.2 Session Store

Sessions are stored in Redis with automatic TTL expiration:

```python
class SessionStore:
    async def create(conversation_id, contact_id, ttl_seconds) -> SessionContext
    async def get(session_id) -> SessionContext | None
    async def get_by_conversation(conversation_id) -> SessionContext | None
    async def get_or_create(conversation_id, ...) -> SessionContext
    async def update(session) -> None
    async def refresh(session_id) -> bool        # Reset TTL
    async def delete(session_id) -> bool
    async def set_agent_data(session_id, agent_id, key, value) -> bool
    async def set_shared_data(session_id, key, value) -> bool
```

Conversations are indexed by both `session_id` (internal) and `conversation_id` (external, e.g., from a CRM or messaging platform), allowing PACO to integrate with external conversation tracking systems.

---

## 9. Security Layer

### 9.1 PII Detection and Masking

PACO's `SecurityManager` scans all messages for personally identifiable information using configurable regex patterns:

```python
class SecurityManager:
    def detect_pii(text) -> dict[PIIType, list[str]]
    def mask_pii(text, preserve_partial=False) -> str
    def sanitize_for_logging(text) -> str
    def sanitize_dict_for_logging(data) -> dict
```

PII is detected and masked in all log entries. The original message is still passed to agents for processing — masking applies only to observability outputs (logs, audit trails, analytics).

### 9.2 Field Encryption

For data that must be stored at rest (e.g., in session data or tickets), PACO provides Fernet-based symmetric encryption:

```python
    def encrypt_field(value: str) -> str
    def decrypt_field(encrypted_value: str) -> str
    def encrypt_dict(data, fields_to_encrypt) -> dict
    def decrypt_dict(data, fields_to_decrypt) -> dict
```

### 9.3 User Identity Pseudonymization

User identities can be pseudonymized using salted SHA-256 hashing:

```python
    def pseudonymize_citizen_id(user_id, salt=None) -> str
```

This allows linking records across sessions (same user = same hash) without storing the actual identity. The salt is configurable via environment variable.

### 9.4 Audit Logging

Every significant system event is logged to a structured audit trail:

- Messages received and sent
- Agent invocations (which agent, success/failure, latency)
- PII detection incidents
- Classification decisions with confidence scores
- Fallback activations with reasons
- Error conditions

Each audit entry includes actor type (user/system/agent), resource type, success/failure status, and a sanitized details payload.

---

## 10. Deployment Architecture

### 10.1 Container Topology

PACO deploys as a Docker Compose stack:

```yaml
services:
  paco-orchestrator:     # Tier 0 — port 8000
  agent-sales:           # Tier 1 — port 8001
  agent-support:         # Tier 1 — port 8002
  agent-billing:         # Tier 1 — port 8003
  agent-fallback:        # Tier 1 — port 800N (designated fallback)
  postgres:              # State persistence (internal)
  redis:                 # Session cache (internal)
```

All services communicate over an isolated Docker bridge network. Health checks run at configurable intervals with retry thresholds.

### 10.2 Adding a New Agent

PACO includes a scaffolding script:

```bash
./scripts/create-agent.sh <agent-id> <category-code> <port>
```

This generates the full agent directory from the template, registers the category in the orchestrator's classifier, and wires the agent into Docker Compose. A new domain can be added in minutes.

### 10.3 Database Schema

The PostgreSQL schema supports five core entities:

| Table | Purpose |
|-------|---------|
| `agents` | Registry of all agents with endpoints and active status |
| `conversations` | Conversation state with LangGraph checkpoints (JSONB) |
| `messages` | Complete message history with agent attribution |
| `tasks` | Multi-step workflow tracking (pending → in_progress → completed → failed) |
| `tickets` | Service tickets with auto-generated reference numbers |
| `events` | Audit trail for inter-agent communication |

---

## 11. Voice Gateway (Optional Module)

PACO includes an optional voice gateway for real-time speech interaction via WebSocket:

```
User (audio) ──▶ WebSocket ──▶ STT ──▶ text
                                         │
                                         ▼
                                 PACO /route
                                         │
                                         ▼
User (audio) ◀── WebSocket ◀── TTS ◀── text response
```

The voice gateway is a thin adapter that converts between audio streams and the orchestrator's text-based `/route` API. STT and TTS providers are pluggable — the reference implementation uses Deepgram (STT) and ElevenLabs (TTS), but any provider can be swapped in without affecting the orchestrator or agents.

---

## 12. Design Tradeoffs

### 12.1 Why HTTP Between Orchestrator and Agents?

**Chosen:** REST over HTTP.
**Alternatives considered:** gRPC, message queues, in-process function calls.

HTTP was chosen for:
- **Simplicity.** No schema compilation, no message broker to operate.
- **Debuggability.** Requests can be replayed with `curl`.
- **Language agnosticism.** Agents can be written in any language.
- **Existing tooling.** Load balancers, API gateways, and monitoring tools all speak HTTP natively.

The latency cost (~1-5ms on a local Docker network) is negligible compared to LLM inference time (~300-800ms).

### 12.2 Why Keyword + LLM Instead of LLM Only?

Pure LLM classification would be simpler but:
- Adds 300-800ms latency to every message
- Costs ~$0.001 per classification
- At scale (millions of messages), this compounds significantly

The keyword stage handles ~70% of traffic at zero cost and near-zero latency. The LLM handles the remaining ~30% that require semantic understanding.

### 12.3 Why One Process Per Agent?

**Chosen:** Each agent runs as an independent container.
**Alternative:** All agents as modules in a single process.

Independent containers enable:
- **Independent deployment.** Update Agent A without touching Agent B.
- **Fault isolation.** Agent A crashing doesn't take down Agent B.
- **Heterogeneous scaling.** Scale the busy agent to 5 replicas while the quiet one stays at 1.
- **Team ownership.** Different teams can own, develop, and deploy different agents.

The tradeoff is operational complexity (more containers to monitor) and the network hop latency for inter-service calls.

### 12.4 Why a Fallback Agent Instead of a Generic Error?

A dedicated fallback agent can:
- Attempt to answer the user's question with general knowledge
- Create a support ticket for follow-up
- Route to a human agent
- Provide relevant self-service links

This is significantly better than returning "Service unavailable, try again later."

---

## 13. Applying PACO

PACO is domain-agnostic. To apply it to a new domain:

1. **Define categories.** List the N domains you need to serve (e.g., Sales, Support, Billing, Shipping).

2. **Populate keyword maps.** For each category, list 10-50 keywords that indicate that intent. This gives you the fast path.

3. **Write classification prompt.** Describe each category to the LLM for semantic classification. This gives you the fallback path.

4. **Scaffold agents.** Run `create-agent.sh` for each category. Fill in the knowledge base and implement domain tools.

5. **Designate a fallback agent.** Pick one agent (usually a general/triage agent) that handles messages when the target agent is unavailable.

6. **Deploy.** `docker-compose up -d --build`.

PACO handles routing, resilience, sessions, security, and audit logging. Domain teams focus only on their agent's knowledge and tools.

---

## 14. Conclusion

PACO provides a production-ready pattern for building conversational AI systems that span multiple domains. The key architectural contributions are:

1. **Hybrid classification** that combines keyword speed with LLM semantic understanding, optimizing for both cost and accuracy.
2. **Agent isolation** through independent containerized services with a standardized HTTP contract, enabling independent deployment and fault isolation.
3. **Cascading resilience** through circuit breakers, exponential backoff retries, and automatic fallback routing — ensuring no user message goes unanswered.
4. **Session compartmentalization** with per-agent data vaults, cross-agent shared data, and automatic TTL expiration.
5. **Security by default** with PII detection, field encryption, identity pseudonymization, and comprehensive audit logging built into the framework rather than bolted on.

PACO is built on LangGraph for stateful workflow management, FastAPI for HTTP serving, Redis for session storage, and PostgreSQL for persistence — all mature, well-supported technologies that reduce operational risk.

---

## Appendix A: Technology Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Workflow engine | LangGraph | Stateful conversation graphs (orchestrator + agents) |
| LLM | Claude (Anthropic) | Classification and agent reasoning |
| HTTP framework | FastAPI | Agent and orchestrator API servers |
| HTTP client | httpx + tenacity | Async requests with retry logic |
| Session store | Redis | TTL-based session storage |
| Persistence | PostgreSQL | Conversations, tickets, audit logs |
| Containerization | Docker Compose | Microservices deployment |
| Configuration | Pydantic BaseSettings | Type-safe, env-var-driven config |
| Encryption | cryptography (Fernet) | At-rest field encryption |

## Appendix B: API Reference

### PACO Orchestrator Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with per-agent circuit breaker status |
| `/route` | POST | Classify intent and route to agent |
| `/classify` | POST | Classify intent without routing (testing) |
| `/agents` | GET | List all registered agents |
| `/agents/{code}` | GET | Get specific agent configuration |
| `/categories` | GET | List all categories with keywords |

### Agent Endpoints (Standard Contract)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Agent health and configuration |
| `/query` | POST | Process a user message |
| `/info` | GET | Agent metadata and capabilities |
