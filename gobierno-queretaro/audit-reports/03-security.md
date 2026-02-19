## Security & Compliance Audit Report

### Executive Summary

The PACO system has a thoughtful security foundation -- including PII detection/masking, field-level encryption, audit logging, and RBAC in the PACO Hub backend -- but suffers from several **critical configuration and architectural gaps** that would allow unauthenticated access to sensitive citizen data in a production deployment. The most urgent issues are wildcard CORS with credentials, unauthenticated agent endpoints exposed on host ports, hardcoded database credentials, and an insecure JWT secret default. Given that PACO handles domestic violence and mental health crisis data across 13 government departments, these findings require immediate remediation.

---

### Critical Findings

**CRIT-001: CORS `allow_origins=["*"]` with `allow_credentials=True` across all services**
- File: `gobierno-queretaro/orchestrator/main.py:391-397`
- Also: All 13 agent `main.py` files (e.g. `agents/vehicles/main.py:91-97`, `agents/women-iqm/main.py:64`, `agents/psychology-sejuve/main.py:94`, etc.) and `voice-gateway/main.py:263`
- Issue: Every FastAPI service sets `allow_origins=["*"]` combined with `allow_credentials=True`. Per the Fetch specification and browser behavior, this combination is explicitly dangerous: any website on the internet can make credentialed cross-origin requests to these endpoints. FastAPI/Starlette will actually downgrade `*` to the requesting origin when credentials=True, effectively echoing back any Origin header -- making CSRF attacks trivial.
- Impact: Any malicious website visited by an operator can silently issue requests to the orchestrator or individual agents, exfiltrating citizen data or submitting malicious queries on behalf of a government employee.
- Recommendation: Replace `allow_origins=["*"]` with an explicit allowlist loaded from environment variables (the PACO backend already has `cors_origins` in `paco/backend/app/core/config.py:33` as a model). For internal-only agent endpoints, consider removing CORS entirely.

