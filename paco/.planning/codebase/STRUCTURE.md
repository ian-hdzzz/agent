# Codebase Structure

**Analysis Date:** 2026-02-03

## Directory Layout

```
paco/
├── backend/                     # FastAPI backend - Agent control plane
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app initialization, routers, health checks
│   │   ├── api/                # REST endpoint routers
│   │   │   ├── __init__.py
│   │   │   ├── agents.py       # Agent CRUD and lifecycle control
│   │   │   ├── auth.py         # Authentication (login, register)
│   │   │   ├── executions.py   # Execution logs and metrics
│   │   │   ├── proxy.py        # Langfuse trace proxying
│   │   │   ├── tools.py        # MCP server and tool management
│   │   │   └── users.py        # User management (admin only)
│   │   ├── core/               # Configuration and infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── config.py       # Pydantic Settings (env vars, defaults)
│   │   │   ├── deps.py         # FastAPI dependency injection (auth, db)
│   │   │   └── security.py     # JWT encoding/decoding
│   │   ├── db/                 # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── models.py       # SQLAlchemy ORM models
│   │   │   └── session.py      # Async engine and session factory
│   │   └── services/           # Business logic services
│   │       ├── __init__.py
│   │       ├── agent_manager.py # Agent lifecycle (YAML sync, health, PM2)
│   │       ├── langfuse_client.py # Observability client
│   │       └── pm2_client.py   # PM2 process control integration
│   ├── alembic/               # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/          # Migration files
│   ├── requirements.txt       # Python dependencies
│   └── venv/                  # Virtual environment (generated)
│
├── frontend/                   # Next.js frontend - Control plane UI
│   ├── app/                   # Next.js app directory (file-based routing)
│   │   ├── layout.tsx         # Root layout wrapper
│   │   ├── page.tsx           # Home page
│   │   ├── providers.tsx      # React Query and context providers
│   │   ├── auth/              # Authentication pages
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── register/
│   │   │       └── page.tsx
│   │   ├── dashboard/         # Main control plane dashboard
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx       # Agent overview, metrics
│   │   ├── agents/            # Agent management
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx       # Agent list, CRUD
│   │   ├── tools/             # Tool/MCP server management
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx       # Server list, tool sync
│   │   ├── executions/        # Execution log viewer
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx       # Execution history, traces
│   │   ├── users/             # User management (admin)
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx       # User list, CRUD
│   │   └── settings/          # App settings
│   │       ├── layout.tsx
│   │       └── page.tsx       # Configuration options
│   ├── components/            # Reusable React components
│   │   ├── ui/                # Generic UI components
│   │   │   ├── Header.tsx     # App header/navbar
│   │   │   └── Sidebar.tsx    # Navigation sidebar
│   │   ├── agents/            # Agent-specific components
│   │   │   └── AgentCard.tsx  # Agent display card
│   │   └── charts/            # Chart components
│   │       ├── TokenUsageChart.tsx # Token usage visualization
│   │       └── AgentCostChart.tsx  # Agent cost comparison
│   ├── lib/                   # Utilities and clients
│   │   ├── api.ts             # API client singleton (fetch wrapper)
│   │   ├── auth.ts            # Zustand auth store
│   │   └── utils.ts           # Formatting, helpers
│   ├── styles/                # Global CSS
│   │   └── globals.css        # Tailwind imports
│   ├── package.json           # Node dependencies
│   ├── tsconfig.json          # TypeScript config
│   ├── next.config.js         # Next.js config
│   ├── tailwind.config.ts     # Tailwind CSS config
│   ├── postcss.config.js      # PostCSS config
│   └── Dockerfile             # Container build
│
├── db/                        # Database initialization
│   └── init.sql              # PostgreSQL schema, extensions, default data
│
├── docker-compose.yml         # Infrastructure services (postgres, redis, langfuse)
├── .env.example              # Environment variables template
├── .env                      # Environment variables (git-ignored)
├── dev.sh                    # Development startup script
└── README.md                 # Project documentation
```

## Directory Purposes

