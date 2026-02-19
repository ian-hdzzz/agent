## System Architecture & Resilience Audit Report

### Executive Summary

PACO is a well-designed two-tier multi-agent orchestration system with a solid foundation: hybrid intent classification, circuit breakers, session compartmentalization, and a consistent agent template pattern. However, the system has several critical gaps that undermine its production readiness: hardcoded confidence scores mask real classifier uncertainty, singleton patterns lack thread safety for async concurrency, the LangGraph orchestrator does not use checkpointing or persistence despite having PostgreSQL tables for it, and a broken import (`KEYWORD_MAP`) will crash the categories endpoint at runtime. The fallback architecture creates a single point of failure where all agent failures cascade to citizen-attention, which itself uses a `best_effort` SLA tier.

### Critical Findings

**CRIT-001: Broken Import - KEYWORD_MAP Does Not Exist**
- File: `gobierno-queretaro/orchestrator/main.py:781`
- Issue: The `_do_list_categories` function imports `KEYWORD_MAP` from `orchestrator.classifier`, but this name does not exist. The actual variable is `_STATIC_KEYWORD_MAP` (a private name). This will cause an `ImportError` at runtime when the `/categories` or `/v1/categories` endpoint is called.
- Impact: Any call to `/categories` or `/v1/categories` will return a 500 error. This is a live runtime bug.
- Recommendation: Change the import to either export `_STATIC_KEYWORD_MAP` as `KEYWORD_MAP` in `classifier.py`, or update `main.py:781` to use `_get_classifier_data().keyword_map` for dynamic-aware behavior.

**CRIT-002: LLM Classifier Returns Hardcoded Confidence Instead of Real Scoring**
- File: `gobierno-queretaro/orchestrator/classifier.py:564`
- Issue: The `llm_classify` function returns `confidence: 0.9` for any non-ATC classification and `confidence: 0.5` for ATC, regardless of how certain the LLM actually was. The structured classifier (`llm_classify_structured`) does request a confidence value from the LLM, but the primary `classify_intent` path uses the non-structured classifier, meaning all routing decisions in production operate on fake confidence scores.
- Impact: Downstream logic that relies on confidence (e.g., ambiguity detection, routing quality metrics, reward evaluation) is operating on fabricated data. Misrouted messages cannot be detected by confidence thresholds because the score is always either 0.9 or 0.5.
- Recommendation: Either (a) use the structured classifier as the default LLM path, or (b) parse the LLM response more carefully to derive a real confidence signal (e.g., check if the response contained exactly one category code vs. hedging language).

**CRIT-003: Singleton Patterns Are Not Thread-Safe in Async Context**
- File: `gobierno-queretaro/orchestrator/router.py:631-639`, `gobierno-queretaro/shared/utils/http_client.py:353-365`, `gobierno-queretaro/shared/context/session.py:497-505`, `gobierno-queretaro/shared/memory/engine.py:243-252`
- Issue: All singleton factories (`get_orchestrator`, `get_circuit_breaker`, `get_session_store`, `get_paco_memory`) use the classic `if None: create` pattern without any locking. In an async context with multiple concurrent requests (uvicorn workers), two coroutines can both see `None` and create duplicate instances simultaneously. For the circuit breaker, this means one coroutine's failure tracking is invisible to another's.
- Impact: Under concurrent load, circuit breaker state can be split across multiple instances, failure thresholds may never be reached, and sessions may be inconsistently created.
- Recommendation: Use `asyncio.Lock` for async-safe singleton initialization, or initialize all singletons during the lifespan startup (which is already partially done for some components but not enforced).

**CRIT-004: Circuit Breaker State Is In-Memory Only - Lost on Restart**
- File: `gobierno-queretaro/shared/utils/http_client.py:71`
- Issue: The `CircuitBreaker` stores all circuit state in a Python dictionary (`self._circuits: dict[str, CircuitStats]`). When the orchestrator restarts, all circuit state is lost. An agent that was failing and had its circuit open will immediately receive traffic again, potentially causing cascading failures. Additionally, in a multi-worker deployment, each worker has its own circuit state.
- Impact: Restart of orchestrator immediately sends traffic to a previously-failing agent. Multi-worker deployments have inconsistent circuit states.
- Recommendation: Persist circuit state in Redis (which is already available) with atomic increment operations for failure/success counts.

