# PACO Comprehensive Audit - Consolidated Report

**Date:** 2026-02-07
**Scope:** Full-stack audit of PACO multi-agent system (gobierno-queretaro + paco control plane)
**Auditors:** 7 specialized review agents (infrastructure, database, security, architecture, code quality, conversation design, frontend/performance)
**Files Reviewed:** 213 across both codebases

---

## Production Readiness Score: 3.5 / 10

PACO has a **strong architectural foundation** -- hybrid classification, circuit breakers, session compartmentalization, GDPR-aware memory, and a consistent agent template. However, it has **critical security vulnerabilities**, **broken safety-critical features**, and **insufficient testing** that make it unsuitable for production deployment in its current state handling real citizen data.

---

## Executive Summary

| Domain | Critical | High | Medium | Low | Score |
|--------|----------|------|--------|-----|-------|
| Infrastructure & DevOps | 5 | 8 | 9 | 8 | 2/10 |
| Database & Data | 3 | 4 | 6 | 6 | 4/10 |
| Security & Compliance | 5 | 6 | 8 | 6 | 2/10 |
| Architecture & Resilience | 4 | 5 | 6 | 6 | 5/10 |
| Code Quality & Testing | 3 | 6 | 7 | 4 | 4/10 |
| Conversation Design & UX | 5 | 5 | 6 | 6 | 4/10 |
| Frontend & Performance | 4 | 5 | 6 | 7 | 4/10 |
| **TOTAL** | **29** | **39** | **48** | **43** | **3.5/10** |

**Total findings: 159** (29 Critical, 39 High, 48 Medium, 43 Low)

---

## Top 10 Most Urgent Findings (Must Fix Before Production)

### 1. BROKEN HUMAN HANDOFF IN CRISIS SCENARIOS (SAFETY-CRITICAL)
- **Reports:** Conversation Design CRIT-004
- **File:** `agents/women-iqm/tools.py:207-248`, `agents/psychology-sejuve/tools.py:307-347`
- **Issue:** `handoff_to_human` tells citizens "te estoy conectando con una especialista" but NO actual transfer mechanism exists. No Chatwoot API call, no webhook, no queue entry. The citizen waits for help that never comes.
- **Impact:** A person in a violence or suicide crisis receives a **broken promise of human intervention**. This is the single most dangerous finding in the entire audit.
- **Fix:** Either implement real handoff (Chatwoot conversation assignment + push notification to on-call staff) or change the message to transparently say "por favor llama directamente a [number]" until real handoff exists.

### 2. WILDCARD CORS WITH CREDENTIALS ON ALL 15+ SERVICES
- **Reports:** Security CRIT-001, Architecture LOW-001
- **File:** `orchestrator/main.py:391-397` and all 13 agent `main.py` files
- **Issue:** `allow_origins=["*"]` + `allow_credentials=True` on every FastAPI service. Any website on the internet can make credentialed cross-origin requests.
- **Impact:** CSRF attacks trivial against the orchestrator and all agents. Any website visited by an operator can silently exfiltrate citizen data.
- **Fix:** Replace `["*"]` with explicit allowlist from environment variable. Remove CORS from internal agent services.

