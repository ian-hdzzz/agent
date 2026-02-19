# PACO System Audit: Code Quality & Testing

**Auditor:** Code Quality & Testing Reviewer
**Date:** 2026-02-07
**Scope:** Test suite, orchestrator Python modules, shared libraries, agent template & implementations, frontend test config, requirements files, configuration patterns

---

## Executive Summary

The PACO codebase demonstrates solid foundational architecture with a well-designed agent template pattern, comprehensive intent classification tests, and a resilient HTTP client with circuit breaker support. However, **critical gaps in test coverage** leave the security module, memory system, session management, admin API, and 11 of 13 agent implementations entirely untested. The test infrastructure relies on a **brittle sys.modules stubbing pattern** that will become increasingly fragile as the system grows. **No dependency pinning** across any requirements file creates reproducibility and supply-chain risks for a production government system. Broad exception handling masks specific errors throughout the orchestrator, and a hardcoded default secret key in the backend config represents a direct security risk.

**Overall Code Quality Grade: C+**
- Test coverage estimated at **15-20%** of total codebase
- 3 Critical findings, 6 High findings, 7 Medium findings, 4 Low findings

---

## Critical Findings

### CRIT-01: Minimal Test Coverage Across Critical Subsystems

**Files affected:** Entire `shared/` directory, `orchestrator/admin.py`, `orchestrator/feedback.py`, 11 of 13 agents, `voice-gateway/`, `training/`

**Description:**
Only the following modules have any test coverage:
- Orchestrator router (`test_router.py` - 16 tests)
- Orchestrator classifier (`test_classifier.py` - ~50 tests, most thorough)
- Vehicles agent tools (`test_vehicle_tools.py`)
- Water agent tools (`test_water_tools.py`)
- Orchestrator API integration (`test_orchestrator_api.py`)
- Agent contract compliance (`test_agent_contract.py`)
- Circuit breaker (`test_circuit_breaker.py`)

**Completely untested subsystems:**
| Module | Risk Level | Reason |
|--------|-----------|--------|
| `shared/security/manager.py` | **Extreme** | PII detection, encryption, citizen ID pseudonymization |
| `shared/security/patterns.py` | **Extreme** | Mexican PII regex patterns (CURP, RFC, INE, NSS) |
| `shared/security/audit.py` | **High** | Redis-backed audit event logging |
| `shared/memory/engine.py` | **High** | PacoMemory scoped operations, GDPR forget |
| `shared/memory/store.py` | **High** | PostgreSQL CRUD, Redis caching, data anonymization |
| `shared/context/session.py` | **High** | SessionContext with per-agent data vaults |
| `shared/registration.py` | **Medium** | Agent self-registration and heartbeat |
| `orchestrator/admin.py` | **High** | Admin API with GDPR forget, citizen management |
| `orchestrator/feedback.py` | **Low** | Simple reward emission |
| 11 agent implementations | **High** | Only vehicles tools tested; water, transport, education, psychology, women, culture, registry, labor, housing, appqro, social, citizen-attention all untested |
| `voice-gateway/` | **Medium** | Entire voice gateway module |
| `training/` | **Medium** | Training pipeline |

**Impact:** A production government system handling citizen PII has zero tests validating its PII detection accuracy, encryption correctness, or GDPR compliance mechanisms.

**Recommendation:**
1. Immediately add unit tests for `shared/security/patterns.py` (PII regex validation against known CURP/RFC/INE formats)
2. Add unit tests for `shared/security/manager.py` (encryption round-trip, PII masking accuracy)
3. Add integration tests for `shared/memory/store.py` (GDPR forget completeness)
4. Establish minimum coverage thresholds: 80% for `shared/security/`, 70% for `shared/memory/`, 60% overall

---

### CRIT-02: Hardcoded Default Secret Key in Backend Config

**File:** `paco/backend/app/core/config.py:28`

**Code:**
```python
secret_key: str = "your-secret-key-change-me-in-production"
```

**Impact:** If the `SECRET_KEY` environment variable is not set, the application runs with a publicly known secret key. This affects JWT token signing, session security, and any cryptographic operations depending on this key. An attacker who discovers this default can forge tokens or decrypt sensitive data.

