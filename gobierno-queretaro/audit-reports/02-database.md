## Database & Data Audit Report

### Executive Summary

The PACO system operates two separate PostgreSQL instances (gobierno-queretaro and paco control plane) with well-structured schemas and generally safe parameterized queries across the memory subsystem. However, there are critical issues including a ticket folio generation race condition, SQL injection vectors in dynamic query construction for citizen profile updates, per-operation connection creation without pooling in the orchestrator registry, and hardcoded default credentials in production seed data. The memory subsystem is well-designed with scope isolation, audit logging, and GDPR-oriented data lifecycle, but the LangGraph checkpoint tables are abandoned dead schema.

### Critical Findings

**CRIT-001: Ticket Folio Generation Race Condition**
- File: `gobierno-queretaro/shared/db/init.sql:176-203`
- Issue: The `generate_ticket_folio()` trigger function uses `SELECT COALESCE(MAX(CAST(SUBSTRING(folio FROM 12) AS INTEGER)), 0) + 1` to compute the next folio sequence number. This MAX-based approach has a classic TOCTOU (time-of-check-time-of-use) race condition. Under concurrent inserts for the same `category_code` on the same day, two transactions can read the same MAX value and generate duplicate folios, violating the `UNIQUE` constraint on `folio` and causing insert failures.
- Impact: Under production concurrency with 13 agents potentially creating tickets simultaneously, this will produce `duplicate key value violates unique constraint` errors, losing citizen service requests. The `WHEN (NEW.folio IS NULL)` guard means the trigger only fires when folio is unset, so there is no retry mechanism.
- Recommendation: Replace the MAX-based approach with a per-category PostgreSQL `SEQUENCE` object, or use a dedicated `ticket_sequences` table with `FOR UPDATE` locking. Example: `CREATE TABLE ticket_sequences (category_code VARCHAR(10), seq_date DATE, current_val INTEGER, PRIMARY KEY (category_code, seq_date));` and use `UPDATE ... SET current_val = current_val + 1 RETURNING current_val` which is atomic.

**CRIT-002: SQL Injection in Dynamic Citizen Profile Updates**
- File: `gobierno-queretaro/shared/memory/store.py:206-229`
- Issue: The `upsert_citizen_profile()` method constructs SQL dynamically by interpolating dictionary keys directly into the query string: `f"UPDATE citizen_profiles SET {', '.join(set_clauses)} WHERE contact_id = $1"` and `f"INSERT INTO citizen_profiles ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"`. The column names come from `**updates` keyword arguments. While values are parameterized (safe from value injection), the column names are NOT parameterized. If any caller passes user-controlled keys in the `updates` dict, an attacker could inject arbitrary SQL via column names (e.g., `{"id; DROP TABLE citizen_profiles; --": "value"}`).
- Impact: If the `updates` dict keys ever originate from user input (currently passed from `nightly_summarize.py:120-132` and the admin API), this is a direct SQL injection vector that could destroy or exfiltrate data.
- Recommendation: Validate column names against a whitelist of known `citizen_profiles` columns before constructing the query. Example: `VALID_COLUMNS = {"citizen_id_hash", "display_name_encrypted", "preferred_language", ...}; for key in updates: assert key in VALID_COLUMNS`.

**CRIT-003: Hardcoded Default Admin Credentials in Production Schema**
- File: `paco/db/init.sql:37-43`
- Issue: The PACO control plane init script creates a default admin user with a hardcoded bcrypt password hash for the password `admin123`: `INSERT INTO users (email, password_hash, name, role) VALUES ('admin@paco.local', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.//H4Y4KqYl.K.y', 'PACO Admin', 'admin')`. The comment says "CHANGE THIS!" but there is no enforcement mechanism, no startup check, and no migration to rotate it.
- Impact: Any deployment that runs init.sql without immediately changing the admin password has a known-credential backdoor with full admin access to the PACO control plane. This is a government system.
- Recommendation: Remove the hardcoded user from init.sql entirely. Create the admin user via a separate secured bootstrap script that prompts for or generates a random password. Add a startup health check that warns if the default password hash is still in the database.

