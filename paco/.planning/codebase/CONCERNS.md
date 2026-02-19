# Codebase Concerns

**Analysis Date:** 2026-02-03

## Security Considerations

**Hardcoded Defaults in Configuration:**
- Issue: Default credentials and secrets in configuration code
- Files: `backend/app/core/config.py`
- Details: Lines 22, 28, 42 contain default values like `paco_secret@localhost`, `your-secret-key-change-me-in-production`, and `http://localhost:3001`
- Risk: If .env is missing or incomplete, application runs with weak defaults. Production deployments must override via environment variables.
- Current mitigation: Environment variable override is implemented
- Recommendations:
  - Add validation in `config.py` to raise errors if `secret_key` contains default value in non-debug mode
  - Document required environment variables clearly for production deployment
  - Add pre-flight checks that fail the application startup if critical secrets are not properly configured

**NullPool Database Connection:**
- Issue: Using `NullPool` in async database configuration
- Files: `backend/app/db/session.py` (line 21)
- Risk: NullPool disables connection pooling, creating new DB connection per request. This degrades performance under load and exhausts database connection limits
- Current state: No connection pooling, each request creates fresh connection
- Fix approach: Replace `NullPool` with `AsyncPool` or `QueuePool` with appropriate sizing for concurrent requests
- Impact: Performance degradation at scale, potential database connection failures under load

**JWT Token Expiration (7 days):**
- Issue: Access tokens expire after 7 days
- Files: `backend/app/core/config.py` (line 30)
- Risk: Long-lived tokens increase breach impact window. If token is compromised, attacker has 7 days of access
- Current state: `access_token_expire_minutes: int = 60 * 24 * 7`
- Recommendations:
  - Reduce to 1 hour for production
  - Implement refresh token rotation for better security posture
  - Add token revocation mechanism

**Missing Input Validation on CORS Origins:**
- Issue: CORS origins are split from string without validation
- Files: `backend/app/core/config.py` (lines 33-37)
- Risk: Invalid URLs in CORS_ORIGINS could cause unexpected behavior
- Current state: Simple string split without URL validation
- Fix approach: Validate each origin is a valid URL before use

**Password Hash Configuration:**
- Issue: Bcrypt context uses `deprecated="auto"` setting
- Files: `backend/app/core/security.py` (line 17)
- Impact: Older password hashes may not get automatically upgraded on next login
- Recommendations: Consider using `deprecated="argon2"` or implement explicit password migration on login

## Tech Debt

**Global Exception Handler Swallows Details:**
- Issue: Generic exception handler returns minimal error information
- Files: `backend/app/main.py` (lines 140-149)
- Problem: Returns only "Internal server error" string, making debugging difficult in production
- Current state: Exception type exposed in response but not logged
- Fix approach: Add proper logging and structured error tracking before returning generic response

**Print Statements Instead of Logging:**
- Issue: Code uses `print()` for debug output instead of proper logging
- Files: `backend/app/api/agents.py` (line 586)
- Problem: Print statements don't route to logs, can't be filtered by severity, don't work in production
- Impact: Hard to debug issues in production environments
- Fix approach: Implement Python logging throughout, configure for file and console output

**Agent Sync Error Handling is Permissive:**
- Issue: YAML sync endpoint silently continues on file processing errors
- Files: `backend/app/api/agents.py` (lines 584-586)
- Details: When processing agent config files, exceptions are caught and printed but don't halt sync
- Risk: Invalid agent configurations could be partially applied without notice
- Fix approach: Collect errors and return them to client, optionally fail entire sync on critical errors

**No Request Rate Limiting:**
- Issue: API endpoints lack rate limiting
- Files: All API router files in `backend/app/api/`
- Risk: Susceptible to DoS attacks, no protection against abuse
- Impact: API can be exhausted by repeated requests
- Fix approach: Add rate limiting middleware using decorators or async middleware

**Missing Database Transaction Rollback Guards:**
- Issue: Async database operations might not properly rollback on errors
- Files: `backend/app/db/session.py`, all API endpoints
- Details: Session close happens in finally block but implicit commits may occur
- Risk: Partial data writes on exceptions
- Current state: Using `autocommit=False` and `autoflush=False` but no explicit transaction context managers
- Fix approach: Use context managers or decorators to ensure explicit rollback on exception

## Performance Bottlenecks

**N+1 Query Problem in Executions List:**
- Issue: Listing executions queries agents separately from executions
- Files: `backend/app/api/executions.py` (lines 144-149)
- Problem: Gets execution list (1 query) then queries all agent names in loop (N additional queries)
- Impact: Performance degrades with number of executions
- Fix approach: Use SQLAlchemy joins to fetch agent names in single query