**Recommendation:**
1. Remove the default value entirely; fail fast if `SECRET_KEY` is not set
2. Add a startup validation that raises an error if the secret key matches the default pattern
3. Add to deployment checklist and CI validation

---

### CRIT-03: Security Module Generates Ephemeral Encryption Key on Startup

**File:** `gobierno-queretaro/shared/security/manager.py:52`

**Code:**
```python
if not self._encryption_key:
    logger.warning("ENCRYPTION_KEY not configured - generating ephemeral key")
    self._encryption_key = Fernet.generate_key().decode()
```

**Impact:** If `ENCRYPTION_KEY` is not set, a new random key is generated on every startup. Any data encrypted in a previous session becomes permanently undecryptable. In a multi-instance deployment, each instance has a different key, making encrypted data unreadable across instances. This is especially dangerous for the PII masking and citizen ID pseudonymization features.

**Recommendation:**
1. Fail fast in production if `ENCRYPTION_KEY` is not configured
2. Add environment validation at startup (distinguish dev/prod behavior)
3. Document key management requirements in deployment guide

---

## High Findings

### HIGH-01: Brittle sys.modules Mocking Strategy in Test Suite

**Files:** `tests/conftest.py:35-111`, `tests/unit/agents/test_vehicle_tools.py:8-51`, `tests/unit/agents/test_water_tools.py`, `tests/integration/test_circuit_breaker.py`

**Description:**
The test suite uses a fragile strategy of injecting fake modules into `sys.modules` before imports to avoid loading heavy dependencies (agentlightning, shared.memory, shared.security, etc.):

```python
# conftest.py lines 35-111
fake_al = types.ModuleType("agentlightning")
fake_al.trace = lambda *a, **kw: (lambda fn: fn)
# ... 76 lines of fake module setup
sys.modules["agentlightning"] = fake_al
sys.modules["shared.memory"] = fake_shared_memory
# etc.
```

Individual test files duplicate this pattern with their own variations:
```python
# test_vehicle_tools.py lines 8-51
fake_shared = types.ModuleType("shared")
fake_utils = types.ModuleType("shared.utils")
# ... 43 lines of module injection
```

**Problems:**
1. **Fragility:** Adding any new import to production code silently breaks tests without clear error messages
2. **Duplication:** Each test file creates its own slightly different fake modules
3. **Inconsistency:** test_circuit_breaker.py uses `importlib.import_module` to bypass the conftest stubs entirely (line 23), proving the strategy is already being worked around
4. **Maintenance burden:** Every new shared module requires updating multiple fake module registrations

**Recommendation:**
1. Replace sys.modules manipulation with proper mocking using `unittest.mock.patch` or `pytest-mock`
2. Create shared test fixtures for common mocks (Anthropic client, HTTP client, Redis, asyncpg)
3. Use dependency injection in production code to make testing natural
4. Consider `conftest.py` fixtures with `autouse=True` for session-scoped mocks

---

### HIGH-02: Broad Exception Catches Masking Specific Errors

**Files and locations:**

| File | Lines | Context |
|------|-------|---------|
| `orchestrator/main.py` | 133, 286-287, 321, 350, 697-698, 709 | Route handling, classification, agent calls |
| `orchestrator/router.py` | ~400 (multiple) | Tracing calls, agent routing |
| `orchestrator/classifier.py` | 568 | LLM classification fallback |
| `orchestrator/admin.py` | 374, 431 | Health checks, memory operations |
| `orchestrator/config.py` | 224, 366, 384, 424 | DB operations |
| `shared/memory/store.py` | Multiple | All DB and Redis operations |
| `shared/memory/engine.py` | Multiple | Memory recall/store |
| `shared/security/audit.py` | Multiple | Redis stream operations |

**Pattern:**
```python
try:
    # operation
except Exception as e:
    logger.warning(f"Something failed: {e}")
    return fallback_value
```

**Impact:**
- `ConnectionError`, `TimeoutError`, `ValueError`, `TypeError`, `KeyError` all caught identically
- Transient network errors get same treatment as programming bugs
- Makes debugging production issues significantly harder
- Retry logic (tenacity) cannot distinguish retryable from non-retryable errors

**Recommendation:**
1. Catch specific exception types: `httpx.TimeoutException`, `asyncpg.PostgresError`, `redis.RedisError`, `anthropic.APIError`
2. Let programming errors (`TypeError`, `KeyError`, `AttributeError`) propagate
3. Use exception hierarchies: catch `httpx.HTTPStatusError` separately from `httpx.ConnectError`
4. Add structured error context to log messages