### High Priority Findings

**HIGH-001: Single Point of Fallback - All Failures Route to citizen-attention**
- File: `gobierno-queretaro/orchestrator/router.py:38`
- Issue: `FALLBACK_AGENT_CATEGORY = "ATC"` (citizen-attention) is the sole fallback for all 12 other agents. If citizen-attention itself is down, the only fallback is a generic error message (router.py:265-271). The citizen-attention agent has an SLA tier of `best_effort` (99% uptime from config.py:269), which is the lowest tier, yet it serves as the system-wide safety net.
- Impact: A citizen-attention outage means no fallback for any agent failure. The SLA tier mismatch means the most critical fallback path has the lowest availability guarantee.
- Recommendation: (a) Elevate citizen-attention to `critical` SLA tier, (b) implement a secondary fallback mechanism (e.g., a static response cache for common queries), (c) consider having the orchestrator generate a basic response using its own LLM access rather than depending on an external agent.

**HIGH-002: LangGraph Checkpointing Not Used Despite DB Schema Support**
- File: `gobierno-queretaro/orchestrator/router.py:516`, `gobierno-queretaro/PACO_PAPER.md:583`
- Issue: The PACO paper and DB schema mention `conversations` table with "LangGraph checkpoints (JSONB)" column. However, `build_orchestrator_graph()` compiles without a checkpointer: `self.app = self.graph.compile()` (router.py:516). Same applies to all agent graphs. This means LangGraph's built-in state persistence, interruption/resumption, and conversation replay are completely unused.
- Impact: If the orchestrator crashes mid-request, the conversation state is lost. There is no ability to resume or replay conversations from a checkpoint. The `conversations` DB table (mentioned in the paper) is either empty or not used.
- Recommendation: Add a PostgreSQL or Redis checkpointer to `graph.compile(checkpointer=...)` for at least the orchestrator graph. This enables conversation replay, debugging, and crash recovery.

**HIGH-003: New httpx.AsyncClient Created Per Request**
- File: `gobierno-queretaro/shared/utils/http_client.py:236`
- Issue: The `_make_request` method creates a new `httpx.AsyncClient` for every single request: `async with httpx.AsyncClient(timeout=self.timeout) as client:`. This means a new TCP connection pool is created and torn down for each request, losing connection reuse, keep-alive benefits, and adding connection establishment overhead.
- Impact: Under load, this creates excessive TCP connections to agent services, increases latency by 10-50ms per request, and may exhaust file descriptors. With 13 agents and retry logic (up to 3 attempts), a single user request could open 3+ TCP connections.
- Recommendation: Initialize `httpx.AsyncClient` once in `ResilientHTTPClient.__init__` and reuse it across requests. Add a proper `close()` method for cleanup.

**HIGH-004: Keyword Overlap Between Categories Creates Misrouting**
- File: `gobierno-queretaro/orchestrator/classifier.py:43-171`
- Issue: Several categories have keyword overlap that the 2x threshold in `keyword_classify` (line 484) may not resolve:
  - "transporte" appears in TRA but "vehiculo" concepts overlap with VEH (TRA line 69: "tramites vehiculo transporte")
  - "apoyo" appears in both PSI ("apoyo emocional") and IQM ("apoyo a mujeres") and SOC ("apoyo economico")
  - "salud mental" in PSI overlaps with "salud" concepts that could appear in IQM health queries
  - "trabajo" in LAB could conflict with VIV ("vivienda trabajadores estado")
  - Numbers like "4421015205" in ATC could match contract number regex in CEA
- Impact: Messages containing overlapping keywords will tie or near-tie, falling through to the LLM classifier (adding 300-800ms latency). Messages like "apoyo para mujeres" could score equally for PSI, IQM, and SOC.
- Recommendation: Add negative keywords (exclusion lists) per category, implement keyword weighting (multi-word phrases score higher), and add integration tests for known ambiguous messages.