**backend/app/api/:**
- Purpose: FastAPI router modules, one per domain (agents, auth, tools, executions, users, proxy)
- Contains: Pydantic request/response schemas, route handlers, HTTP method declarations
- Key files: `agents.py` (156 KB), `tools.py` (148 KB), `executions.py` (128 KB)
- Pattern: Each file imports `router = APIRouter(prefix="/api/...", tags=[...])` then registers endpoints

**backend/app/core/:**
- Purpose: Cross-cutting concerns: configuration loading, JWT security, dependency injection
- Contains: Settings singleton, security utilities, FastAPI dependency functions
- Key files: `config.py` (Pydantic Settings from .env), `deps.py` (auth + db dependencies), `security.py` (JWT)
- Pattern: Settings cached via `@lru_cache()`, dependencies use type annotations for FastAPI injection

**backend/app/db/:**
- Purpose: Database layer - ORM models and session management
- Contains: SQLAlchemy declarative models (User, Agent, Tool, MCP Server, Execution, ApiKey, ToolCall)
- Key files: `models.py` (272+ lines), `session.py` (creates async engine and session maker)
- Pattern: Async-first via `create_async_engine()`, NullPool for async compatibility

**backend/app/services/:**
- Purpose: Business logic services not directly tied to HTTP requests
- Contains: Agent lifecycle management, PM2 integration, Langfuse observability
- Key files: `agent_manager.py` (YAML sync, health checks), `pm2_client.py`, `langfuse_client.py`
- Pattern: Imported and used by API routers, handle async operations

**frontend/app/:**
- Purpose: Next.js file-based routing - each folder is a route, `page.tsx` is the page component
- Contains: Layout wrappers and page components (TSX)
- Structure: `[feature]/page.tsx` and `[feature]/layout.tsx` files
- Pattern: Uses React hooks (useQuery, custom hooks), connects to backend via `frontend/lib/api.ts`

**frontend/components/:**
- Purpose: Reusable React components organized by domain
- Contains: UI primitives (Header, Sidebar), domain-specific (AgentCard), visualizations (Charts)
- Key files: `ui/Header.tsx` (navigation), `agents/AgentCard.tsx` (agent display), `charts/*.tsx` (Recharts)
- Pattern: Export default components, may use props for configuration

**frontend/lib/:**
- Purpose: Shared TypeScript utilities, API client, state management
- Contains: Fetch wrapper with auth, Zustand store for auth state, formatting helpers
- Key files: `api.ts` (API client singleton, 456 lines), `auth.ts` (Zustand store), `utils.ts`
- Pattern: `api.ts` is ApiClient class with singleton export, `auth.ts` is create()(persist(...)) store

## Key File Locations

**Entry Points:**
- Backend: `backend/app/main.py` - FastAPI app definition, router registration
- Frontend: `frontend/app/layout.tsx` - Root layout
- Frontend: `frontend/app/page.tsx` - Home page redirect
- Both: Docker containers started via `docker-compose.yml`

**Configuration:**
- Backend: `backend/app/core/config.py` - Settings class loads from `.env`
- Frontend: `frontend/lib/api.ts` line 7 - `NEXT_PUBLIC_API_URL` controls backend URL
- Database: `db/init.sql` - PostgreSQL schema
- Compose: `docker-compose.yml` - Service definitions (postgres, redis, langfuse)

**Core Logic:**
- Agent Management: `backend/app/api/agents.py` (routers) + `backend/app/services/agent_manager.py` (logic)
- Execution Tracking: `backend/app/api/executions.py` (routers) + `backend/app/db/models.py` (Execution model)
- Authentication: `backend/app/api/auth.py` (routers) + `backend/app/core/security.py` (JWT) + `frontend/lib/auth.ts` (Zustand)
- MCP Tools: `backend/app/api/tools.py` (routers) + `backend/app/db/models.py` (McpServer, Tool models)

**Testing:**
- No test files found - testing infrastructure not yet implemented
- Test configuration: `pytest` in `requirements.txt` but no test suite present

## Naming Conventions