---

### HIGH-03: No Dependency Pinning in Any Requirements File

**Files:** All `requirements.txt` across the project

| File | Pinning Style | Example |
|------|--------------|---------|
| `orchestrator/requirements.txt` | All `>=` | `langgraph>=0.2.0`, `fastapi>=0.115.0` |
| `agents/_template/requirements.txt` | All `>=` | Same as orchestrator |
| `paco/backend/requirements.txt` | All `>=` except one | `bcrypt==4.0.1` (only pinned dep) |
| `voice-gateway/requirements.txt` | All `>=` | `fastapi>=0.115.0` |
| `training/requirements.txt` | All `>=` | `anthropic>=0.40.0` |
| `tests/requirements-test.txt` | All `>=` | `pytest>=8.0.0` |

**Impact:**
- Non-reproducible builds: `pip install` today produces different packages than tomorrow
- Breaking changes in minor/patch versions can silently break production
- Supply chain risk: a compromised upstream package version is automatically pulled
- Government compliance may require reproducible, auditable builds

**Recommendation:**
1. Add a `requirements.lock` or use `pip-compile` (pip-tools) to generate pinned lockfiles
2. Pin direct dependencies to exact versions in production requirements
3. Use `>=` only in library development, not application deployment
4. Implement Dependabot or Renovate for automated dependency update PRs
5. At minimum, pin critical security-sensitive packages: `cryptography`, `anthropic`, `pydantic`

---

### HIGH-04: Vehicles Agent Diverges Significantly from Template

**Files:** `agents/vehicles/main.py` vs `agents/_template/main.py`

**Missing from vehicles agent:**
| Feature | Template | Vehicles |
|---------|----------|----------|
| Self-registration with orchestrator | Yes (line 91) | **No** |
| Heartbeat loop | Yes (line 94) | **No** |
| PacoMemory support | Yes (lines 81-109) | **No** |
| `/metrics` endpoint | Yes (line 226) | **No** |
| `/memory/{contact_id}` endpoint | Yes (line 210) | **No** |
| `/.well-known/agent.json` A2A card | Yes (line 264) | **No** |
| Agent Card builder | Yes (line 252) | **No** |

**Additional divergences in vehicles/config.py:**
- Missing fields: `capabilities`, `version`, `sla_tier`, `memory_enabled`, `confidentiality_level`
- Cannot generate `to_registration_payload()` required by registration module
- No `to_info_dict()` method

**Impact:** The vehicles agent cannot be dynamically discovered by the orchestrator, has no health monitoring, no memory persistence, and no A2A protocol compliance. The static registry fallback in `orchestrator/config.py:128-133` is the only reason it works.

**Recommendation:**
1. Migrate vehicles agent to use the template pattern
2. Add a CI check that validates all agents implement the required interface (the contract test in `test_agent_contract.py` is a good start but only validates HTTP endpoints, not registration behavior)
3. Create a compliance script that diffs each agent against the template

---

### HIGH-05: Admin API Uses `verify=False` for HTTPS

**File:** `gobierno-queretaro/orchestrator/admin.py:364`

**Code:**
```python
async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
```

**Impact:** Disables TLS certificate verification for health check requests to agents. In a production environment, this allows man-in-the-middle attacks between the orchestrator and agents. Even for internal health checks, this sets a dangerous precedent.

**Recommendation:**
1. Use proper CA certificates or configure a custom CA for internal services
2. If self-signed certs are used internally, configure `httpx.AsyncClient(verify="/path/to/internal-ca.pem")`
3. Never disable TLS verification in production code

---

### HIGH-06: Missing Async in Classifier LLM Call

**File:** `gobierno-queretaro/orchestrator/classifier.py`

**Description:** The `llm_classify` function uses the synchronous Anthropic SDK (`anthropic.Anthropic().messages.create()`) rather than the async variant (`anthropic.AsyncAnthropic().messages.create()`). Since this is called from an async FastAPI endpoint via the LangGraph orchestrator, it blocks the event loop during LLM inference.

**Impact:** Under concurrent load, a single slow LLM classification blocks all other requests on the same event loop thread. This is especially problematic because LLM calls can take 2-10 seconds.

