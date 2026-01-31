# Codebase Concerns

**Analysis Date:** 2026-01-31

## Tech Debt

**In-Memory Conversation Store (Production Risk):**
- Issue: Conversation history stored in JavaScript Map, lost on process restart
- Files: `src/agent.ts` (lines 50-75), `maria-claude/src/agent.ts` (lines 26-51)
- Impact: Multi-turn conversations reset when server restarts; no persistence across deployments
- Fix approach: Implement Redis-based session storage or persist to PostgreSQL; current comment acknowledges this gap: "Production: use Redis"

**Type Safety Gaps with @ts-ignore:**
- Issue: Five instances of @ts-ignore bypass TypeScript strict mode
- Files: `src/test-api.ts` (lines 99, 105, 288, 292), `src/tools.ts` (line 109)
- Impact: Potential runtime type mismatches with undici fetch library; reduces code reliability
- Fix approach: Properly type undici Response objects or create type wrapper interface

**Oversized Tool Files (Code Complexity):**
- Issue: Core tool files exceed 1200 LOC; tools.ts in maria-claude is 1296 lines
- Files: `maria-claude/src/tools.ts` (1296 lines), `src/tools.ts` (1031 lines)
- Impact: Difficult to maintain, test, and modify; high cognitive load for developers
- Fix approach: Split into `soap-tools.ts`, `database-tools.ts`, `ticket-tools.ts` modules

**XML Parsing with Regex (Fragile):**
- Issue: CEA SOAP responses parsed with simple regex patterns instead of XML parser
- Files: `src/tools.ts` (lines 145-161), `maria-claude/src/tools.ts` (similar patterns)
- Impact: Fails on whitespace changes, nested tags, or CDATA sections; unmaintainable parsing
- Fix approach: Use xml2js or fast-xml-parser library; add schema validation

**Manual Database Connection Management:**
- Issue: pgPool created at module load, no connection health checks or pooling configuration validation
- Files: `src/tools.ts` (lines 33-43), `maria-claude/src/tools.ts` (lines 36-45)
- Impact: Connection exhaustion possible under load; no graceful degradation if database unavailable
- Fix approach: Add connection pool monitoring, implement circuit breaker pattern for DB failures

## Known Bugs

**Fallback Folio Generation Collision Risk:**
- Symptoms: Two tickets created rapidly may get same folio (timestamp-based fallback)
- Files: `src/tools.ts` (lines 169-182, 186-223)
- Trigger: PostgreSQL query fails while tickets are being created; fallback uses last 4 digits of Date.now()
- Workaround: Manual folio deduplication in database during recovery; current code comments this gap

**Empty Message Array Parsing Inconsistency:**
- Symptoms: Message array input handling differs between server endpoints; some extract first element, others may fail
- Files: `src/server.ts` (lines 109-121)
- Trigger: Webhook sends message as array instead of string
- Workaround: Current code handles this but parsing is inconsistent across different integrations (n8n vs Chatwoot)

**Database Fallback Returns Success=true on Failure:**
- Symptoms: Ticket creation reports success when database fails; client may not know about sync issues
- Files: `src/tools.ts` (lines 584-596) - createTicketDirect returns success=true with warning when DB fails
- Trigger: PostgreSQL connection loss during ticket creation
- Workaround: Client can detect via 'warning' field, but semantically incorrect (success should mean fully created)

## Security Considerations

**CORS Allows All Origins:**
- Risk: API accessible from any domain; enables cross-origin attacks if tokens/auth added later
- Files: `src/server.ts` (lines 55-65) - `Access-Control-Allow-Origin: "*"`
- Current mitigation: API currently stateless, no authentication tokens in use
- Recommendations: Restrict CORS to known Chatwoot/n8n domains; move to environment variable

**Hardcoded SOAP Credentials:**
- Risk: CEA API credentials embedded in SOAP templates, visible in source code
- Files: `src/tools.ts` (lines 234-235), `maria-claude/src/tools.ts` (lines 120-122)
  - Username: WSGESTIONDEUDA
  - Password: WSGESTIONDEUDA (hardcoded in every request)
- Current mitigation: These are shared service credentials (not user-specific), but still exposed
- Recommendations: Move to environment variables or secrets manager; audit API for credential rotation capability

