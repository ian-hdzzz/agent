# Architecture

**Analysis Date:** 2026-02-03

## Pattern Overview

**Overall:** Layered Web Application Architecture with separate frontend and backend services

**Key Characteristics:**
- Frontend-backend separation (Next.js + FastAPI)
- RESTful API design with JWT authentication
- Async/await throughout backend for I/O operations
- Database-driven agent registry and execution tracking
- Role-based access control (admin, operator, viewer)
- Integration with external observability (Langfuse) and process management (PM2)

## Layers

**Presentation Layer (Frontend):**
- Purpose: Web-based control plane UI for agent management and observability
- Location: `frontend/`
- Contains: Next.js pages, React components, TypeScript utilities
- Depends on: Backend API, local state (Zustand stores)
- Used by: End users (browser clients)

**API Gateway Layer (Backend):**
- Purpose: REST endpoints managing agents, tools, executions, users, and authentication
- Location: `backend/app/api/`
- Contains: FastAPI routers (agents.py, tools.py, executions.py, users.py, auth.py, proxy.py)
- Depends on: Service layer, dependency injection, database session
- Used by: Frontend, external API consumers

**Service Layer (Backend):**
- Purpose: Business logic for agent lifecycle, PM2 process management, and observability
- Location: `backend/app/services/`
- Contains: AgentManager (lifecycle), PM2Client (process control), Langfuse integration
- Depends on: Database models, external service clients (PM2, Langfuse)
- Used by: API layer endpoints

**Data Access Layer (Backend):**
- Purpose: Database models and session management
- Location: `backend/app/db/`
- Contains: SQLAlchemy ORM models (User, Agent, MCP Server, Tool, Execution, ToolCall), async session factory
- Depends on: PostgreSQL database, SQLAlchemy
- Used by: Service layer and API endpoints via dependency injection

**Infrastructure Layer:**
- Purpose: Configuration, security, and dependency injection
- Location: `backend/app/core/`
- Contains: Settings (config.py), JWT/role-based security (security.py), FastAPI dependencies (deps.py)
- Depends on: Environment variables, database engine
- Used by: All backend layers

## Data Flow

**Agent Management Flow:**

1. User interacts with Agent page in frontend (`frontend/app/agents/page.tsx`)
2. Frontend calls API client methods (`frontend/lib/api.ts`) → `GET /api/agents`
3. Backend receives request in agents router (`backend/app/api/agents.py`)
4. Router dependency injects authenticated user and database session (`backend/app/core/deps.py`)
5. Endpoint queries Agent model from database via SQLAlchemy
6. Response serialized as JSON (AgentResponse schema) and returned to frontend
7. Frontend uses React Query to cache and manage state
8. Components re-render with agent data using Zustand stores for auth context

**Execution Tracking & Metrics Flow:**

1. External agents (maria-claude, maria-voz) call backend to log execution: `POST /api/executions`
2. Backend creates Execution record in database with token counts
3. Langfuse client (if configured) logs trace with observability data
4. Frontend periodically queries: `GET /api/executions/metrics/summary` and `GET /api/executions/metrics/realtime`
5. Dashboard components fetch and display metrics via React Query (`frontend/app/dashboard/page.tsx`)
6. Charts render historical token usage and agent costs

**Authentication & Authorization Flow:**

1. User submits login form → `api.login(email, password)` (`frontend/lib/api.ts`)
2. Backend receives: `POST /api/auth/login` (`backend/app/api/auth.py`)
3. Backend validates credentials, returns JWT access token if valid
4. Frontend stores token in Zustand auth store (`frontend/lib/auth.ts`) with persist middleware
5. Token auto-injected into Authorization header for all future requests (`frontend/lib/api.ts` line 37-39)
6. Backend validates token via `get_current_user` dependency on protected endpoints
7. RoleChecker verifies user role matches endpoint requirements (`backend/app/core/deps.py` lines 71-91)
8. Protected endpoints use type aliases: `AdminUser`, `OperatorUser` to enforce roles

**State Management:**

- **Frontend:** Zustand stores for auth state (token, user, loading, error) with localStorage persistence
- **Frontend:** React Query for server state (agents, executions, metrics) with automatic caching and refetching
- **Backend:** PostgreSQL for persistent state (users, agents, tools, executions)
- **Backend:** No session state (stateless API design)

## Key Abstractions