**Recommendation:**
1. Switch to `anthropic.AsyncAnthropic` and `await client.messages.create()`
2. Or wrap in `asyncio.to_thread()` as a temporary fix
3. The `llm_classify_structured` function has the same issue

---

## Medium Findings

### MED-01: DRY Violation with Backward-Compatible Route Aliases

**File:** `gobierno-queretaro/orchestrator/main.py:544-592`

**Description:** Seven route handlers duplicate v1 endpoints as unversioned aliases:

```python
# Line 544-592: Backward-compatible aliases
@app.post("/route")
async def route_compat(request: RouteRequest): ...
    # Calls same _do_route()

@app.post("/classify")
async def classify_compat(request: ClassifyRequest): ...
    # Calls same _do_classify()

# ... 5 more aliases
```

While the aliases share implementation functions (`_do_route`, `_do_classify`), the endpoint definitions, decorators, and any future middleware/rate-limiting/auth must be maintained in parallel.

**Recommendation:**
1. Use FastAPI's `APIRouter` with `include_router` and prefix stripping
2. Or use redirect responses (HTTP 301) from old paths to `/v1/` paths
3. Set a deprecation timeline and remove old routes

---

### MED-02: Inconsistent Configuration Pattern (BaseSettings + os.getenv)

**Files:** `orchestrator/config.py:22-70`, `agents/_template/config.py`, `agents/vehicles/config.py:20-29`

**Pattern:**
```python
class OrchestratorSettings(BaseSettings):
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://...")
```

**Problem:** `pydantic-settings` `BaseSettings` already reads environment variables automatically. Using `os.getenv()` as the default value means:
1. The value is read at **import time**, not at instantiation time
2. `.env` file support via `Config.env_file` is bypassed (os.getenv runs first)
3. Environment variable precedence is inverted from what `BaseSettings` provides
4. Testing with environment overrides behaves unexpectedly

**Recommendation:**
```python
class OrchestratorSettings(BaseSettings):
    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gobierno"

    class Config:
        env_file = ".env"
```

---

### MED-03: Excessive Lazy Imports Inside Functions

**Files:** `orchestrator/main.py` (lines 277, 293, 317, 347, 601, 641-642, 686-687, 719, 781), `orchestrator/admin.py` (lines 61, 166, 181, 248, 262, 325), `orchestrator/config.py` (multiple)

**Description:** Over 20 instances of imports inside function bodies:

```python
async def _do_route(...):
    from .config import get_agent_registry  # line 277
    from .classifier import classify_intent  # line 293
```

**Root cause:** Circular import dependencies between orchestrator modules.

**Impact:**
- Import errors surface at runtime, not at startup
- Harder to trace dependencies
- Small performance overhead on every function call (Python caches, but lookup still occurs)
- IDE tooling struggles with type resolution

**Recommendation:**
1. Refactor module boundaries to break circular dependencies
2. Use a dependency injection pattern or a central "wiring" module
3. If lazy imports are truly needed, consolidate them into a single `_imports.py` module with clear documentation

---

### MED-04: Frontend Has Jest Config but Nearly Zero Tests

**Files:** `paco/frontend/jest.config.js`, `paco/frontend/jest.setup.ts`

**Test files found:** Only 2 test files in `paco/frontend/`:
- `components/builder/code-generation/workflow-to-ir.test.ts`
- `components/builder/code-generation/ir-to-typescript.test.ts`

**Missing test coverage for:**
- All React components
- State management
- API client layer
- Form validation
- User authentication flows
- Routing
- Error boundaries

**Recommendation:**
1. Add component tests for critical user-facing features first
2. Use React Testing Library (already configured in jest.setup.ts)
3. Add snapshot tests for key UI components
4. Target 50% coverage for frontend as initial milestone

---

### MED-05: Multiple Singleton Patterns with Global Variables

**Files:** `orchestrator/config.py:429-437`, `shared/utils/http_client.py`, `shared/memory/engine.py`, `orchestrator/router.py`

**Pattern:**
```python
_registry: AgentRegistry | None = None

def _get_registry_instance() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
```

**Problems:**
1. Not thread-safe (though less critical in async Python)
2. Makes testing difficult - global state persists between tests
3. No cleanup mechanism for graceful shutdown
4. Scattered across multiple modules with no consistent pattern