**Metrics Aggregation Queries Not Indexed:**
- Issue: Complex aggregate queries on execution and tool_call tables may be slow
- Files: `backend/app/api/executions.py` (lines 241-339)
- Details: Group-by and sum operations without index guidance
- Current bottleneck: Metrics endpoints scan entire execution history
- Fix approach: Add database indexes on `started_at`, `agent_id`, and `status` columns

**No Pagination on Tool Calls in Execution Detail:**
- Issue: Gets all tool calls for execution without limit
- Files: `backend/app/api/executions.py` (lines 195-200)
- Problem: Large execution jobs could return thousands of tool call records
- Risk: Memory explosion, slow response times for executions with many tool calls
- Fix approach: Implement pagination or limit on tool calls returned

**PM2 Client Makes Blocking Subprocess Calls:**
- Issue: PM2 client spawns processes without timeout management
- Files: `backend/app/services/pm2_client.py` (lines 20-24, 108-116)
- Problem: `asyncio.create_subprocess_exec` awaits indefinitely if PM2 hangs
- Risk: Can hang entire API if PM2 becomes unresponsive
- Fix approach: Add timeout parameter to `asyncio.wait_for()` around subprocess calls

## Fragile Areas

**Dependency on External PM2 Installation:**
- Issue: PM2 is called via subprocess, not abstracted
- Files: `backend/app/services/pm2_client.py`
- Why fragile: If PM2 is not installed or in PATH, API errors silently return FileNotFoundError
- Current state: Error caught but not propagated clearly
- Safe modification: Implement healthcheck for PM2 availability on startup, fail fast if missing
- Test coverage: No tests for PM2 unavailable scenario

**YAML Agent Configuration Parsing:**
- Issue: Agent config loading uses unsafe yaml.safe_load without schema validation
- Files: `backend/app/api/agents.py` (lines 528-587)
- Why fragile: Malformed YAML silently skipped, config changes could break agents
- Risk: Partial agent configurations deployed without error notification
- Safe modification:
  - Validate against Pydantic schema after YAML load
  - Fail-fast on schema violations
  - Return validation errors to client
- Test coverage: No validation tests for agent config schema

**Execution Metadata as Untyped Dict:**
- Issue: Execution metadata stored as arbitrary JSONB
- Files: `backend/app/db/models.py` (line 179)
- Why fragile: No schema validation, different executions store different metadata structures
- Risk: Code expecting certain fields may crash
- Fix approach: Define Pydantic models for common metadata structures, validate on insertion

**Frontend NextAuth Integration Incomplete:**
- Issue: Frontend uses NextAuth but backend has JWT auth
- Files: `frontend/app/layout.tsx`, `frontend/package.json` includes `next-auth`
- Problem: Two different auth systems may not be synchronized
- Risk: Session mismatch between frontend and backend
- Current state: NextAuth configured in package.json but unclear if provider is set up
- Fix approach: Document auth flow clearly, ensure frontend receives JWT from backend login endpoint

## Missing Critical Features

**No API Key Management:**
- Issue: Database has ApiKey model but no endpoints to manage them
- Files: `backend/app/db/models.py` (lines 266-291) defines ApiKey table but no API routes
- Problem: Users can't generate API keys for programmatic access
- Blocks: External system integration without basic auth
- Fix approach: Implement POST/DELETE endpoints for API key CRUD

**No Audit Logging:**
- Issue: No record of who changed what and when
- Files: All API endpoints lack audit trail
- Blocks: Compliance requirements, security incident investigation
- Current state: Only execution logs exist, not API action logs
- Fix approach: Add middleware to log all state-changing requests with user and timestamp

**No Rate Limiting on Proxy Endpoints:**
- Issue: Langfuse proxy endpoints lack rate limits
- Files: `backend/app/api/proxy.py`
- Risk: User could hammer Langfuse API through proxy, incurring costs
- Fix approach: Implement per-user rate limiting on proxy endpoints

**Missing Health Check for Dependencies:**
- Issue: Only basic health checks, no persistent monitoring
- Files: `backend/app/main.py` (lines 76-119)
- Problem: One-time health check on startup, no ongoing verification
- Current state: Checks database and Langfuse once at startup
- Fix approach: Implement periodic health check task that updates status in database or Redis

**No Secrets Rotation Mechanism:**
- Issue: No way to rotate API keys without downtime
- Files: `backend/app/core/config.py`
- Problem: Compromised keys require full application restart to change
- Fix approach: Implement hot-reloading of secrets from environment or secret store

