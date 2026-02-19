# Phase 4 Research: Persistence

## Discovery Level: 0 (Skip)

All work follows established codebase patterns. No new external dependencies needed.

## Existing Infrastructure Analysis

### Backend Patterns (Level 0 - Use Existing)

**Database:**
- PostgreSQL with async SQLAlchemy (asyncpg)
- Existing `Flow` model in `backend/app/db/models.py`
- Alembic migrations at `backend/alembic/versions/` (currently empty - using direct table creation)
- UUID primary keys with `server_default=func.uuid_generate_v4()`

**API Patterns (from agents.py):**
- Pydantic models for Request/Response
- CRUD pattern: list, get by ID, create, update, delete
- DbSession, AdminUser, OperatorUser dependencies
- HTTPException for errors (404, 409 conflict, 400 validation)
- Response uses `from_attributes = True` for ORM mapping

**Auth:**
- JWT with role-based access (admin, operator, viewer)
- `AdminUser` for write operations, `OperatorUser` for lifecycle control
- Auth store at `frontend/lib/auth.ts` (Zustand with persist)

### Frontend Patterns (Level 0 - Use Existing)

**API Client:**
- `frontend/lib/api.ts` with typed methods
- Token set via `api.setToken()`
- Generic `request<T>()` method handles all calls

**Builder Store:**
- `syncToJson()` - returns `Component<TeamConfig> | null` (current canvas state as JSON)
- `loadFromJson()` - loads JSON into canvas state
- Already handles dirty state (`currentHistoryIndex > 0`)

**Builder UI:**
- Download button already exports JSON via `syncToJson()`
- Save button calls `handleSave()` which uses `onChange` prop
- `TeamBuilderProps.team` has `id`, `component` structure

### Existing Flow Model (Partially Useful)

```python
class Flow(Base):
    __tablename__ = "flows"
    id: UUID
    name: str (unique)
    description: Optional[str]
    config_yaml: str  # Will store JSON, not YAML
    is_enabled: bool
    created_at, updated_at
    created_by: Optional[UUID] -> users.id
```

**Assessment:** Model has the right shape. `config_yaml` column name is misleading but stores text - we can store JSON there. No schema migration needed.

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Reuse `Flow` model | Already has name, description, config storage, created_by |
| Store JSON in `config_yaml` | Column is Text type, works fine for JSON |
| Create `workflows` router (not flows) | "Workflow" aligns with builder terminology |
| Auto-save interval: 30s | Balance between data safety and API load |
| Export uses `syncToJson()` directly | Already produces valid JSON structure |

## API Design

```
GET    /api/workflows          - List user's workflows
GET    /api/workflows/{id}     - Get workflow by ID
POST   /api/workflows          - Create new workflow
PUT    /api/workflows/{id}     - Update workflow (manual save + auto-save)
DELETE /api/workflows/{id}     - Delete workflow
```

## No External Services

- No new npm packages needed
- No new Python packages needed
- No external API integrations
- All work uses existing patterns

---
*Research completed: 2026-02-03*