**HIGH-005: Conversation Snapshot Upsert Has Wrong Conflict Target**
- File: `gobierno-queretaro/shared/memory/store.py:277-287`
- Issue: The `save_snapshot` method uses `ON CONFLICT (id) DO NOTHING`, but `id` is an auto-generated UUID primary key. Since a new UUID is generated for each insert, the conflict clause will never trigger. The method should conflict on `conversation_external_id` to properly upsert snapshots for the same conversation.
- Impact: Every call to `save_snapshot` for the same conversation creates a new row instead of updating the existing one. Over time, this creates duplicate snapshot records, inflating storage and causing the nightly summarizer to process duplicate conversations.
- Recommendation: Change to `ON CONFLICT (conversation_external_id) DO UPDATE SET message_history = $3::jsonb, agents_involved = $4, categories_involved = $5`.

### Medium Priority Findings

**MED-001: Agent Template Divergence - Vehicles/Women/Citizen Don't Use Template Features**
- File: `gobierno-queretaro/agents/vehicles/main.py`, `gobierno-queretaro/agents/women-iqm/main.py`, `gobierno-queretaro/agents/citizen-attention/main.py`
- Issue: The agent template (`_template/main.py`) includes self-registration with orchestrator, heartbeat loop, persistent memory initialization, metrics endpoint, and memory endpoint. The actual agent implementations (vehicles, women-iqm, citizen-attention) do NOT use the template at all - they each have a hand-written `main.py` that omits:
  - Self-registration (`register_with_orchestrator` / `start_heartbeat_loop`)
  - PacoMemory initialization and recall
  - Memory endpoint (`/memory/{contact_id}`)
  - Metrics endpoint (`/metrics`)
  - AgentLightning tracing (present in template `agent.py` but absent from vehicles/women/citizen `agent.py`)
- Impact: Agents do not self-register with the orchestrator's dynamic registry, meaning the orchestrator always falls back to static config. Memory recall is not injected into agent prompts. No distributed tracing for agent-level operations. Health sweeps will deactivate agents that never send heartbeats.
- Recommendation: Have all agents extend/import from the template rather than copy-paste-and-diverge. Consider making the template a proper base class.

**MED-002: Vehicles Agent Config Missing Capabilities/Registration Metadata**
- File: `gobierno-queretaro/agents/vehicles/config.py`
- Issue: `VehiclesAgentSettings` is a minimal config class that lacks the `AgentCapabilities` metadata (keywords, classification_hint, category_description), `version`, `sla_tier`, `confidentiality_level`, `handles_pii`, `memory_enabled`, and `to_registration_payload()` fields that the template config provides. This means the vehicles agent cannot self-register with the orchestrator even if the registration code was added.
- Impact: The dynamic classifier cannot build category data from this agent. The health endpoint returns minimal data. SLA-aware routing cannot prioritize this agent.
- Recommendation: Use the template `AgentSettings` base class and extend it for vehicle-specific settings.

**MED-003: Context Continuity Edge Case - Topic Switch After Ambiguous Message**
- File: `gobierno-queretaro/orchestrator/router.py:108-127`
- Issue: The context continuity logic in `classify_intent_node` checks `is_ambiguous_message(last_message)` and routes to `last_category` if true. However, this creates an edge case: if a user sends an ambiguous message like "si" to confirm something with one agent, then on the NEXT turn sends a NEW topic, the `last_category` from the session is still set. If that new message happens to be short (< 15 chars, e.g., "mi agua"), it will be misrouted to the previous agent instead of being reclassified. The check at line 112 only requires `last_category` to exist AND the message to be ambiguous - there is no decay/timeout on `last_category`.
- Impact: Short but topically distinct messages following a context switch get routed to the wrong agent. Example: user talks to VEH about plates, says "gracias", then asks "mi agua" (9 chars, < 15) -- routes to VEH instead of CEA.
- Recommendation: Add a time-based decay to `last_category` (e.g., clear after 5 minutes of inactivity), or combine the ambiguity check with a quick keyword scan to detect obvious topic changes.

**MED-004: Session Store Read-Modify-Write Race Condition**
- File: `gobierno-queretaro/shared/context/session.py:443-468`
- Issue: The `set_agent_data` and `set_shared_data` methods perform read-modify-write without atomicity: they `get()` the session, modify it in Python, then `update()` it back to Redis. Two concurrent requests for the same conversation can read the same session, modify different fields, and the last writer wins - overwriting the first writer's changes.
- Impact: Under concurrent load, session data (message history, agent visits, task types) can be silently lost. This is especially problematic for the `_do_route` function in main.py which reads, modifies, and writes session data for every request.
- Recommendation: Use Redis transactions (MULTI/EXEC) or Lua scripting for atomic read-modify-write operations. Alternatively, use Redis HSET for individual field updates instead of serializing the entire session.