## Missing Test Coverage

**No Authentication Tests:**
- Untested areas: JWT validation, token expiration, role-based access control
- Files: `backend/app/core/security.py`, `backend/app/core/deps.py`
- Risk: Auth bypass or permission escalation could exist undetected
- Priority: High - authentication is critical

**No Database Migration Tests:**
- Untested areas: Alembic migrations, schema changes
- Files: `backend/alembic/` directory
- Risk: Broken migrations could fail deployments
- Priority: High - database state is critical

**No PM2 Integration Tests:**
- Untested areas: Process management, agent lifecycle
- Files: `backend/app/services/pm2_client.py`
- Risk: Process management could fail without detection
- Priority: Medium - affects agent availability

**No API Contract Tests:**
- Untested areas: Response schemas match documentation, error codes consistent
- Files: All API endpoint files
- Risk: Frontend integration failures, API version mismatches
- Priority: Medium - affects frontend reliability

**Frontend Missing Component Tests:**
- Untested areas: All React components, API integration
- Files: `frontend/app/**/*.tsx`
- Risk: UI bugs, broken features, poor user experience
- Priority: Medium - affects user experience

## Scaling Limits

**NullPool Connection Model:**
- Current capacity: One connection per request (no pooling)
- Limit: Database max_connections parameter (typically 100)
- Scaling path: Implement proper connection pooling with AsyncPool, tune pool size to concurrent requests
- Estimated impact: At 10 concurrent users with avg 500ms request time, system hits connection limits

**Single PostgreSQL Database:**
- Current capacity: Single database instance for PACO, Langfuse, agents
- Limit: Single 5432 port, no replication, single point of failure
- Scaling path: Implement read replicas, separate databases per service, load balancing
- Impact: Database unavailability = entire system unavailable

**Synchronous PM2 Subprocess Calls:**
- Current capacity: One PM2 operation at a time due to sequential subprocess calls
- Limit: Blocking operations from queuing if PM2 is slow
- Scaling path: Batch PM2 operations, implement command queue with async processing
- Impact: Agent management becomes bottleneck under high concurrency

**No Caching Layer for Metrics:**
- Current capacity: Fresh calculation on every metrics request
- Limit: Aggregate queries scan entire execution history for each request
- Scaling path: Implement Redis caching with TTL, batch metric updates
- Impact: Metrics endpoints become slow with large execution history (>100k records)

## Dependencies at Risk

**Langfuse Integration Hard-Coded:**
- Risk: Tight coupling to Langfuse service
- Files: `backend/app/services/langfuse_client.py`, multiple proxy endpoints
- Impact: Service unavailability blocks metrics, traces, observability
- Current state: Graceful degradation if not configured, but proxy endpoints fail if not available
- Migration path: Implement observability adapter pattern to swap Langfuse for OpenTelemetry or other providers

**YAML Configuration Format:**
- Risk: No schema versioning for agent config YAML
- Files: `backend/app/api/agents.py`, agent config files in `/agents` directory
- Impact: Changing YAML structure requires code changes, no backward compatibility
- Migration path: Implement config versioning with migration functions for old formats

**PM2 Dependency for Process Management:**
- Risk: Hard-coded PM2 as process manager
- Files: `backend/app/services/pm2_client.py`, subprocess calls
- Impact: Can't use Docker, Kubernetes, or systemd as alternative orchestration
- Migration path: Implement process manager abstraction interface

## Database Schema Concerns

**Metadata Field Not Indexed:**
- Issue: `extra_metadata` JSONB column in Execution model not indexed
- Files: `backend/app/db/models.py` (line 179)
- Problem: Queries filtering on metadata fields will scan entire table
- Fix: Add GIN index on metadata column: `CREATE INDEX idx_execution_metadata ON executions USING GIN (metadata)`

**Missing Foreign Key Cascade Check:**
- Issue: ToolCall has `ondelete="SET NULL"` for tool_id but `ondelete="CASCADE"` for execution_id
- Files: `backend/app/db/models.py` (lines 196-200)
- Problem: Inconsistent cascade behavior could leave orphaned records
- Impact: Cleanup operations may not work as expected
- Fix: Document or standardize cascade strategy across all foreign keys

**User Email Not Indexed for Lookups:**
- Issue: User.email is unique but queries do `select(User).where(User.email == email)`
- Files: `backend/app/db/models.py` (line 42), auth endpoints use this frequently
- Problem: Unique constraint creates index, but unclear if it's being used efficiently
- Fix: Explicitly verify index usage in queries

---

*Concerns audit: 2026-02-03*