**Database Credentials in Environment:**
- Risk: PostgreSQL password in .env file; if .env committed, exposed in git history
- Files: `.env.example` (line 25) - PGPASSWORD in plaintext
- Current mitigation: Good - .env is in .gitignore (should be verified)
- Recommendations: Use environment-only secrets in production; consider 1Password/Vault integration for local dev

**Missing Input Validation on API Endpoints:**
- Risk: Limited validation on chat message content; potential for injection attacks in SOAP/SQL contexts
- Files: `src/server.ts` (lines 124-140) - only validates message type and length
- Current mitigation: Message is treated as text (not executed), but no sanitization before SOAP embedding
- Recommendations: Add zod schema validation; sanitize XML special characters before SOAP generation

**Webhook Payload Logging:**
- Risk: Full webhook payload logged including customer data (names, phone numbers)
- Files: `maria-claude/src/chatwoot.ts` (line 79) - `console.log(JSON.stringify(payload, null, 2))`
- Current mitigation: Logs are not persisted to database (memory only)
- Recommendations: Log only message ID and event type; sanitize PII before logging; use structured logging with data retention policy

## Performance Bottlenecks

**Synchronous Conversation Cleanup Loop:**
- Problem: Every 5 minutes, iterates all conversations to find and delete expired ones; blocks event loop
- Files: `src/agent.ts` (lines 52-60) - `setInterval` with synchronous Map iteration
- Cause: No indexed lookup; O(n) operation grows with conversation count
- Improvement path: Implement lazy deletion (on access) or use LRU cache library; offload to background worker

**Repeated PostgreSQL Lookups for Contact Names:**
- Problem: For each ticket creation, queries contacts table by ID then by contract number separately
- Files: `src/tools.ts` (lines 507-539) - two separate pgQuery calls in serial
- Cause: No caching of contact lookups across requests; N+1 query pattern
- Improvement path: Batch lookups into single query; cache contact info in conversation store for duration

**XML Parsing on Every SOAP Response:**
- Problem: Uses regex for each tag extraction (multiple regex.exec calls per response)
- Files: `src/tools.ts` (lines 700-750 for consumo parsing)
- Cause: No compiled regex cache; O(n*m) complexity for n tags across m responses
- Improvement path: Use xml2js parser once; memoize regex patterns

**No Response Caching for CEA API:**
- Problem: Identical contract queries hit CEA API every time; no client-side caching
- Files: `src/tools.ts` (getDeudaTool, getConsumoTool, getContratoTool)
- Cause: Each agent call invokes fresh API request even within same conversation
- Improvement path: Add 5-minute cache keyed by contract number; invalidate on ticket creation

**Conversation Store Memory Leak Risk:**
- Problem: While cleanup runs every 5 minutes, conversations created during bursts can grow unbounded
- Files: `src/agent.ts` (lines 50-75)
- Cause: 1-hour expiry is long; burst of 100 concurrent users = 100 Map entries for 60 minutes
- Improvement path: Implement max conversation cap; reject new conversations if store exceeds threshold

## Fragile Areas

**SOAP Integration with External CEA API:**
- Files: `src/tools.ts` (lines 91-143, 229-320), `maria-claude/src/tools.ts` (similar)
- Why fragile:
  - Depends on third-party SOAP API with no versioning guarantees
  - Response format changes would break regex parsing with no error signal
  - Hardcoded explotacion values (12, 1) may not be correct for all contract types
  - No schema validation of XML responses
- Safe modification:
  - Add XML validation schema before parsing
  - Test with actual CEA API responses to verify parsing handles all cases
  - Log full XML responses on parse failure for debugging
- Test coverage: No unit tests found for XML parsing; only integration tests via test-api.ts

**Database Ticket Creation Logic:**
- Files: `src/tools.ts` (lines 483-597)
- Why fragile:
  - Multiple PostgreSQL queries in sequence without transaction wrapping
  - If contact lookup succeeds but ticket insert fails, no rollback
  - Assumes specific column names and data types (account_id=2, channel='whatsapp')
  - No validation that contact_id/conversation_id exist before insertion
- Safe modification:
  - Wrap in PostgreSQL transaction (BEGIN...COMMIT)
  - Validate foreign key relationships before insert
  - Add constraint checks for enum values