### High Priority Findings

**HIGH-001: No Connection Pooling in Orchestrator Registry**
- File: `gobierno-queretaro/orchestrator/config.py:190-227, 318-368, 370-386, 398-425`
- Issue: The `AgentRegistry` class creates a new `asyncpg.connect()` connection for every database operation (`_load_from_db`, `register_agent`, `heartbeat`, `health_sweep`). Each call opens a TCP connection, performs TLS handshake (if configured), authenticates, executes one query, and closes. This happens on every cache refresh (every 30 seconds via `registry_cache_ttl`), every heartbeat from every agent, and every health sweep.
- Impact: With 13 agents sending heartbeats and the registry refreshing frequently, this creates hundreds of short-lived connections per minute, consuming PostgreSQL `max_connections` slots and adding ~10-50ms of connection overhead per operation. Under load, this can exhaust PostgreSQL's connection limit and cause cascading failures.
- Recommendation: Use `asyncpg.create_pool()` with a shared pool (min_size=2, max_size=10) initialized once at startup and reused across all AgentRegistry operations. The memory subsystem (`PacoMemory.connect()` at `gobierno-queretaro/shared/memory/engine.py:57-61`) already correctly uses `asyncpg.create_pool()` -- follow that pattern.

**HIGH-002: Two Separate PostgreSQL Instances Without Shared Data Strategy**
- Files: `gobierno-queretaro/docker-compose.yml:490-510` and `paco/docker-compose.yml:28-47`
- Issue: The system runs two completely separate PostgreSQL instances:
  1. `gobierno-postgres` (postgres:15-alpine, user: `postgres/postgres`, db: `gobierno`) -- agent registry, conversations, tickets, memories
  2. `paco-postgres` (postgres:16-alpine, user: `paco/paco_secret`, db: `paco`) -- control plane, executions, tools, flows, infrastructure definitions
  Both contain an `agents` table but with different schemas (gobierno uses `VARCHAR(50)` primary key, paco uses `UUID`). There is no cross-database reference, no shared identity, and no data synchronization.
- Impact: Agent identity is duplicated and can drift between systems. Execution logs in PACO cannot be correlated with conversations in gobierno. Token/cost tracking in `paco.executions` has no link to `gobierno.tickets` or `gobierno.messages`. Operational dashboards must query two databases independently.
- Recommendation: This appears to be an intentional separation (control plane vs. runtime), but document the boundary clearly. Add a shared `agent_id` mapping or use the PACO control plane as the single source of truth for agent metadata, with gobierno referencing it via API rather than maintaining a parallel registry.

**HIGH-003: Default Database Credentials in Docker Compose**
- File: `gobierno-queretaro/docker-compose.yml:494-497`
- Issue: The gobierno PostgreSQL instance uses `POSTGRES_USER=postgres` and `POSTGRES_PASSWORD=postgres` hardcoded directly in the docker-compose file, not sourced from environment variables or secrets. The connection strings throughout all 13 agent containers and the orchestrator use `postgres://postgres:postgres@postgres:5432/gobierno`.
- Impact: Any network access to the PostgreSQL port (not exposed to host, but accessible within the Docker network and from any compromised container) provides full database access with superuser credentials. In a government system handling citizen PII, this violates basic security hygiene.
- Recommendation: Use Docker secrets or environment variable references (`${POSTGRES_PASSWORD}`) for credentials. Restrict the application user to minimum required permissions (SELECT, INSERT, UPDATE on specific tables) and separate from the superuser account.

**HIGH-004: NullPool in PACO Backend Disables Connection Reuse**
- File: `paco/backend/app/db/session.py:18-23`
- Issue: The SQLAlchemy async engine is configured with `poolclass=NullPool`, which disables connection pooling entirely. The comment says "Use NullPool for async" but this is incorrect -- SQLAlchemy's `create_async_engine` supports `AsyncAdaptedQueuePool` by default and works well with asyncpg.
- Impact: Every database operation opens a new connection and closes it afterward, similar to HIGH-001. For a backend serving a dashboard UI with multiple concurrent users, this adds latency and wastes PostgreSQL connection slots.
- Recommendation: Remove the `poolclass=NullPool` parameter to use SQLAlchemy's default connection pool, or configure `pool_size=5, max_overflow=10` explicitly.