### 3. UNAUTHENTICATED AGENT ENDPOINTS EXPOSED ON HOST PORTS
- **Reports:** Security CRIT-002, Infrastructure HIGH-004
- **File:** `docker-compose.yml:76-400` (13 agent port mappings)
- **Issue:** Every agent's `/query` endpoint is exposed on host ports 9101-9113 with zero authentication, bypassing the orchestrator's rate limiting, PII detection, and audit logging.
- **Impact:** Direct access to crisis agents (psychology port 9105, women's services port 9106) without any security controls or audit trail.
- **Fix:** Remove all agent port mappings from docker-compose.yml. Agents should only be reachable via the internal Docker network through the orchestrator.

### 4. DOCKER SOCKET MOUNT GRANTS ROOT HOST ACCESS
- **Reports:** Infrastructure CRIT-001
- **File:** `paco/docker-compose.yml:120`
- **Issue:** `paco-backend` mounts `/var/run/docker.sock:/var/run/docker.sock:ro`. Even read-only, any process inside can issue Docker API commands granting effective root access to the host.
- **Impact:** If paco-backend is compromised (via the guessable JWT secret, for example), the attacker gains full control of the host and every container.
- **Fix:** Remove Docker socket mount entirely. Use a restricted Docker API proxy if container management is needed.

### 5. CRISIS DETECTION MISSES IMPLICIT DISTRESS SIGNALS
- **Reports:** Conversation Design CRIT-001, CRIT-002, CRIT-005
- **Files:** `agents/women-iqm/agent.py:61-62`, `agents/psychology-sejuve/agent.py:83-86`
- **Issue:** Violence detection only checks 7 explicit keywords; suicide detection only checks 9. Real victims use indirect language ("mi esposo llego borracho", "ya no le veo sentido", "soy una carga"). No cross-agent crisis detection exists at the orchestrator level.
- **Impact:** Citizens in genuine danger get routed to generic inquiry handlers instead of crisis protocols. A suicidal person talking to the water agent about their bill won't trigger crisis escalation.
- **Fix:** Add LLM-based urgency pre-check at orchestrator level that runs BEFORE context continuity. Expand keyword lists to 30+ phrases per crisis type.

### 6. HARDCODED/DEFAULT CREDENTIALS EVERYWHERE
- **Reports:** Security CRIT-003, CRIT-004, Infrastructure CRIT-002, CRIT-003, CRIT-004, Database CRIT-003
- **Files:** `docker-compose.yml` (postgres:postgres), `paco/docker-compose.yml` (ClickHouse, all-zeros encryption), `paco/backend/app/core/config.py:28` (JWT secret), `paco/db/init.sql:37-43` (admin123), login page (admin@paco.local)
- **Issue:** Database credentials, JWT signing key, encryption keys, ClickHouse credentials, and admin user password are all hardcoded with trivially guessable defaults.
- **Impact:** Complete authentication bypass, full database access, and null encryption across both systems.
- **Fix:** Remove all default values for secrets. Require environment variables. Fail fast on startup if not configured. Remove credentials from login page UI.

### 7. ENCRYPTION KEY AUTO-GENERATES ON RESTART (DATA LOSS)
- **Reports:** Security CRIT-005, Code Quality CRIT-03
- **File:** `shared/security/manager.py:42-57`
- **Issue:** When `ENCRYPTION_KEY` is not set, a new random Fernet key is generated per startup. Previously encrypted citizen PII becomes permanently undecryptable. The `decrypt_field` method silently returns the encrypted blob unchanged, propagating corruption.
- **Impact:** Every service restart silently destroys all encrypted citizen data. In multi-instance deployment, each instance has a different key.
- **Fix:** Make `ENCRYPTION_KEY` required. Fail fast if not set. Add key versioning for rotation support.

### 8. NO RESOURCE LIMITS ON ANY CONTAINER
- **Reports:** Infrastructure HIGH-001
- **File:** Both `docker-compose.yml` files (27+ services)
- **Issue:** Zero CPU/memory limits on any service. 13 LLM-calling agents can each consume unbounded memory.
- **Impact:** A single memory leak or large LLM response can OOM-kill all containers, taking down the entire system serving citizens.
- **Fix:** Add `deploy.resources.limits` to all services. Start with agents at 512m, orchestrator at 1g, databases at 1g.

### 9. TICKET FOLIO RACE CONDITION
- **Reports:** Database CRIT-001
- **File:** `shared/db/init.sql:176-203`
- **Issue:** Folio generation uses `MAX(folio) + 1` in a trigger. Under concurrent inserts, two transactions can read the same MAX and generate duplicate folios.
- **Impact:** `duplicate key` errors lose citizen service requests with no retry mechanism.
- **Fix:** Replace with a `ticket_sequences` table using `FOR UPDATE` locking or PostgreSQL sequences.

### 10. ~15% TEST COVERAGE FOR A PRODUCTION GOVERNMENT SYSTEM
- **Reports:** Code Quality CRIT-01
- **Files:** `tests/` directory (7 test files total)
- **Issue:** Security module, memory system, session management, admin API, 11 of 13 agents, voice gateway, and training pipeline have ZERO tests. PII detection regex patterns have never been tested against real Mexican document formats.
- **Impact:** No safety net for regressions. The system handling citizen PII, crisis scenarios, and GDPR compliance operates without any verification of its security features.
- **Fix:** Prioritize tests for `shared/security/` (PII detection accuracy), `shared/memory/` (GDPR forget completeness), and the 2 crisis agents.

---

## Cross-Cutting Themes

### Theme 1: Security as Afterthought
The security *framework* is well-designed (PII detection, Fernet encryption, audit logging, RBAC), but the *deployment configuration* undermines every security measure:
- CORS allows all origins
- Agents bypass all security via direct port access
- Credentials are hardcoded
- Encryption keys auto-generate
- JWT secret is guessable
- Redis has no auth
This is a pattern of good security code with bad operational security.

### Theme 2: Template vs Reality Gap
The agent template (`_template/`) includes self-registration, heartbeat, memory integration, A2A protocol, and metrics. But **11 of 13 actual agents don't use the template**. They have hand-written `main.py` files missing registration, heartbeat, memory, and tracing. The dynamic registry system exists but agents never register, so the orchestrator always falls back to static config.

### Theme 3: Crisis Protocol Incomplete
The crisis-handling architecture follows the right *pattern* (detect first, escalate, provide resources) but has critical gaps:
- Keyword detection is too narrow (7-9 keywords vs 30+ needed)
- No orchestrator-level crisis intercept across all agents
- Human handoff is a stub that promises help that never comes
- Phone numbers conflict between prompts and tools
- Temperature is too high (0.7) for crisis responses

### Theme 4: Two-System Integration Gap
`gobierno-queretaro` (runtime) and `paco` (control plane) are effectively separate systems:
- Two different Postgres instances with no shared data strategy
- Agent identity duplicated with different schemas
- No cross-system correlation for observability
- The boundary between PACO and the MARIA WhatsApp system is undocumented

### Theme 5: Observability Fragile
- Tracing store is in-memory only (lost on restart)
- Audit logs are Redis-only with 100K cap and no persistence config
- Circuit breaker state is in-memory only
- The RL training pipeline has placeholder rollout functions
- Langfuse encryption key defaults to all-zeros

---

## Prioritized Remediation Roadmap

### Phase 0: Safety-Critical (This Week)
| # | Action | Effort | Reports |
|---|--------|--------|---------|
| 1 | Fix `handoff_to_human` - either implement real handoff or change messaging to be transparent | 2-3 days | Conv CRIT-004 |
| 2 | Remove agent port mappings from docker-compose.yml | 30 min | Sec CRIT-002, Infra HIGH-004 |
| 3 | Fix CORS to explicit allowlist | 1 hour | Sec CRIT-001 |
| 4 | Require `ENCRYPTION_KEY` env var (fail fast) | 1 hour | Sec CRIT-005 |
| 5 | Require `SECRET_KEY` env var (fail fast, no default) | 30 min | Sec CRIT-004, CQ CRIT-02 |
| 6 | Remove Docker socket mount | 30 min | Infra CRIT-001 |
| 7 | Expand crisis keywords to 30+ per type | 1 day | Conv CRIT-001, CRIT-002 |
| 8 | Add orchestrator-level urgency pre-check | 1-2 days | Conv CRIT-005 |
| 9 | Fix conflicting IQM phone numbers | 1 hour | Conv CRIT-003 |
| 10 | Remove default admin credentials from login page UI | 30 min | FE CRIT-002 |

### Phase 1: Security Hardening (Week 2-3)
| # | Action | Effort | Reports |
|---|--------|--------|---------|
| 11 | Externalize all credentials to env vars / secrets | 2-3 days | Infra CRIT-002-005, Sec CRIT-003, DB HIGH-003 |
| 12 | Add resource limits to all containers | 2 hours | Infra HIGH-001 |
| 13 | Implement network segmentation (3 networks) | 3 hours | Infra HIGH-002 |
| 14 | Add non-root users to all gobierno-queretaro Dockerfiles | 2 hours | Infra HIGH-005 |
| 15 | Add Redis authentication | 1 hour | Sec MED-002 |
| 16 | Fix admin API key timing attack (hmac.compare_digest) | 30 min | Sec HIGH-002 |
| 17 | Restrict Jaeger/infra port exposure | 1 hour | Infra HIGH-003, Sec LOW-004 |
| 18 | Disable open user registration or add approval | 2 hours | Sec HIGH-005 |
| 19 | Add prompt injection resistance to BASE_RULES | 1 hour | Conv HIGH-005 |
| 20 | Reduce JWT expiry to 60 min, add refresh tokens | 1 day | Sec MED-005 |

### Phase 2: Data & Reliability (Week 3-4)
| # | Action | Effort | Reports |
|---|--------|--------|---------|
| 21 | Fix ticket folio race condition (sequences table) | 2 hours | DB CRIT-001 |
| 22 | Fix SQL injection in upsert_citizen_profile (column whitelist) | 1 hour | DB CRIT-002 |
| 23 | Implement connection pooling in AgentRegistry | 3 hours | DB HIGH-001 |
| 24 | Remove NullPool from paco backend | 30 min | DB HIGH-004 |
| 25 | Fix conversation snapshot ON CONFLICT target | 1 hour | Arch HIGH-005, DB LOW-002 |
| 26 | Fix broken KEYWORD_MAP import | 30 min | Arch CRIT-001 |
| 27 | Add asyncio.Lock to singleton patterns | 2 hours | Arch CRIT-003 |
| 28 | Persist circuit breaker state in Redis | 3 hours | Arch CRIT-004 |
| 29 | Reuse httpx.AsyncClient (create once) | 1 hour | Arch HIGH-003 |
| 30 | Switch classifier to async Anthropic client | 2 hours | CQ HIGH-06 |

### Phase 3: Testing & Quality (Month 2)
| # | Action | Effort | Reports |
|---|--------|--------|---------|
| 31 | Add tests for shared/security/ (PII patterns, encryption) | 3 days | CQ CRIT-01 |
| 32 | Add tests for shared/memory/ (GDPR forget, store ops) | 2 days | CQ CRIT-01 |
| 33 | Pin all dependencies with lockfiles | 1 day | CQ HIGH-03 |
| 34 | Replace sys.modules mocking with proper fixtures | 2 days | CQ HIGH-01 |
| 35 | Narrow exception catches to specific types | 3 days | CQ HIGH-02 |
| 36 | Add error.tsx and loading.tsx to frontend routes | 1 day | FE CRIT-001, HIGH-002 |
| 37 | Replace `any` in API client with proper types | 1 day | FE HIGH-001 |
| 38 | Migrate agents to use template pattern | 1 week | Arch MED-001, CQ HIGH-04 |

### Phase 4: Operational Excellence (Month 2-3)
| # | Action | Effort | Reports |
|---|--------|--------|---------|
| 39 | Extract BASE_RULES to shared module | 2 hours | Conv HIGH-001 |
| 40 | Externalize phone numbers/URLs to config | 2 days | Conv HIGH-004 |
| 41 | Add voice-friendly text preprocessing | 2 days | Conv HIGH-003 |
| 42 | Implement database migration tool (Alembic) | 2 days | DB MED-001 |
| 43 | Add data retention/archival for messages/events | 2 days | DB MED-003 |
| 44 | Set up CI/CD pipeline | 3 days | Infra LOW-003 |
| 45 | Persist tracing store (Redis or PostgreSQL) | 2 days | FE CRIT-004 |
| 46 | Implement LangGraph checkpointing | 3 days | Arch HIGH-002 |
| 47 | Add database backup automation | 1 day | DB LOW-006, Infra LOW-002 |
| 48 | Encrypt PII in tickets.contact_info | 1 day | DB MED-004 |

---

## Positive Observations

Despite the critical findings, PACO demonstrates strong engineering in several areas:

1. **Hybrid Classification Architecture** - Keyword-first, LLM-fallback saves ~70% of classification costs while maintaining accuracy. The dynamic classifier built from agent registry is forward-looking.

2. **PacoMemory Scoped Design** - Clean scope isolation between agents, GDPR-compliant deletion, auto-anonymization for stale profiles, and configurable per-scope settings including disabling memory for sensitive categories (IQM).

3. **Circuit Breaker with Fallback Cascade** - The three-state circuit breaker + exponential backoff + automatic fallback routing creates a robust failure handling chain.

4. **Mexican PII Detection** - Comprehensive regex patterns for CURP, RFC, INE, NSS with proper validation functions. Well-suited for the domain.

5. **Security Middleware Pipeline** - Automatic PII scanning, audit logging, and confidentiality tracking on every request, with proper masking in logs.

6. **Crisis-First Agent Design** - Both IQM and PSI check for crisis signals BEFORE any other routing, and include crisis hotline numbers even in error handlers.

7. **Agent Template Pattern** - The `_template/` provides a comprehensive, production-ready foundation including A2A protocol, self-registration, memory, and metrics. When adopted, it ensures consistency.

8. **Session Compartmentalization** - Per-agent data vaults with confidentiality elevation (never lowered) is well-designed for multi-agent government data handling.

9. **Visual Workflow Builder** - Sophisticated drag-and-drop builder with undo/redo, auto-save, validation, and IR-based code generation pipeline with actual test coverage.

10. **RBAC in Control Plane** - Proper role-based access control with admin/operator/viewer roles and clean FastAPI dependency injection.

---

## Individual Audit Reports

| # | Domain | File | Findings |
|---|--------|------|----------|
| 1 | Infrastructure & DevOps | [01-infrastructure.md](./01-infrastructure.md) | 5C, 8H, 9M, 8L |
| 2 | Database & Data | [02-database.md](./02-database.md) | 3C, 4H, 6M, 6L |
| 3 | Security & Compliance | [03-security.md](./03-security.md) | 5C, 6H, 8M, 6L |
| 4 | Architecture & Resilience | [04-architecture.md](./04-architecture.md) | 4C, 5H, 6M, 6L |
| 5 | Code Quality & Testing | [05-code-quality.md](./05-code-quality.md) | 3C, 6H, 7M, 4L |
| 6 | Conversation Design & UX | [06-conversation-design.md](./06-conversation-design.md) | 5C, 5H, 6M, 6L |
| 7 | Frontend & Performance | [07-frontend-performance.md](./07-frontend-performance.md) | 4C, 5H, 6M, 7L |
