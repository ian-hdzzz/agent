# Coding Conventions

**Analysis Date:** 2026-02-03

## Naming Patterns

**Files:**
- TypeScript/React: PascalCase for components (`AgentCard.tsx`, `Header.tsx`), camelCase for utilities (`api.ts`, `auth.ts`)
- Python: snake_case for modules and files (`agent_manager.py`, `config.py`, `session.py`)
- Page routes: kebab-case in directory structure (`/app/dashboard`, `/app/auth/login`)

**Functions:**
- TypeScript: camelCase for all functions (`formatDate`, `useQuery`, `getStatusColor`)
- Python: snake_case for functions and methods (`get_settings`, `sync_agents_from_yaml`, `check_health`)
- React hooks: camelCase with `use` prefix (`useAuth`, `useIsAdmin`, `useQuery`)

**Variables:**
- TypeScript: camelCase (`agents`, `isLoading`, `errorMessage`)
- Python: snake_case (`agents_path`, `pm2_status`, `health_result`)

**Types & Interfaces:**
- TypeScript: PascalCase for interface names (`AuthState`, `Agent`, `AgentCardProps`)
- Python: PascalCase for class names (`Settings`, `User`, `AgentManager`)

## Code Style

**Formatting:**
- Prettier configured for TypeScript/JavaScript (no explicit config file, using defaults)
- Black formatter for Python (as dependency in `requirements.txt`)
- Trailing commas in multiline structures
- 80-100 character line length observed in practice

**Linting:**
- ESLint with `next/core-web-vitals` config for frontend (from `package.json`)
- Ruff for Python (from `requirements.txt`)
- No explicit `.eslintrc` or `ruff.toml` - using framework defaults

## Import Organization

**Order (TypeScript/React):**
1. External React/Next libraries (`"react"`, `"next/navigation"`)
2. Third-party packages (`@tanstack/react-query`, `lucide-react`, `zustand`)
3. Internal aliases (`@/lib/...`, `@/components/...`)
4. Relative imports (same-level files)

**Example from `app/dashboard/page.tsx`:**
```typescript
import { useQuery } from "@tanstack/react-query";
import { Bot, Zap, DollarSign } from "lucide-react";
import { Header } from "@/components/ui/Header";
import { api } from "@/lib/api";
```

**Order (Python):**
1. Standard library (`datetime`, `pathlib`, `typing`)
2. Third-party packages (`fastapi`, `sqlalchemy`, `yaml`)
3. Internal modules (`from app.api import`, `from app.db import`)

**Example from `app/api/agents.py`:**
```python
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Agent
```

**Path Aliases:**
- Frontend: `@/*` maps to root directory (from `tsconfig.json`)
- Example: `@/lib/api` resolves to `lib/api.ts`

## Error Handling

**TypeScript/React:**
- Try-catch blocks in async functions
- Error objects typed with `ApiError` interface
- Propagate errors to UI with error state in stores
- Example from `lib/auth.ts`:
```typescript
catch (err: any) {
  set({
    error: err.detail || "Login failed",
    isLoading: false,
  });
  throw err;
}
```

**Python/FastAPI:**
- HTTPException for API errors with proper status codes
- Global exception handler in `app/main.py`
- Return JSONResponse with `detail` and `type` fields
- Example from `app/api/agents.py`:
```python
if not agent:
  raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f"Agent {agent_id} not found",
  )
```

## Logging

**Framework:** `console.log` / `print` statements (no structured logging library)

**Patterns:**
- Frontend: Minimal logging, mainly for development
- Python: Print statements for startup info and errors
- Example from `app/main.py`:
```python
print(f"Starting {settings.app_name} v{settings.app_version}")
print("Langfuse connection: OK")
```

## Comments

**When to Comment:**
- Document function purposes with docstrings
- Clarify non-obvious logic
- Add section headers in complex files (see `app/main.py` with `=== Health Check ===` sections)

**JSDoc/TSDoc:**
- Block comments for module-level documentation
- Example from `lib/api.ts`:
```typescript
/**
 * PACO API Client
 *
 * Handles all API requests to the PACO backend.
 */
```

**Python Docstrings:**
- Triple-quoted strings for functions and classes
- Example from `app/main.py`:
```python
"""Application lifespan handler."""
```

## Function Design

**Size:**
- Keep functions focused and under 50 lines when practical
- Larger functions broken into helper methods
- Example: `AgentManager` has separate `_sync_agent_config()` helper

**Parameters:**
- Max 4-5 parameters before considering object destructuring
- Use interfaces/types for multiple related params
- Example from `AgentCardProps`:
```typescript
interface AgentCardProps {
  agent: Agent;
  onStart?: () => void;
  onStop?: () => void;
  onRestart?: () => void;
  onClick?: () => void;
  isLoading?: boolean;
}
```

**Return Values:**
- Use explicit return types in TypeScript
- Python functions use type hints
- Pydantic models for API responses

## Module Design

**Exports:**
- Default export for page components (`export default function DashboardPage()`)
- Named exports for utilities and components
- Single API instance export: `export const api = new ApiClient(API_URL)`

**Barrel Files:**
- Not extensively used, imports done directly from files
- Example: `from app.core.deps import AdminUser, DbSession, OperatorUser`

**File Organization:**
- One primary class/component per file
- Related types defined in same file (e.g., `AgentCardProps` in `AgentCard.tsx`)
- Utilities grouped by domain (`lib/api.ts`, `lib/auth.ts`, `lib/utils.ts`)

## React-Specific Patterns

**Client Components:**
- Explicit `"use client"` directive at top of files that need client features
- Applies to any component using hooks (useState, useQuery, useAuth)

**State Management:**
- Zustand for authentication (`useAuth` in `lib/auth.ts`)
- TanStack React Query for server state and data fetching
- QueryClient configured in `app/providers.tsx` with 1-minute staleTime default

**Component Structure:**
- Functional components with hooks
- Props passed via interfaces (TypeScript)
- No class components observed

## Python-Specific Patterns

**Async/Await:**
- All database operations are async-first (SQLAlchemy AsyncSession)
- Functions marked with `async def`
- Proper `await` usage for I/O operations

**Type Hints:**
- Comprehensive type hints on all functions
- Use `Optional[T]` for nullable types
- Use `List[T]`, `Dict[str, Any]` for collections

**Model Declarations:**
- SQLAlchemy 2.0+ with `Mapped` type annotations (modern style)
- All models inherit from `Base` declarative class
- UUID primary keys with `PG_UUID(as_uuid=True)`

---

*Convention analysis: 2026-02-03*