**Recommendation:**
1. Use FastAPI's dependency injection system (`Depends()`) for request-scoped or app-scoped instances
2. Store singletons on the FastAPI `app.state` object
3. Use `@lru_cache()` consistently (already used for `get_settings()`)

---

### MED-06: Raw SQL Queries Without Parameterized Safeguards Documentation

**File:** `gobierno-queretaro/shared/memory/store.py`

**Description:** The memory store uses raw SQL with `asyncpg` parameterized queries (`$1`, `$2`, etc.), which is correct and safe. However, there are no SQL injection tests, no documentation of the parameterization strategy, and no safeguards against accidental string interpolation. Given that citizen-provided data (names, IDs, messages) flows through these queries, a single f-string mistake would create a SQL injection vulnerability.

**Recommendation:**
1. Add a linting rule or code review checklist item to flag f-strings near SQL
2. Add SQL injection tests with adversarial input
3. Consider using SQLAlchemy's query builder for compile-time safety (already in requirements but not used)

---

### MED-07: Inconsistent Error Response Formats

**Files:** `orchestrator/main.py`, `orchestrator/admin.py`, `agents/_template/main.py`

**Description:** Error responses use different formats across endpoints:

```python
# main.py - HTTPException with detail string
raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

# main.py - JSON response with error field
return {"error": str(e), "category": None, ...}

# admin.py - HTTPException with detail string
raise HTTPException(status_code=500, detail=f"Memory error: {str(e)}")

# Template - HTTPException
raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
```

**Impact:** API consumers cannot rely on a consistent error schema. Some errors are HTTP 500 with `detail`, others are HTTP 200 with an `error` field in the body.

**Recommendation:**
1. Define a standard `ErrorResponse` Pydantic model
2. Use FastAPI exception handlers for consistent error formatting
3. Always use appropriate HTTP status codes (don't return 200 with error field)

---

## Low Findings

### LOW-01: Mixed Type Hint Styles

**Files:** Multiple files across the codebase

**Description:** The codebase mixes Python 3.10+ union syntax (`X | None`) with the older `Optional[X]` from `typing`:

```python
# Modern style (used in most files)
conversation_id: str | None = None

# Legacy style (used in some files)
from typing import Optional
value: Optional[str] = None
```

**Recommendation:** Standardize on `X | None` syntax throughout. Add ruff rule `UP007` to enforce.

---

### LOW-02: Logging Inconsistency

**Files:** All Python modules

**Description:**
- Orchestrator uses `structlog` in requirements but `logging.getLogger(__name__)` in code
- Some modules use `f-string` formatting in log calls (evaluated even when log level is disabled)
- No structured logging fields (JSON) despite structlog being a dependency

**Recommendation:**
1. Either adopt structlog fully or remove it from requirements
2. Use lazy formatting: `logger.info("Registered: %s", agent_id)` instead of f-strings
3. Add correlation IDs for request tracing

---

### LOW-03: Missing `__init__.py` Files and Import Guards

**Files:** Various agent and shared module directories

**Description:** Some directories have `__init__.py` files while others rely on implicit namespace packages. This inconsistency can cause import issues depending on the Python path configuration and tool support.

**Recommendation:** Add `__init__.py` to all Python package directories for explicit package declarations.

---

### LOW-04: Commented-Out Dependencies

**File:** `gobierno-queretaro/training/requirements.txt`

**Code:**
```
# torch>=2.0.0
# vllm>=0.4.0
```

**Impact:** Minor - suggests incomplete implementation or deferred decision. Could confuse new developers about actual requirements.

**Recommendation:** Remove commented dependencies or add a clear comment explaining why they are deferred.

---

## Positive Observations

1. **Well-designed agent template pattern** (`agents/_template/`): The template provides a comprehensive, production-ready foundation including self-registration, heartbeat, A2A protocol compliance, memory integration, and standard endpoints. When agents follow it, the system is well-structured.

2. **Thorough classifier test suite** (`test_classifier.py`): With ~50 tests covering all 13 categories, ambiguity detection, entity extraction, urgency detection, and structured classification, this is the gold standard for the rest of the codebase.

3. **Circuit breaker implementation** (`shared/utils/http_client.py`): Clean state machine with proper state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED), configurable thresholds, per-service isolation, and well-tested with both unit and integration tests.