**Files:**
- Python: lowercase_with_underscores.py (e.g., `agent_manager.py`, `config.py`)
- TypeScript: PascalCase for components (e.g., `AgentCard.tsx`, `Header.tsx`), lowercase for utilities (e.g., `api.ts`, `auth.ts`)
- Directories: lowercase for packages (`api/`, `core/`, `services/`), PascalCase for component groups (`agents/`, `charts/`)
- Database migrations: Alembic default format (e.g., `001_initial.py`)

**Functions:**
- Python: `snake_case` (e.g., `get_agents()`, `sync_from_yaml()`, `health_check()`)
- TypeScript: `camelCase` (e.g., `getAgents()`, `login()`, `formatCost()`)

**Variables:**
- Python: `snake_case` for all variables, constants, parameters
- TypeScript: `camelCase` for variables, `UPPER_SNAKE_CASE` for constants (e.g., `API_URL`)

**Types:**
- Python: PascalCase for Pydantic models and SQLAlchemy models (e.g., `AgentResponse`, `ExecutionResponse`, `Agent`, `Tool`)
- TypeScript: PascalCase for interfaces and types (e.g., `User`, `Agent`, `ApiError`), exported from `frontend/lib/api.ts`

## Where to Add New Code

**New Backend Endpoint:**
1. Create request/response Pydantic models in the appropriate `backend/app/api/{feature}.py` file
2. Add router function decorated with `@router.get()`, `@router.post()`, etc.
3. Use type annotations for dependency injection: `DbSession`, `CurrentUser`, `AdminUser`, etc. from `backend/app/core/deps.py`
4. Query database via SQLAlchemy async queries on injected `session` parameter
5. Return response model instance or raise `HTTPException` for errors
6. Router is auto-registered in `backend/app/main.py` via `app.include_router()`

**New Frontend Page:**
1. Create directory under `frontend/app/[feature-name]/`
2. Add `page.tsx` with default export component
3. Optionally add `layout.tsx` for shared structure within the feature
4. Use `"use client"` at top for client-side components
5. Import hooks: `useQuery` from `@tanstack/react-query`, custom hooks from `frontend/lib/api.ts`
6. Use `api` singleton to call backend endpoints
7. Route automatically available at `http://localhost:3006/[feature-name]`

**New Frontend Component:**
1. Create file under `frontend/components/[category]/ComponentName.tsx`
2. Export default React component
3. Define interface for props at top of file
4. Use Tailwind classes for styling (dark mode, no CSS files)
5. Import icons from `lucide-react`
6. Import UI primitives from sibling files if needed

**New Service:**
1. Create file under `backend/app/services/[service_name].py`
2. Define class that encapsulates business logic
3. Use async/await for I/O operations (database, HTTP calls)
4. Instantiate singleton in api router files, pass injected `session` parameter
5. Raise custom exceptions or return success/failure tuples

**New Database Model:**
1. Add SQLAlchemy model class to `backend/app/db/models.py`
2. Use `mapped_column`, `Mapped`, and relationship types from SQLAlchemy 2.0 style
3. Create database migration: `alembic revision --autogenerate -m "Add new table"`
4. Update `db/init.sql` to reflect schema for fresh database init

## Special Directories

**backend/alembic/:**
- Purpose: Database schema versioning and migrations
- Generated: Yes (Alembic manages)
- Committed: Yes (versions/ subdirectory tracked)
- Usage: `alembic upgrade head` to apply pending migrations

**frontend/.next/:**
- Purpose: Next.js build output and type generation
- Generated: Yes (auto-generated by `next build`)
- Committed: No (in .gitignore)
- Usage: Auto-generated, should not be edited

**frontend/node_modules/:**
- Purpose: Installed NPM dependencies
- Generated: Yes (via `npm install`)
- Committed: No (in .gitignore)
- Usage: `npm install` to populate

**backend/venv/:**
- Purpose: Python virtual environment
- Generated: Yes (via `python -m venv venv`)
- Committed: No (in .gitignore)
- Usage: `source venv/bin/activate` to use

**db/:**
- Purpose: Database initialization and schema definition
- Generated: No (hand-written)
- Committed: Yes
- Usage: PostgreSQL reads init.sql on container startup via docker-compose

---

*Structure analysis: 2026-02-03*