- Test coverage: createTicketDirect tested only via full workflow; edge cases untested

**Agent Classification Accuracy:**
- Files: `src/agent.ts` (lines 116-145), `maria-claude/src/agent.ts` (lines 58-103)
- Why fragile:
  - Regex-based keyword classification in maria-interno/src/agent.ts is brittle
  - Temperature=0.3 may be too low for nuanced Spanish inputs
  - No fallback to human review if confidence is low
  - extractedContract detection assumes 6+ digit numbers but contracts may vary
- Safe modification:
  - Test with real user inputs from different regions/dialects
  - Add low-confidence threshold and queue for manual review
  - Use regex for keywords, GPT for edge cases
- Test coverage: Only manual integration tests; no unit tests for classification logic

**Chatwoot Webhook Processing:**
- Files: `maria-claude/src/chatwoot.ts`, `maria-claude/src/server.ts` (lines 170-262)
- Why fragile:
  - Webhook payload structure assumed but not validated against schema
  - Async processing after returning 200 means errors not reported back
  - Message deduplication using Set limited to 60 seconds; could miss duplicates
  - No retry logic if sendToChatwoot fails after processing
- Safe modification:
  - Add zod schema validation for ChatwootWebhookPayload structure
  - Implement persistent message ID log (Redis/DB) for deduplication
  - Retry failed Chatwoot sends with exponential backoff
- Test coverage: No unit tests for webhook validation; only integration tests

## Scaling Limits

**In-Memory Conversation Store:**
- Current capacity: Tested with <100 conversations
- Limit: Each conversation stores full message history as array; 1000 conversations with 50 messages each = ~1MB heap
- At 10,000 concurrent conversations, heap usage becomes significant; memory thrashing possible
- Scaling path: Migrate to Redis for out-of-process storage; implement connection pooling

**PostgreSQL Connection Pool:**
- Current capacity: max=10 connections (hardcoded in `PG_CONFIG`)
- Limit: With 5-second query latency, max 50 concurrent requests; bottleneck at 100+ concurrent users
- Scaling path: Increase pool size based on load testing; monitor pool exhaustion; implement request queuing

**SOAP API Request Serialization:**
- Current capacity: One request at a time per contract lookup; no connection reuse
- Limit: CEA API likely has rate limits (not documented); retry logic has exponential backoff but caps at maxRetries=3
- Scaling path: Implement dedicated pool of HTTP connections; add queue for batched requests; document CEA API rate limits

**No Queue System for Ticket Creation:**
- Current capacity: Synchronous ticket creation per message; if PG slow, blocks agent response
- Limit: One ticket per conversation per agent call; burst of 100 messages = 100 sequential DB inserts
- Scaling path: Implement job queue (Bull/RabbitMQ); defer ticket creation to background worker; return folio immediately

## Dependencies at Risk

**@openai/agents SDK (src/ agent):**
- Risk: Experimental SDK (version 0.0.14); small community; may have breaking changes
- Impact: Entire agent workflow depends on this; breaking changes require refactor
- Migration plan: src/ implementation already has alternative (maria-claude uses @anthropic-ai/claude-agent-sdk); consider standardizing on Anthropic SDK long-term

**CEA SOAP API (External Dependency):**
- Risk: Legacy SOAP API may be deprecated; no published SLA; unresponsive to issues
- Impact: Core functionality (balance, consumption, contract info) depends entirely on this API
- Migration plan: Maintain fallback mode that gracefully degrades; cache responses; implement offline mode; contact CEA about API modernization roadmap

**PostgreSQL/AGORA Database:**
- Risk: Database schema changes by AGORA team could break ticket creation queries
- Impact: Tickets cannot be created if schema changes; system degrades to local folios
- Migration plan: Version database schema; add migration scripts; document expected table/column structure; add schema validation on startup

**Undici HTTP Client (Proxy Support):**
- Risk: Undici is fetch polyfill; less mature than axios/node-fetch in some edge cases
- Impact: Proxy-based CEA API access fails if undici has bugs; affects deployments behind corporate proxy
- Migration plan: Document known undici issues; consider axios as fallback; add feature flag to switch HTTP clients