**CRIT-002: No authentication on individual agent `/query` endpoints -- orchestrator bypass**
- File: `gobierno-queretaro/agents/vehicles/main.py:111-160` (representative of all 13 agents)
- Issue: Every specialist agent exposes a `/query` POST endpoint with zero authentication. The agents are designed to be called by the orchestrator over the Docker network, but Docker Compose maps every agent port to the host (`9101:8000` through `9113:8000` in `docker-compose.yml:76,104,130,...`). Anyone with network access to the host can directly query any agent, completely bypassing the orchestrator's rate limiting, PII detection middleware, audit logging, and security middleware.
- Impact: An attacker can directly access sensitive agents (psychology, women's services for domestic violence cases) without any audit trail, rate limits, or PII protections. The psychology agent (`9105`) and women's services agent (`9106`) handle crisis scenarios.
- Recommendation: (1) Remove host port mappings for agents in docker-compose.yml -- agents should only be reachable via the internal Docker network. (2) Add a shared secret or mTLS between orchestrator and agents. (3) At minimum, add an internal API key header check on agent `/query` endpoints.

**CRIT-003: Hardcoded database credentials in Docker Compose**
- File: `gobierno-queretaro/docker-compose.yml:496-497`
- Issue: PostgreSQL is configured with `POSTGRES_USER=postgres` and `POSTGRES_PASSWORD=postgres` hardcoded directly in the docker-compose file. The same credentials are used in all agent and orchestrator `DATABASE_URL` environment variables (e.g., line 31: `postgres://postgres:postgres@postgres:5432/gobierno`).
- Impact: If the compose file is committed to a public repo or shared, the database credentials are exposed. Even in private repos, hardcoded credentials prevent proper secrets rotation and violate the principle of least privilege.
- Recommendation: Move database credentials to `.env` file or a secrets manager. Use `${POSTGRES_PASSWORD}` variable substitution in docker-compose.yml.

**CRIT-004: Insecure JWT secret key default -- trivially guessable**
- File: `paco/backend/app/core/config.py:28`
- Issue: The JWT signing key defaults to the literal string `"your-secret-key-change-me-in-production"`. If the `SECRET_KEY` environment variable is not set (which is the default), all JWTs are signed with this known value, allowing anyone to forge admin tokens.
- Impact: Complete authentication bypass for the PACO Hub backend -- an attacker can craft a JWT with `role: "admin"` and gain full access to all PACO management APIs including agent CRUD, user management, and infrastructure control.
- Recommendation: Remove the default value entirely (make the field required with no default) so the application fails to start without a proper secret. Validate minimum key length (32+ bytes). Add a startup check that rejects known-insecure values.

**CRIT-005: Encryption key auto-generation causes data loss on restart**
- File: `gobierno-queretaro/shared/security/manager.py:42-57`
- Issue: When `ENCRYPTION_KEY` is not set, SecurityManager generates a new random Fernet key on each instantiation. This key is stored only in memory. If the process restarts, a new key is generated and all previously encrypted data becomes permanently undecryptable. The code only logs a warning (`line 53-56`).
- Impact: In production, any service restart will silently make all encrypted citizen PII (CURP, RFC, etc.) permanently inaccessible. The `decrypt_field` method silently catches the error and returns the encrypted blob unchanged (`manager.py:189-190`), meaning corrupted data propagates silently.
- Recommendation: Make `ENCRYPTION_KEY` a required environment variable. Fail fast on startup if not set. Implement key rotation support with versioned keys.

---

### High Priority Findings

**HIGH-001: Langfuse encryption key is all-zeros default**
- File: `paco/.env.example:26`
- Issue: `LANGFUSE_ENCRYPTION_KEY=0000000000000000000000000000000000000000000000000000000000000000` -- a 64-hex-char all-zeros key. If operators copy .env.example to .env without changing this value, all Langfuse data encryption uses a known key.
- Impact: Langfuse stores LLM traces which may contain citizen conversation data, PII, and sensitive queries about domestic violence, mental health, etc. A known encryption key renders this encryption useless.
- Recommendation: Remove the default value from .env.example. Add a startup validation that rejects all-zeros keys. Document key generation instructions.

**HIGH-002: Admin API key comparison is not constant-time**
- File: `gobierno-queretaro/orchestrator/admin.py:36`
- Issue: The admin key validation uses Python's `!=` operator (`if key != ADMIN_API_KEY`), which is vulnerable to timing attacks. String comparison with `!=` in Python returns as soon as a mismatch is found, leaking information about how many leading characters of the key are correct.
- Impact: An attacker with network access could determine the admin API key character-by-character through timing analysis, especially since admin endpoints have no rate limiting beyond the global limiter.
- Recommendation: Use `hmac.compare_digest(key, ADMIN_API_KEY)` for constant-time comparison. Also add the `ADMIN_API_KEY` to an empty-string check before comparison (already done at line 33-34, which is good).

**HIGH-003: CEA SOAP credentials hardcoded in source code across multiple files**
- Files: `src/tools.ts:234-235`, `maria-claude/src/tools.ts:120-121`, `maria-v2/src/tools.ts:170-171`, `maria-v3/src/tools.ts:114-115`, `maria-voz/src/services/cea-api.ts:109-110`, `paco/mcp-servers/cea-tools/src/server.ts:88-89`, and more (approximately 15 files)
- Issue: The WSSE credentials `WSGESTIONDEUDA/WSGESTIONDEUDA` for the CEA water service SOAP API are hardcoded as string literals directly in source code across multiple codebases. While `gobierno-queretaro/agents/water-cea/config.py:36-37` uses environment variables with these as defaults, the older codebases embed them directly.
- Impact: Credentials for a government water utility API are visible in the repository. If these credentials provide write access or can be used to look up citizen water accounts, this represents unauthorized access to government infrastructure.
- Recommendation: Move all SOAP credentials to environment variables. Remove hardcoded values from source. Rotate the credentials immediately since they have been committed to the repository.

**HIGH-004: Sensitive internal exceptions leaked in HTTP error responses**
- Files: `gobierno-queretaro/orchestrator/main.py:713,738,818`, `gobierno-queretaro/agents/vehicles/main.py:160`, and all 13 agent main.py files, `gobierno-queretaro/orchestrator/admin.py:187,254,432`, `gobierno-queretaro/voice-gateway/main.py:311,342,403,416`
- Issue: Exception messages are passed directly to HTTP responses via `detail=f"Agent error: {str(e)}"` or `detail=str(e)`. Python exception messages can contain internal paths, database connection strings, SQL queries, stack trace fragments, or other sensitive system information.
- Impact: An attacker can trigger errors to enumerate internal service URLs, database schemas, file paths, and software versions. For a government system handling sensitive data, information disclosure is particularly dangerous.
- Recommendation: Return generic error messages to clients. Log the full exception internally. Use unique error correlation IDs that operators can use to find detailed logs.

**HIGH-005: Open user registration with no controls**
- File: `paco/backend/app/api/auth.py:103-146`
- Issue: The `/auth/register` endpoint allows anyone to create a user account with no email verification, CAPTCHA, admin approval, or rate limiting specific to registration. New users get `viewer` role by default, which grants read access to all agents, executions, and metrics.
- Impact: An attacker can create unlimited accounts to access the PACO Hub dashboard, view agent configurations, execution traces, and potentially sensitive operational data.
- Recommendation: Either disable open registration (require admin to create users), add email domain restrictions (e.g., only `@queretaro.gob.mx`), or require admin approval for new accounts. Add registration-specific rate limiting.

**HIGH-006: No password strength validation**
- File: `paco/backend/app/api/auth.py:22-25` (LoginRequest/RegisterRequest models)
- Issue: The `RegisterRequest` model accepts any string as a password with no minimum length, complexity requirements, or common password checking. The `password: str` field has no validators.
- Impact: Users can set single-character or empty-string passwords, making brute-force attacks trivial against the government management dashboard.
- Recommendation: Add Pydantic validators for minimum password length (12+ characters for a government system), complexity requirements, and a check against common password lists.

---

### Medium Priority Findings

**MED-001: Agent registration and heartbeat endpoints have no authentication**
- File: `gobierno-queretaro/orchestrator/main.py:464-473` (v1 registration/heartbeat)
- Issue: The `/v1/register` and `/v1/heartbeat` endpoints allow any caller to register arbitrary agents in the dynamic registry or send heartbeats for existing agents, with no authentication.
- Impact: An attacker could register a malicious agent that receives citizen queries routed by the orchestrator, intercepting sensitive conversations. They could also send heartbeats for legitimate agents to prevent the health sweep from deactivating compromised endpoints.
- Recommendation: Require the admin API key or a shared registration secret for these endpoints.

**MED-002: Redis has no authentication configured**
- Files: `gobierno-queretaro/docker-compose.yml:474-488`, `gobierno-queretaro/orchestrator/config.py:31` (`redis://localhost:6379` -- no password)
- Issue: Redis is deployed without authentication (`redis:7-alpine` with no `--requirepass` or custom config). While the port is not mapped to the host, any container on the Docker network can access Redis without credentials.
- Impact: Redis stores audit logs, session data, and memory snapshots. A compromised container can read/modify all audit trails and session state, potentially erasing evidence of an intrusion.
- Recommendation: Configure Redis with a password via `--requirepass` and update all `REDIS_URL` references to include the password.

**MED-003: TLS verification disabled for API health checks**
- File: `gobierno-queretaro/orchestrator/admin.py:364`
- Issue: The admin API health check endpoint creates an httpx client with `verify=False`, disabling TLS certificate verification.
- Impact: Health check requests to external government APIs (like CEA) are vulnerable to man-in-the-middle attacks, allowing interception or modification of health check responses.
- Recommendation: Remove `verify=False` or use a proper CA bundle. If self-signed certificates are used internally, configure the specific CA.

**MED-004: Audit log durability -- Redis-only with no persistence guarantees**
- File: `gobierno-queretaro/shared/security/audit.py:116-232`
- Issue: Audit events are stored exclusively in Redis streams (`xadd` at line 228-232). The Redis instance uses a default Docker volume with no explicit persistence configuration (no `appendonly yes` or custom `save` directives in docker-compose.yml). The `maxlen=100000` truncation at line 232 means old events are automatically deleted.
- Impact: For a government system requiring compliance audit trails, audit logs can be lost on Redis restart or Docker volume issues. The 100K event cap means historical audit data is silently discarded.
- Recommendation: Add a PostgreSQL sink for audit events (the code mentions "optional PostgreSQL storage" at line 124 but it is not implemented). Configure Redis with `appendonly yes` for AOF persistence. Consider increasing or making `max_stream_length` configurable.

**MED-005: JWT tokens have excessively long expiration (7 days)**
- File: `paco/backend/app/core/config.py:30`
- Issue: `access_token_expire_minutes: int = 60 * 24 * 7` sets tokens to expire after 7 days. There is no refresh token mechanism with shorter access token lifetimes, and no token revocation/blacklist capability.
- Impact: If a JWT is stolen, it remains valid for a full week. There is no way to revoke a compromised token short of rotating the signing key (which invalidates all active sessions).
- Recommendation: Reduce access token expiration to 15-60 minutes. Implement refresh tokens with longer expiration. Add a token revocation mechanism (e.g., Redis-based blacklist).

**MED-006: Frontend stores JWT in localStorage via Zustand persist**
- File: `paco/frontend/lib/auth.ts:105-117`
- Issue: The auth store uses Zustand's `persist` middleware with default `localStorage` storage (the `name: "paco-auth"` config at line 106 stores token and user data in localStorage).
- Impact: JWTs in localStorage are accessible to any JavaScript running on the page, making them vulnerable to XSS attacks. Unlike httpOnly cookies, localStorage provides no protection against cross-site scripting.
- Recommendation: Use httpOnly, Secure, SameSite cookies for JWT storage. If localStorage must be used, implement shorter token lifetimes and consider using a BFF (Backend For Frontend) pattern.

**MED-007: PII detection regex patterns have significant false positive potential**
- File: `gobierno-queretaro/shared/security/patterns.py:39-41`
- Issue: The `PHONE_MX` pattern (`(?:\+?52)?[\s.-]?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}\b`) is very broad and will match many numeric sequences that are not phone numbers (e.g., contract numbers, reference IDs, dates). The `CREDIT_CARD` pattern (`\b(?:\d{4}[\s.-]?){3,4}\d{1,4}\b`) will match any sequence of 13-19 digits. The `PASSPORT` pattern (`\b[A-Z]\d{8}\b`) matches any single letter followed by 8 digits.
- Impact: False positives cause legitimate data to be redacted in audit logs and responses, potentially hiding important operational information. False negatives (missed PII) leave citizen data exposed in logs.
- Recommendation: Add Luhn checksum validation for credit cards. Tighten phone pattern with boundary conditions. Add validation functions (like the existing `validate_curp` and `validate_rfc` in `manager.py:308-362`) for other PII types. Consider using the validators before masking, not just the regex.

**MED-008: Pseudonymization salt is non-deterministic when env var is missing**
- File: `gobierno-queretaro/shared/security/manager.py:288`
- Issue: `salt = salt or os.getenv("CITIZEN_ID_SALT", secrets.token_hex(16))` -- when `CITIZEN_ID_SALT` is not set, a new random salt is generated on every call. This means the same citizen ID produces different pseudonymized hashes across calls.
- Impact: The purpose of pseudonymization is to allow linking records without storing the actual ID. With a random salt per call, records cannot be linked, defeating the entire purpose of the function.
- Recommendation: Make `CITIZEN_ID_SALT` a required environment variable. Fail if not configured, or generate and persist the salt on first use.

---

### Low Priority / Improvements

**LOW-001: Feedback endpoint has no authentication or rate limiting**
- File: `gobierno-queretaro/orchestrator/feedback.py:60-99`
- Issue: The `/feedback` POST endpoint accepts feedback from anyone with no authentication and only the global rate limiter (not feedback-specific).
- Impact: An attacker could flood the system with fake feedback scores, poisoning the RL/APO training pipeline.
- Recommendation: Require at least a conversation ID validation (verify the conversation exists) and consider adding a simple HMAC-based webhook signature.

**LOW-002: Admin dashboard UI served without authentication**
- File: `gobierno-queretaro/orchestrator/admin.py:439-446`
- Issue: The `/admin/ui` endpoint serves the admin dashboard HTML without requiring the admin API key. While the dashboard's API calls require the key, the UI itself is publicly accessible.
- Impact: Low direct risk, but exposes the admin interface structure and may aid reconnaissance.
- Recommendation: Add `dependencies=[Depends(verify_admin_key)]` or implement session-based auth for the UI.

**LOW-003: No input size validation on message fields**
- File: `gobierno-queretaro/orchestrator/main.py:182` (`message: str` in RouteRequest)
- Issue: The `message` field in RouteRequest and all agent QueryRequest models has no maximum length constraint. A very large message could consume excessive LLM tokens/costs.
- Impact: DoS via large message payloads that get forwarded to the LLM API, causing high costs.
- Recommendation: Add `Field(max_length=10000)` or similar constraints to message fields.

**LOW-004: Docker Compose exposes Jaeger ports to host**
- File: `gobierno-queretaro/docker-compose.yml:458-460`
- Issue: Jaeger UI (16686), OTLP gRPC (4317), and OTLP HTTP (4318) ports are mapped to the host with no authentication.
- Impact: Anyone on the network can view all distributed traces, which contain agent routing decisions, conversation flow, and potentially PII in trace attributes.
- Recommendation: Remove host port mappings or restrict to localhost (`127.0.0.1:16686:16686`). Add authentication if Jaeger must be externally accessible.

**LOW-005: No HTTPS/TLS termination in the application layer**
- Files: `gobierno-queretaro/docker-compose.yml` (no TLS config), `gobierno-queretaro/orchestrator/main.py:838` (uvicorn without SSL)
- Issue: No service in the docker-compose stack terminates TLS. All inter-service communication is plaintext HTTP. There is no reverse proxy (nginx, Traefik) configured for TLS termination.
- Impact: In a production deployment without an external load balancer providing TLS, all citizen data travels in plaintext, including PII, CURP, and crisis-related conversations.
- Recommendation: Add a reverse proxy (e.g., Traefik) to the docker-compose stack for TLS termination, or document that TLS is expected to be handled by the infrastructure layer (cloud load balancer, etc.).

**LOW-006: Secrets rotation strategy is absent**
- Files: All `.env.example` files
- Issue: There is no documentation or mechanism for rotating secrets (API keys, encryption keys, JWT signing keys, database passwords). The encryption key auto-generation in SecurityManager would break existing encrypted data on rotation.
- Impact: If any secret is compromised, there is no documented procedure for rotation without downtime or data loss.
- Recommendation: Document a secrets rotation procedure. Implement key versioning for the encryption system. Add a key rotation management utility.

---

### Positive Observations

1. **Comprehensive PII detection framework**: The `shared/security/patterns.py` module covers Mexican-specific PII types (CURP, RFC, INE, NSS) beyond just the standard email/credit card patterns. The masking system is well-structured with configurable partial preservation.

2. **Structured audit logging**: The `AuditLogger` class in `audit.py` provides a well-designed audit trail with event types, confidentiality levels, actor tracking, and automatic PII sanitization before logging. The event type taxonomy is thorough.

3. **Security middleware integration**: The `SecurityMiddleware` in `orchestrator/main.py` automatically scans incoming requests for PII and creates audit entries, providing defense-in-depth even if individual endpoints don't explicitly handle PII.

4. **RBAC in PACO Hub backend**: The `paco/backend/app/core/deps.py` implements proper role-based access control with `RoleChecker` dependency injection, supporting admin/operator/viewer roles with clean FastAPI integration.

5. **Bcrypt password hashing**: `paco/backend/app/core/security.py` uses `passlib` with bcrypt for password hashing, which is the recommended approach.

6. **Rate limiting on routing endpoints**: The orchestrator uses `slowapi` with per-IP rate limiting and proper 429 responses with `Retry-After` headers.

7. **Admin API key protection**: All memory management and admin endpoints in `admin.py` use the `verify_admin_key` dependency, and the system properly returns 503 when the key is not configured rather than silently allowing access.

8. **Field-level encryption**: The `SecurityManager` provides Fernet-based field-level encryption for sensitive data storage, not just transport-level encryption.

9. **.env in .gitignore**: The root `.gitignore` and `maria-claude/.gitignore` both exclude `.env` files, preventing accidental credential commits.

---

### OWASP Top 10 Coverage

| OWASP Category | Findings | Status |
|---|---|---|
| **A01:2021 - Broken Access Control** | CRIT-002 (unauthenticated agent endpoints), HIGH-005 (open registration), MED-001 (unauthenticated registration/heartbeat) | CRITICAL |
| **A02:2021 - Cryptographic Failures** | CRIT-004 (weak JWT secret), CRIT-005 (ephemeral encryption key), HIGH-001 (all-zeros Langfuse key), MED-008 (random pseudonymization salt) | CRITICAL |
| **A03:2021 - Injection** | HIGH-004 (error message leakage may expose SQL context). No direct SQL injection found (uses ORM/parameterized queries). No HTML sanitization but responses are JSON-only. | MEDIUM |
| **A04:2021 - Insecure Design** | CRIT-002 (agents directly accessible bypassing security layer), MED-004 (audit log durability) | HIGH |
| **A05:2021 - Security Misconfiguration** | CRIT-001 (wildcard CORS), CRIT-003 (hardcoded DB creds), MED-002 (Redis no auth), MED-003 (TLS verify disabled), LOW-004 (Jaeger exposed) | CRITICAL |
| **A06:2021 - Vulnerable and Outdated Components** | Not assessed (no dependency audit performed -- recommend running `pip audit` and `npm audit`) | UNKNOWN |
| **A07:2021 - Identification and Authentication Failures** | CRIT-004 (guessable JWT secret), HIGH-002 (timing attack on admin key), HIGH-006 (no password policy), MED-005 (7-day JWT expiry) | CRITICAL |
| **A08:2021 - Software and Data Integrity Failures** | LOW-001 (unauthenticated feedback poisoning RL training) | LOW |
| **A09:2021 - Security Logging and Monitoring Failures** | MED-004 (Redis-only audit with truncation), positive: SecurityMiddleware auto-logging | MEDIUM |
| **A10:2021 - Server-Side Request Forgery** | MED-001 (agent registration can point to arbitrary URLs that orchestrator will call) | MEDIUM |

---

### Metrics

- Files reviewed: 32
- Critical findings: 5
- High findings: 6
- Medium findings: 8
- Low findings: 6
- OWASP categories with critical exposure: 4 of 10