**MED-005: Anthropic Client Created Per LLM Call**
- File: `gobierno-queretaro/orchestrator/classifier.py:535`, `gobierno-queretaro/agents/vehicles/agent.py:63-69`
- Issue: `llm_classify()` creates a new `Anthropic()` client for every classification call. Similarly, each agent's `get_llm()` creates a new `ChatAnthropic()` instance per handler invocation. These clients establish new HTTP connections to Anthropic's API each time.
- Impact: Connection establishment overhead on every LLM call. Under load, this can cause connection exhaustion or rate limiting from Anthropic's side due to many concurrent connections.
- Recommendation: Create the client once at module level or in the singleton, not per-call.

**MED-006: `datetime.utcnow()` Deprecated - Should Use `timezone.utc`**
- File: `gobierno-queretaro/shared/context/session.py:62-63`, `gobierno-queretaro/shared/utils/http_client.py:44,96,100`
- Issue: Multiple files use `datetime.utcnow()` which is deprecated in Python 3.12+ and returns a naive datetime. The memory store correctly uses `timezone.utc` in `store.py:343`, but the circuit breaker and session context do not.
- Impact: Naive datetimes can cause subtle timezone bugs when comparing with timezone-aware datetimes from PostgreSQL. Python 3.12+ emits deprecation warnings.
- Recommendation: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`.

### Low Priority / Improvements

**LOW-001: CORS Configured as allow_origins=["*"] on All Services**
- File: `gobierno-queretaro/orchestrator/main.py:392-397`, `gobierno-queretaro/agents/vehicles/main.py:91-97`, and all agent main.py files
- Issue: Every service has `allow_origins=["*"]` with `allow_credentials=True`. While agents communicate over an internal Docker network, the orchestrator is the external-facing API.
- Impact: Any website can make credentialed cross-origin requests to the orchestrator. This is a security concern if the orchestrator is exposed to the internet.
- Recommendation: Restrict `allow_origins` to the actual frontend domains for the orchestrator. Internal agent-to-agent communication does not need CORS.

**LOW-002: Rate Limiter Uses IP-Based Key Only**
- File: `gobierno-queretaro/orchestrator/main.py:57`
- Issue: `limiter = Limiter(key_func=get_remote_address)` means rate limiting is per-IP only. In production behind a load balancer, all requests may appear from the same IP unless `X-Forwarded-For` is properly configured.
- Impact: Either all users share a rate limit (if behind proxy without forwarded headers) or rate limiting is trivially bypassed (if users can rotate IPs).
- Recommendation: Add `X-Forwarded-For` trust configuration and consider adding conversation_id-based rate limiting.

**LOW-003: Agent Error Messages Expose Internal Details**
- File: `gobierno-queretaro/orchestrator/main.py:711-714`
- Issue: The route error handler returns `detail=f"Orchestrator error: {str(e)}"` which exposes internal error messages to the API caller. Similarly, agent query handlers expose `f"Agent error: {str(e)}"`.
- Impact: Internal error details (database connection strings, file paths, stack traces) may be exposed to external callers.
- Recommendation: Return generic error messages to external callers and log detailed errors internally.

**LOW-004: Keyword Classifier Confidence Is Also Hardcoded**
- File: `gobierno-queretaro/orchestrator/classifier.py:603-607`
- Issue: `keyword_classify` returns a fixed `confidence: 0.85` regardless of the match quality. A message matching 5 keywords should have higher confidence than one matching 1 keyword.
- Impact: No way to distinguish strong keyword matches from weak ones in metrics or routing decisions.
- Recommendation: Scale confidence with match strength, e.g., `min(0.7 + 0.05 * match_count, 0.95)`.

**LOW-005: Tool Node Does Not Loop Back to Handler on Multi-Step Tool Use**
- File: `gobierno-queretaro/agents/_template/agent.py:294`, `gobierno-queretaro/agents/vehicles/agent.py:313`
- Issue: After tool execution, the graph edges go `tools -> respond -> END`. This means if the LLM needs to call multiple tools in sequence (call tool A, see result, then call tool B), it cannot. The graph only supports a single round of tool calls.
- Impact: Complex multi-step tool workflows (e.g., look up account, then create ticket with that info) require the LLM to make all tool calls in a single response or cannot be completed.
- Recommendation: Edge `tools` back to the handler node instead of `respond`, so the LLM can see tool results and decide to call more tools or generate a final response.

**LOW-006: Conversation History Truncation Inconsistency**
- File: `gobierno-queretaro/orchestrator/router.py:131` (6 messages), `gobierno-queretaro/orchestrator/main.py:626` (10 messages), `gobierno-queretaro/orchestrator/main.py:673` (20 messages)
- Issue: Different parts of the system truncate conversation history at different limits: 6 messages for classification context, 10 messages for routing context, 20 messages for session storage. There is no documented rationale for these different limits.
- Impact: Classification operates on a narrower window than routing, which could cause inconsistent behavior when conversation context is important for classification.
- Recommendation: Centralize history limits in configuration with documented rationale.

### Positive Observations

1. **Well-designed two-tier architecture.** The separation between orchestrator (Tier 0) and domain agents (Tier 1) is clean. The orchestrator knows nothing about domain logic, and agents know nothing about routing. This enables independent deployment, fault isolation, and team ownership.

2. **Hybrid classification is a smart optimization.** The keyword-first, LLM-fallback approach saves ~70% of LLM classification costs while maintaining accuracy. The dynamic classifier data system (building from registry) is a forward-looking design.

3. **Comprehensive session compartmentalization.** The `SessionContext` with per-agent data vaults, shared data, confidentiality elevation (never lowered), and agent history tracking is well-designed for a multi-agent system handling sensitive government data.

4. **PacoMemory is well-scoped.** The memory system enforces scope isolation (agents cannot access other agents' data), has GDPR-compliant deletion (`forget_citizen_all_scopes`), auto-anonymization for stale profiles, and configurable per-scope settings. The nightly batch summarization via snapshots is a practical design for avoiding real-time summarization costs.

5. **Resilient HTTP client pattern.** The combination of circuit breaker, exponential backoff retries, and automatic fallback routing creates a robust failure handling cascade. The circuit breaker's three-state model (CLOSED/OPEN/HALF_OPEN) is correctly implemented.

6. **Agent self-registration and health sweeps.** The dynamic registry with heartbeat-based health sweeps is the right approach for a microservices architecture, even though actual agents have not yet adopted it.

7. **Security middleware with PII detection.** The SecurityMiddleware intercepts all requests, detects PII, and creates an audit trail. PII is masked in logs but preserved for agent processing, which is the correct approach.

8. **API versioning from day one.** The `/v1/` prefix with backward-compatible unversioned aliases shows forward thinking about API evolution.

9. **Standardized tool return format.** The `formatted_response` pattern in tool returns ensures consistent user-facing messages regardless of LLM generation variability.

10. **Context continuity for multi-turn conversations.** The ambiguous message detection and `last_category` routing prevents unnecessary re-classification of follow-up messages like "yes", "ok", etc.

### Architecture Diagram Notes

1. **PACO_PAPER.md diagram is accurate** for the general architecture but does not show the PacoMemory system, the dynamic agent registry, or the A2A agent card endpoints that have been added.

2. **Missing from documentation:** The voice gateway (`gobierno-queretaro/voice-gateway/`) is mentioned in PACO_PAPER.md but its integration with the orchestrator is not documented in ARCHITECTURE.md.

3. **CEA agent inconsistency:** ARCHITECTURE.md states "CEA is handled by maria-v3 separately and is not part of this multi-agent system" (line 335), but the orchestrator's static registry has a CEA entry pointing to a `water-cea` agent URL, and the classifier has extensive CEA keywords. This discrepancy should be resolved.

4. **Two-system gap:** The `maria-claude/` and `maria-v3/` directories represent a separate system. The integration between PACO (gobierno-queretaro) and the MARIA system is not architecturally documented. It appears MARIA handles the WhatsApp/Chatwoot interface and PACO handles the intelligent routing, but the boundary is unclear.

### Metrics
- Files reviewed: 28
- Critical findings: 4
- High findings: 5
- Medium findings: 6
- Low findings: 6
