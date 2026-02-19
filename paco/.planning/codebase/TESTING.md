# Testing Patterns

**Analysis Date:** 2026-02-03

## Test Framework

**Runner:**
- **Python:** pytest >= 7.0.0 (from `requirements.txt`)
- **JavaScript/TypeScript:** Not configured (no test runner detected)

**Python Config:**
- Location: Not explicitly configured (using pytest defaults)
- Command: `pytest` (inferred from dependencies)

**Assertion Library:**
- Python: pytest assertions (built-in with pytest)

**Run Commands:**

```bash
# Python tests (backend)
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest --cov                    # With coverage
pytest -k test_name             # Run specific test
pytest app/api/test_agents.py   # Run tests in specific file

# JavaScript/TypeScript (frontend)
# Not yet configured - no test runner dependency detected
```

## Test File Organization

**Python Location:**
- Observed structure suggests tests in same directories as code or dedicated `tests/` folder
- Not yet implemented in codebase (no test files found in `backend/app/`)
- Recommended location: `backend/tests/` or alongside source in `backend/app/`

**Naming:**
- Python: `test_*.py` or `*_test.py` pattern
- TypeScript: Not configured

**Structure:**
```
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   └── services/
└── tests/                      # Recommended
    ├── api/
    │   ├── test_agents.py
    │   ├── test_auth.py
    │   └── test_executions.py
    ├── services/
    │   ├── test_agent_manager.py
    │   └── test_pm2_client.py
    └── conftest.py             # Shared fixtures
```

## Test Structure

**Python Test Suite Pattern:**

Based on project structure and framework (pytest + FastAPI + SQLAlchemy):

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def db_session() -> AsyncSession:
    """Create async database session for testing."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)
    async with async_session() as session:
        yield session

@pytest.fixture
def client(db_session):
    """FastAPI test client."""
    return TestClient(app)

class TestAgents:
    """Test agent endpoints."""

    async def test_list_agents(self, client, db_session):
        """Test retrieving agent list."""
        response = client.get("/api/agents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_create_agent(self, client, db_session):
        """Test creating new agent."""
        data = {
            "name": "test-agent",
            "type": "test",
            "config_yaml": "name: test\ntype: test"
        }
        response = client.post("/api/agents", json=data)
        assert response.status_code == 201
        assert response.json()["name"] == "test-agent"
```

**Patterns:**
- Use pytest fixtures for setup/teardown
- Async fixtures with `@pytest.fixture` for async operations
- Test classes group related tests
- Clear test names: `test_<action>_<expected_outcome>`

## Mocking

**Framework:** unittest.mock (Python standard library)

**Patterns:**
```python
from unittest.mock import AsyncMock, patch, MagicMock

async def test_agent_health_check():
    """Mock PM2 client for health checks."""
    with patch('app.services.agent_manager.PM2Client') as mock_pm2:
        mock_pm2.return_value.status = AsyncMock(
            return_value={"pm2_env": {"status": "online"}}
        )

        manager = AgentManager()
        health = await manager.check_health(agent)
        assert health["overall_status"] == "healthy"

async def test_http_health_timeout():
    """Mock httpx for timeout scenarios."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = TimeoutError()

        health_result = await manager.check_health(agent)
        assert health_result["http_health"]["healthy"] is False
```

**What to Mock:**
- External service calls (PM2, HTTP endpoints)
- Database operations in isolation tests
- Environment-dependent functionality
- Time-based operations (use `freezegun` for time mocking)

**What NOT to Mock:**
- Database models (test with in-memory SQLite or test database)
- Core business logic (test actual behavior)
- API response parsing (test real responses)

## Fixtures and Factories

**Test Data Pattern:**

```python
# backend/tests/conftest.py
import pytest
from app.db.models import User, Agent
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        name="Test User",
        role="admin"
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def test_agent(db_session: AsyncSession, test_user: User) -> Agent:
    """Create test agent."""
    agent = Agent(
        name="test-agent",
        display_name="Test Agent",
        type="test",
        version="1.0.0",
        config_yaml="name: test\ntype: test",
        status="stopped",
        pm2_name="test-agent"
    )
    db_session.add(agent)
    await db_session.commit()
    return agent

@pytest.fixture
async def authenticated_client(client, test_user):
    """Client with authentication token."""
    token = create_access_token(test_user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

**Location:**
- Central fixtures in `backend/tests/conftest.py`
- Domain-specific fixtures in `backend/tests/<domain>/conftest.py`
- Factory functions for complex object creation

## Coverage

**Requirements:** Not enforced (no `.coveragerc` or pytest config found)

**View Coverage:**
```bash
pytest --cov=app --cov-report=html
# Opens coverage report in htmlcov/index.html

pytest --cov=app --cov-report=term-missing
# Shows coverage in terminal with missing lines
```

**Current State:**
- No test files present yet
- Recommended target: 80%+ for core business logic
- 100% for critical paths (authentication, data persistence)

## Test Types

**Unit Tests:**
- Scope: Individual functions/methods in isolation
- Approach: Mock external dependencies
- Examples:
  - `test_format_date()` - utility function
  - `test_agent_status_calculation()` - business logic
  - `test_validate_config_yaml()` - input validation

**Integration Tests:**
- Scope: Multiple components working together
- Approach: Use real database, mock external APIs
- Examples:
  - `test_create_agent_and_fetch()` - create then retrieve from DB
  - `test_agent_start_workflow()` - start agent, check status updates
  - `test_execution_logging_end_to_end()` - full execution flow

**E2E Tests:**
- Framework: Not yet implemented
- Recommendation: Use `pytest-asyncio` + `httpx.AsyncClient` for async endpoint testing
- Would cover: Full API workflows with real database

## Common Patterns

**Async Testing:**

```python
import pytest
from pytest_asyncio import fixture

@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    result = await async_function()
    assert result == expected_value

@fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

**Database Testing:**

```python
@pytest.fixture
async def test_db():
    """Create fresh test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

**Error Testing:**

```python
@pytest.mark.asyncio
async def test_invalid_agent_raises_404():
    """Test 404 error on missing agent."""
    response = client.get("/api/agents/invalid-uuid")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_duplicate_agent_raises_conflict():
    """Test 409 conflict on duplicate name."""
    client.post("/api/agents", json=agent_data)
    response = client.post("/api/agents", json=agent_data)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()
```

## Frontend Testing Notes

**Current Status:** No test infrastructure configured

**Recommended Setup for TypeScript/React:**
```bash
# Install dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom

# Test file location
frontend/__tests__/
├── components/
│   ├── AgentCard.test.tsx
│   └── Header.test.tsx
├── lib/
│   ├── api.test.ts
│   └── auth.test.ts
└── utils.test.ts

# Run tests
npm run test
npm run test:coverage
```

---

*Testing analysis: 2026-02-03*