### Medium Priority Findings

**MED-001: No Migration Tool for gobierno-queretaro Schema**
- Files: `gobierno-queretaro/shared/db/init.sql`, `gobierno-queretaro/shared/db/migrations/002_memory_tables.sql`, `gobierno-queretaro/shared/db/migrations/003_classifier_metadata.sql`
- Issue: Schema changes are managed via raw SQL files loaded through Docker entrypoint (`/docker-entrypoint-initdb.d/`). These scripts only run on first database creation (empty `PGDATA`). Migration 003 (classifier metadata) is NOT mounted in docker-compose.yml. There is no versioning, no rollback capability, no idempotency tracking, and no way to apply migrations to an existing database.
- Impact: Any schema change after initial deployment requires manual SQL execution. The memory tables migration (002) is mounted, but 003 is not -- it was likely applied manually. Adding new tables, columns, or indexes requires downtime or risky manual intervention. This is especially problematic for a production government system with 13+ services.
- Recommendation: Adopt Alembic (already a dependency in PACO backend) for gobierno-queretaro as well. Create a proper migration chain with version tracking. At minimum, create a `schema_version` table and a migration runner script.

**MED-002: LangGraph Checkpoint Tables Are Abandoned Dead Schema**
- File: `gobierno-queretaro/shared/db/init.sql:236-270`
- Issue: Three tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`) are created for LangGraph PostgresSaver crash recovery. However, grepping the entire gobierno-queretaro codebase shows these tables are never referenced from application code. The only references are in `init.sql` itself, `PACO_PAPER.md` (documentation), and `docker-compose.yml` (file mount). The orchestrator uses Redis-based session storage (`shared/context/session.py`) instead of LangGraph checkpointing.
- Impact: Dead schema wastes storage if data were ever inserted, creates confusion about the system's crash recovery strategy, and adds unnecessary tables to the database. The indexes on these tables consume catalog space.
- Recommendation: Either remove these tables in a migration (they are unused) or implement LangGraph checkpointing as originally intended. Document the decision either way.

**MED-003: No Data Retention/Archival for Core Tables**
- Files: `gobierno-queretaro/shared/db/init.sql` (messages, events, tasks tables)
- Issue: The `messages`, `events`, and `tasks` tables have no TTL, no partitioning, and no archival strategy. Messages accumulate indefinitely for every conversation. Events (audit/pub-sub) accumulate with a `processed` boolean but are never cleaned up. The memory subsystem has proper retention config (`retention.memory_days=180`, `retention.summary_days=90`), but core operational tables do not.
- Impact: Over months/years of production use with 13 agents and thousands of citizen interactions, these tables will grow unbounded. The `messages` table is especially problematic as it stores full conversation content. Query performance will degrade as the table grows, and storage costs will increase linearly.
- Recommendation: Add a `pg_partman` time-based partitioning strategy for `messages` and `events` (partition by `created_at` monthly). Add a nightly cleanup job for `events WHERE processed = true AND created_at < NOW() - INTERVAL '30 days'`. Archive old conversations to cold storage.

**MED-004: PII Stored in Plaintext JSONB Fields**
- File: `gobierno-queretaro/shared/db/init.sql:162` (`contact_info JSONB` on tickets table)
- Issue: The `tickets.contact_info` JSONB column stores citizen PII (name, phone, email, location) as documented in the `CreateTicketRequest` model (`gobierno-queretaro/shared/db/models.py:201-206`). This data is stored in plaintext with no encryption at rest at the application level. The `citizen_profiles` table correctly uses `display_name_encrypted` (Fernet) and `citizen_id_hash` (SHA-256), but the tickets table does not follow this pattern.
- Impact: A database breach or backup leak would expose citizen contact information in plaintext. For a government system handling sensitive categories (women's services/IQM at SECRET level, psychology/SEJUVE at CONFIDENTIAL level), this is a compliance concern.
- Recommendation: Apply the same Fernet encryption pattern from `citizen_profiles.display_name_encrypted` to `tickets.contact_info`. Alternatively, store contact info in the memory subsystem (which has encryption support) and reference it by ID from tickets.

**MED-005: Missing Foreign Key on events.conversation_id**
- File: `gobierno-queretaro/shared/db/init.sql:138`
- Issue: The `events.conversation_id` column references `conversations(id)` but without `ON DELETE CASCADE` or any other cascade behavior specified. If a conversation is deleted, orphaned events will remain. The `messages` and `tasks` tables correctly use `ON DELETE CASCADE`, but events do not follow the same pattern.
- Impact: Orphaned events accumulate over time when conversations are cleaned up. More importantly, if conversation deletion is used as part of a GDPR "right to be forgotten" flow, related events (which may contain PII in the `payload` JSONB) would survive deletion.
- Recommendation: Add `ON DELETE CASCADE` to `events.conversation_id` to match the pattern used by `messages` and `tasks`. If event preservation is intentional for audit, add `ON DELETE SET NULL` instead and ensure the payload does not contain PII.

**MED-006: builder_sessions Table Missing from init.sql**
- File: `paco/backend/app/db/models.py:770-803`
- Issue: The SQLAlchemy model `BuilderSession` defines a `builder_sessions` table, but this table is not created in `paco/db/init.sql`. The table will fail to be created unless SQLAlchemy's `create_all()` is called (which is not visible in the codebase) or a manual migration is run.
- Impact: The agent builder feature will fail with a `relation "builder_sessions" does not exist` error on first use unless the table was created through an untracked mechanism.
- Recommendation: Add the `CREATE TABLE builder_sessions` DDL to `paco/db/init.sql` or create a proper Alembic migration for it.

### Low Priority / Improvements

**LOW-001: Migration 003 Not Mounted in Docker Compose**
- File: `gobierno-queretaro/docker-compose.yml:502-503`
- Issue: Only `init.sql` (as 001) and `002_memory_tables.sql` are mounted in the postgres container's entrypoint. The `003_classifier_metadata.sql` migration is not mounted, meaning it must be applied manually. Since the same data is now included in `init.sql`'s seed INSERT (which uses `ON CONFLICT DO UPDATE`), migration 003 is effectively redundant but its omission is confusing.
- Impact: Minor -- data is covered by the seed INSERT. But the migration file's existence without being applied creates confusion.
- Recommendation: Either mount 003 in docker-compose.yml for completeness, or remove the file with a note that its content was folded into init.sql.

**LOW-002: conversation_snapshots ON CONFLICT Target Is Incorrect**
- File: `gobierno-queretaro/shared/memory/store.py:277-287`
- Issue: The `save_snapshot()` method uses `ON CONFLICT (id) DO NOTHING`, but `id` is auto-generated via `uuid_generate_v4()`. A conflict on a random UUID will essentially never happen. The intent appears to be deduplication by `conversation_external_id`, but there is no unique constraint on that column. This means every call creates a new snapshot row even for the same conversation.
- Impact: Duplicate snapshots accumulate for the same conversation, leading to duplicate summarization work in the nightly batch. Each snapshot also stores full `message_history` JSONB, so duplicates waste significant storage.
- Recommendation: Add a unique constraint on `(conversation_external_id, contact_id)` and change the conflict target to match, or use UPSERT logic to update the existing snapshot's `message_history`.

**LOW-003: No Index on tickets.conversation_id**
- File: `gobierno-queretaro/shared/db/init.sql:151-171`
- Issue: The `tickets` table has a foreign key `conversation_id UUID REFERENCES conversations(id)` but no index on this column. Indexes exist for `folio`, `category_code`, and `status`, but not for `conversation_id`.
- Impact: Queries that join tickets to conversations or look up tickets by conversation will perform sequential scans. As the tickets table grows, this becomes increasingly expensive.
- Recommendation: Add `CREATE INDEX IF NOT EXISTS idx_tickets_conversation_id ON tickets(conversation_id);`

**LOW-004: No Index Maintenance or VACUUM Strategy**
- Files: All database schemas
- Issue: No `pg_cron` configuration, no scheduled ANALYZE/VACUUM, and no index monitoring. The schemas create many indexes but have no maintenance plan.
- Impact: Over time, table and index bloat will degrade query performance. PostgreSQL's autovacuum handles basic cleanup, but heavily updated tables (like `agents.last_heartbeat` updated every heartbeat) may need more aggressive vacuuming.
- Recommendation: Add `pg_cron` or crontab-based VACUUM ANALYZE for heavily updated tables. Monitor index usage with `pg_stat_user_indexes` to identify unused indexes.

**LOW-005: PACO Backend env_vars and auth_config Store Secrets in Plaintext JSONB**
- File: `paco/backend/app/db/models.py:184` (`env_vars JSONB`), `paco/db/init.sql:58` (`auth_config JSONB`)
- Issue: Agent `env_vars` and MCP server `auth_config` JSONB columns can store API keys and credentials in plaintext. These are visible to anyone with database read access and appear in database backups.
- Impact: Credential leakage through database access or backup exposure.
- Recommendation: Encrypt sensitive JSONB values at the application layer or use PostgreSQL's `pgcrypto` extension (already enabled in paco init.sql) to encrypt these columns.

**LOW-006: No Database Backup Configuration**
- Files: `gobierno-queretaro/docker-compose.yml`, `paco/docker-compose.yml`
- Issue: Neither docker-compose file configures automated database backups. Data volumes (`postgres_data`) are Docker volumes with no backup schedule, no WAL archiving, and no point-in-time recovery capability.
- Impact: A disk failure, accidental deletion, or data corruption event would result in complete data loss for either or both databases.
- Recommendation: Add a backup container or cron job that runs `pg_dump` to an external volume or object storage. Enable WAL archiving for point-in-time recovery. Test restore procedures regularly.

### Positive Observations

1. **Scope isolation in memory subsystem**: The `MemoryStore` consistently filters all queries by `scope_id`, preventing cross-agent data leakage. Every SQL query in `store.py` includes `WHERE scope_id = $1` as the first parameter. This is a well-executed security boundary.

2. **Parameterized queries throughout**: With the exception of CRIT-002, all SQL queries use asyncpg's `$1, $2, ...` parameterized placeholders. The memory CRUD operations in `store.py` are consistently safe against SQL injection through values.

3. **GDPR-aware data lifecycle**: The memory subsystem includes comprehensive privacy features:
   - `forget_citizen_all()` for right-to-erasure across all scopes
   - `anonymize_stale()` with configurable days threshold (default 730 days)
   - `memory_audit_log` table tracking all memory operations
   - Per-scope memory disable (IQM/women's services disabled by default)
   - `pii_in_summaries` flag controlling PII in batch summarization
   - `display_name_encrypted` using Fernet encryption

4. **Well-structured schema design**: Tables use proper foreign keys, UUID primary keys, JSONB for flexible metadata, and `TIMESTAMPTZ` consistently. The agent registry includes confidentiality levels and SLA tiers. The `updated_at` triggers are consistently applied.

5. **Redis caching layer**: The memory subsystem uses Redis with proper TTL (300 seconds), cache invalidation on writes, and graceful degradation when Redis is unavailable (cache misses fall through to PostgreSQL).

6. **Dynamic agent registry with fallback**: The `AgentRegistry` class gracefully falls back to static configuration when the database is unavailable, with cache-based reads and background refresh. This prevents database outages from taking down the entire system.

7. **Nightly batch processing**: The `nightly_summarize.py` script properly handles cleanup of expired records, profile anonymization, and conversation summarization in a single idempotent batch job.

### Metrics

- Files reviewed: 22
- Critical findings: 3
- High findings: 4
- Medium findings: 6
- Low findings: 6