4. **Contract compliance testing** (`test_agent_contract.py`): Parametrized tests that validate all 13 agents implement the required HTTP interface. This is an excellent pattern for maintaining consistency across a large agent fleet.

5. **Mexican PII patterns** (`shared/security/patterns.py`): Comprehensive regex patterns for CURP, RFC, INE, NSS, and other Mexican government identifiers. Well-suited for the domain.

6. **Dynamic agent registry with static fallback** (`orchestrator/config.py`): Graceful degradation from DB-backed discovery to static configuration ensures the system operates even when PostgreSQL is unavailable.

7. **PacoMemory scoped architecture** (`shared/memory/engine.py`): Clean separation between agent-scoped and orchestrator-scoped memory operations with explicit access control.

8. **A2A Protocol compliance** via agent cards and `/.well-known/agent.json` endpoint in the template.

---

## Test Coverage Matrix

| Module | Unit Tests | Integration Tests | Coverage Estimate | Priority |
|--------|-----------|-------------------|-------------------|----------|
| `orchestrator/classifier.py` | ~50 tests | - | ~70% | Adequate |
| `orchestrator/router.py` | 16 tests | - | ~50% | Needs improvement |
| `orchestrator/main.py` | - | 12 tests | ~30% | **High priority** |
| `orchestrator/config.py` | - | - | 0% | Medium priority |
| `orchestrator/admin.py` | - | - | 0% | **High priority** |
| `orchestrator/feedback.py` | - | - | 0% | Low priority |
| `shared/security/manager.py` | - | - | 0% | **Critical priority** |
| `shared/security/patterns.py` | - | - | 0% | **Critical priority** |
| `shared/security/audit.py` | - | - | 0% | High priority |
| `shared/memory/engine.py` | - | - | 0% | **High priority** |
| `shared/memory/store.py` | - | - | 0% | **High priority** |
| `shared/context/session.py` | - | - | 0% | Medium priority |
| `shared/utils/http_client.py` | 8 tests | 3 tests | ~80% | Adequate |
| `shared/registration.py` | - | - | 0% | Medium priority |
| `agents/vehicles/tools.py` | 7 tests | - | ~60% | Adequate |
| `agents/water-cea/tools.py` | 5 tests | - | ~50% | Needs improvement |
| Other 11 agents | - | Contract only | <5% | **High priority** |
| `paco/frontend/` | 2 files | - | <5% | Medium priority |
| `paco/backend/` | - | - | 0% | Medium priority |
| `voice-gateway/` | - | - | 0% | Medium priority |

---

## Metrics

| Metric | Value |
|--------|-------|
| Total test files | 7 (unit: 4, integration: 3) |
| Estimated total test count | ~100 |
| Estimated line coverage | 15-20% |
| Critical findings | 3 |
| High findings | 6 |
| Medium findings | 7 |
| Low findings | 4 |
| Positive observations | 8 |
| Requirements files audited | 6 |
| Pinned dependencies | 1 of ~80+ (`bcrypt==4.0.1`) |
| Agents following template | 2 of 13 (estimated) |
| Broad exception catches | 20+ instances |
| Lazy function-level imports | 20+ instances |
| Frontend test files | 2 |
| Python files with zero test coverage | ~30+ |

---

## Recommended Priority Actions

1. **Immediate (Week 1):** Add tests for `shared/security/patterns.py` and `shared/security/manager.py` - these handle PII in a production government system
2. **Immediate (Week 1):** Remove or protect the hardcoded secret key in `paco/backend/app/core/config.py`
3. **Immediate (Week 1):** Require `ENCRYPTION_KEY` in production (fail-fast instead of ephemeral key)
4. **Short-term (Week 2-3):** Pin all dependencies with lockfiles; add `pip-compile` to CI
5. **Short-term (Week 2-3):** Add tests for `shared/memory/` and `orchestrator/admin.py`
6. **Medium-term (Month 1):** Migrate vehicles agent (and others) to template pattern
7. **Medium-term (Month 1):** Replace sys.modules mocking with proper test fixtures
8. **Medium-term (Month 1):** Switch classifier to async Anthropic client
9. **Ongoing:** Narrow exception catches as bugs are fixed; establish exception handling guidelines