**Express.js (Both servers):**
- Risk: Not security-focused; requires manual middleware for validation; older versions have known vulnerabilities
- Impact: Server endpoints vulnerable to injection if input not properly sanitized
- Migration plan: Upgrade Express regularly; use helmet middleware for security headers; validate all inputs with zod

## Missing Critical Features

**Error Recovery and Resilience:**
- Problem: No circuit breaker for failing external APIs; system degrades to partial failures
- Blocks: Long-running scenarios where CEA API is temporarily down; users get confusing error messages
- Impact: Availability < 99%; customers frustrated during maintenance windows
- Fix: Implement circuit breaker pattern (Opossum/Polly); graceful degradation with cached data

**Request Tracing and Observability:**
- Problem: Request IDs not propagated through async calls; logs hard to correlate
- Blocks: Debugging production issues; tracing multi-step workflows
- Impact: Mean time to resolution increases; bugs take longer to fix
- Fix: Add OpenTelemetry instrumentation; correlation IDs in logs; structured logging with JSON

**Testing Framework:**
- Problem: No test files found (jest.config.js, vitest.config.js, *.test.ts)
- Blocks: Regression detection; refactoring confidence; CI/CD validation
- Impact: Tech debt accumulates; breaking changes introduced silently
- Fix: Implement Jest/Vitest; add unit tests for tools, SOAP parsing, database logic; aim for >80% coverage

**Input Sanitization:**
- Problem: User messages not sanitized before embedding in SOAP XML or SQL
- Blocks: Potential XML injection or SQL injection attacks through customer input
- Impact: Data breach risk if attacker sends malicious contract number
- Fix: Use parameterized queries (already done for SQL); use XML libraries instead of string concatenation

**Secrets Management:**
- Problem: SOAP credentials and API tokens in source code (.env.example) or configuration
- Blocks: Credential rotation; compliance with security standards
- Impact: If repository leaked, credentials compromised; hard to implement zero-trust
- Fix: Use environment variables only; integrate with 1Password/Vault; implement automatic rotation

**Monitoring and Alerting:**
- Problem: No monitoring for error rates, API latency, or database connection health
- Blocks: Detecting and responding to outages; SLA compliance
- Impact: Silent failures; customers affected before team knows
- Fix: Add Prometheus metrics; Grafana dashboards; PagerDuty alerts for critical paths

## Test Coverage Gaps

**SOAP Parsing Logic:**
- What's not tested: XML parsing for deuda, consumo, contrato responses; edge cases like missing tags, malformed XML
- Files: `src/tools.ts` (lines 145-161, 270-320 for consumo/deuda parsing)
- Risk: Parser silently returns null for malformed responses; customers see "error" with no context
- Priority: High - XML parsing is critical path for all contract lookups

**Database Transaction Logic:**
- What's not tested: Concurrent ticket creation; contact lookup failures; database connection loss
- Files: `src/tools.ts` (lines 483-597 createTicketDirect)
- Risk: Race conditions in folio generation; orphaned tickets without contact linkage
- Priority: High - ticket creation is core feature; must be reliable

**Chatwoot Webhook Integration:**
- What's not tested: Webhook payload validation; attachment processing; error handling on send failures
- Files: `maria-claude/src/chatwoot.ts` (all), `maria-claude/src/server.ts` (lines 170-262)
- Risk: Webhook processing silently fails; messages never reach customer; no error notification
- Priority: Medium - affects customer experience but has fallback to status endpoint

**Classification Logic:**
- What's not tested: Spanish language variants; slang; edge cases where classification confidence is low
- Files: `src/agent.ts` (lines 116-145), `maria-interno/src/agent.ts` (keyword matching)
- Risk: Misclassified messages routed to wrong agent; customer gets irrelevant responses
- Priority: Medium - incorrect routing degrades UX but doesn't cause data loss

**Error Handling in Server Routes:**
- What's not tested: Malformed JSON payloads; messages exceeding 10KB limit; missing required fields
- Files: `src/server.ts` (lines 102-185), `maria-claude/src/server.ts` (lines 67-164)
- Risk: Unhandled exceptions crash server; customers see 500 errors instead of helpful messages
- Priority: Medium - error messages should be user-friendly

---

*Concerns audit: 2026-01-31*