**Agent:**
- Purpose: Represents an AI agent (maria-claude, maria-voz, etc.) managed by PACO
- Examples: `backend/app/db/models.py` (Agent model), `backend/app/api/agents.py` (AgentResponse, AgentCreateRequest)
- Pattern: SQLAlchemy ORM model with YAML configuration support, PM2 process binding

**Execution:**
- Purpose: Tracks a single agent execution with token usage, duration, and costs
- Examples: `backend/app/db/models.py` (Execution model), `backend/app/api/executions.py` (ExecutionResponse, ExecutionDetailResponse)
- Pattern: Records linked to agents via agent_id, optionally linked to Langfuse traces

**MCP Server (Model Context Protocol):**
- Purpose: Registry of Model Context Protocol servers that agents can use for extended tools
- Examples: `backend/app/db/models.py` (McpServer model), `backend/app/api/tools.py`
- Pattern: Managed via creation/deletion endpoints, health check endpoints, tool sync from server

**User & Role:**
- Purpose: Authentication identity with role-based access control
- Examples: `backend/app/db/models.py` (User model with role field), `backend/app/core/deps.py` (RoleChecker, role-specific dependencies)
- Pattern: JWT token issued at login, role validated on protected endpoints

## Entry Points

**Backend Application:**
- Location: `backend/app/main.py`
- Triggers: uvicorn startup via `uvicorn app.main:app --reload --port 8000`
- Responsibilities: FastAPI app initialization, CORS middleware setup, lifespan handlers (health checks), router registration, exception handlers

**Frontend Application:**
- Location: `frontend/app/layout.tsx` (root layout) → `frontend/app/page.tsx` (home page)
- Triggers: Next.js dev server via `next dev -p 3006` or production build
- Responsibilities: App layout, provider setup (QueryClientProvider, auth store), page routing, metadata

**API Routes:**
- Auth: `backend/app/api/auth.py` → POST /api/auth/login, POST /api/auth/register, GET /api/auth/me
- Agents: `backend/app/api/agents.py` → GET/POST /api/agents, POST /api/agents/{id}/start|stop|restart|status
- Tools: `backend/app/api/tools.py` → GET/POST /api/tools/servers, POST /api/tools/servers/{id}/sync
- Executions: `backend/app/api/executions.py` → GET /api/executions, GET /api/executions/metrics/summary|realtime
- Users: `backend/app/api/users.py` → CRUD operations for user management
- Proxy: `backend/app/api/proxy.py` → Langfuse trace proxying

## Error Handling

**Strategy:** HTTPException for expected errors, global exception handler for uncaught errors

**Patterns:**

- **API Errors:** Raise `HTTPException(status_code=..., detail="message")` in endpoints (`backend/app/api/agents.py` line 13, throughout)
- **Validation:** Pydantic BaseModel validation auto-returns 422 Unprocessable Entity
- **Global Handler:** `@app.exception_handler(Exception)` catches unhandled errors and returns 500 (`backend/app/main.py` lines 140-149)
- **Frontend:** API client throws `ApiError` with status and detail fields (`frontend/lib/api.ts` lines 9-12, 47-54)
- **Frontend:** Components handle errors via React Query error states and display toast/alert UI
- **Database:** Async session lifecycle auto-handles rollback on exception (`backend/app/core/deps.py` lines 20-26)

## Cross-Cutting Concerns

**Logging:**
- Backend: Print statements to stdout in lifespan handlers (`backend/app/main.py` lines 23-33)
- Backend: Langfuse integration logs execution traces with observability data
- Frontend: No explicit logging; relies on browser console

**Validation:**
- Backend: Pydantic models validate all request bodies automatically (e.g., AgentCreateRequest, ExecutionResponse)
- Backend: Custom validators via RoleChecker for authorization
- Frontend: React hook form + validation libraries for form inputs

**Authentication:**
- Backend: JWT token-based via python-jose library (`backend/app/core/security.py`)
- Backend: HTTPBearer automatic extraction from Authorization header
- Backend: Token expiration set to 7 days by default (`backend/app/core/config.py` line 30)
- Frontend: Zustand store persists token to localStorage, rehydrates on page load (`frontend/lib/auth.ts` lines 105-117)
- Frontend: Token auto-attached to all API requests via ApiClient (`frontend/lib/api.ts` lines 37-39)

**Configuration:**
- Backend: Pydantic Settings loads from .env file with defaults (`backend/app/core/config.py`)
- Frontend: NEXT_PUBLIC_API_URL environment variable controls backend URL (`frontend/lib/api.ts` line 7)
- Both: Environment-specific configuration (dev, staging, production)

---

*Architecture analysis: 2026-02-03*
