"""
Integration tests for the Orchestrator FastAPI endpoints.

Tests /health, /v1/route, /v1/classify, /v1/agents, /v1/categories,
and their backward-compatible unversioned aliases.

All external services (LLM, DB, Redis, agents) are mocked.
Uses FastAPI TestClient for synchronous HTTP testing.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Build a test-friendly copy of the orchestrator app.
#
# The real app has a heavy lifespan (DB, Redis, tracing, memory, sweeps).
# We replace the lifespan with a no-op and patch the dependencies the
# endpoint handlers actually call.
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _noop_lifespan(app: FastAPI):
    yield


def _build_test_app():
    """
    Import orchestrator.main with all heavy deps already stubbed (by conftest)
    and replace lifespan + middleware so tests run fast.
    """
    # Patch the security middleware dispatch to be a passthrough
    from orchestrator.main import app as real_app

    # Replace lifespan to avoid DB/Redis/tracing startup
    real_app.router.lifespan_context = _noop_lifespan

    # Remove SecurityMiddleware (it needs real audit logger)
    real_app.user_middleware = [
        m for m in real_app.user_middleware
        if "SecurityMiddleware" not in str(m)
    ]

    return real_app


# Build once at module level
_app = _build_test_app()


# ---------------------------------------------------------------------------
# Mock the orchestrator.route() that /route and /v1/route call
# ---------------------------------------------------------------------------

def _mock_route_result(category="CEA", response_text="Test response"):
    return {
        "response": response_text,
        "category": category,
        "category_description": f"Description for {category}",
        "agent_id": "test-agent",
        "contract_number": "123456",
        "task_type": "consulta_saldo",
        "error": None,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """FastAPI TestClient with mocked orchestrator internals."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.route = AsyncMock(return_value=_mock_route_result())
    mock_orchestrator.get_health.return_value = {
        "status": "healthy",
        "service": "orchestrator",
        "agents": ["CEA", "TRA", "VEH"],
        "agent_count": 3,
    }

    mock_session_store = MagicMock()
    mock_session_store.get_or_create = AsyncMock(return_value=MagicMock(
        get_shared=MagicMock(return_value=[]),
        set_shared=MagicMock(),
        record_agent_visit=MagicMock(),
    ))
    mock_session_store.update = AsyncMock()

    with patch("orchestrator.main.get_orchestrator", return_value=mock_orchestrator), \
         patch("orchestrator.main.get_session_store", return_value=mock_session_store), \
         patch("orchestrator.main.get_agent_registry", return_value={
             "CEA": {"id": "water-cea", "name": "Agua CEA", "url": "http://localhost:8001", "description": "Agua"},
             "TRA": {"id": "transport-ameq", "name": "Transporte", "url": "http://localhost:8002", "description": "Transporte"},
             "VEH": {"id": "vehicles", "name": "Vehiculos", "url": "http://localhost:8004", "description": "Vehiculos"},
         }), \
         patch("orchestrator.main.settings") as mock_settings:
        mock_settings.rate_limit_route = "1000/minute"
        mock_settings.rate_limit_classify = "1000/minute"
        mock_settings.host = "0.0.0.0"
        mock_settings.port = 8000

        with TestClient(_app, raise_server_exceptions=False) as tc:
            tc._mock_orchestrator = mock_orchestrator
            yield tc


# ===================================================================
# GET /health
# ===================================================================

class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_fields(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "orchestrator"
        assert "agents" in data
        assert "agent_count" in data

    def test_health_has_rate_limits(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "rate_limits" in data


# ===================================================================
# GET /
# ===================================================================

class TestRootEndpoint:

    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_has_service_info(self, client):
        data = client.get("/").json()
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data


# ===================================================================
# POST /v1/classify and /classify
# ===================================================================

class TestClassifyEndpoint:
    """Test classification endpoints."""

    def test_v1_classify_keyword_match(self, client):
        resp = client.post("/v1/classify", json={"message": "tengo una fuga de agua"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "CEA"
        assert data["method"] == "keyword"
        assert "category_description" in data
        assert "confidence" in data

    def test_compat_classify_same_result(self, client):
        resp = client.post("/classify", json={"message": "tengo una fuga de agua"})
        assert resp.status_code == 200
        assert resp.json()["category"] == "CEA"

    def test_classify_with_context(self, client):
        resp = client.post("/v1/classify", json={
            "message": "tengo una fuga de agua",
            "context": "El usuario ya consulto su saldo.",
        })
        assert resp.status_code == 200

    def test_classify_vehicle(self, client):
        resp = client.post("/v1/classify", json={"message": "cuanto debo de placas y multas"})
        assert resp.status_code == 200
        assert resp.json()["category"] == "VEH"

    def test_classify_exit(self, client):
        resp = client.post("/v1/classify", json={"message": "gracias adios"})
        assert resp.status_code == 200
        assert resp.json()["category"] == "EXIT"

    def test_classify_empty_message_still_works(self, client):
        # An empty message should still return something (LLM fallback or ATC)
        resp = client.post("/v1/classify", json={"message": ""})
        assert resp.status_code == 200


# ===================================================================
# POST /v1/route and /route
# ===================================================================

class TestRouteEndpoint:
    """Test message routing endpoints."""

    def test_v1_route_returns_200(self, client):
        resp = client.post("/v1/route", json={"message": "quiero consultar mi agua"})
        assert resp.status_code == 200

    def test_v1_route_response_fields(self, client):
        resp = client.post("/v1/route", json={"message": "quiero consultar mi agua"})
        data = resp.json()
        assert "response" in data
        assert "category" in data
        assert "agent_id" in data

    def test_compat_route_same_result(self, client):
        resp = client.post("/route", json={"message": "quiero consultar mi agua"})
        assert resp.status_code == 200
        assert "response" in resp.json()

    def test_route_with_metadata(self, client):
        resp = client.post("/v1/route", json={
            "message": "quiero consultar mi agua",
            "conversation_id": "conv-001",
            "contact_id": "contact-001",
            "contract_number": "123456",
            "metadata": {"source": "whatsapp"},
        })
        assert resp.status_code == 200

    def test_route_passes_message_to_orchestrator(self, client):
        client.post("/v1/route", json={"message": "test message"})
        client._mock_orchestrator.route.assert_called_once()
        call_kwargs = client._mock_orchestrator.route.call_args
        assert call_kwargs.kwargs["message"] == "test message"


# ===================================================================
# GET /v1/agents and /agents
# ===================================================================

class TestAgentsEndpoint:
    """Test agent listing endpoints."""

    def test_v1_agents_returns_list(self, client):
        resp = client.get("/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_agent_has_required_fields(self, client):
        data = client.get("/v1/agents").json()
        for agent in data:
            assert "id" in agent
            assert "name" in agent
            assert "category_code" in agent
            assert "description" in agent
            assert "url" in agent

    def test_compat_agents_same_result(self, client):
        v1_data = client.get("/v1/agents").json()
        compat_data = client.get("/agents").json()
        assert len(v1_data) == len(compat_data)

    def test_get_agent_by_category(self, client):
        resp = client.get("/v1/agents/CEA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "water-cea"
        assert data["category_code"] == "CEA"

    def test_get_agent_case_insensitive(self, client):
        resp = client.get("/v1/agents/cea")
        assert resp.status_code == 200

    def test_get_agent_not_found(self, client):
        resp = client.get("/v1/agents/ZZZ")
        assert resp.status_code == 404


# ===================================================================
# GET /v1/categories and /categories
# ===================================================================

class TestCategoriesEndpoint:
    """Test categories listing endpoints."""

    def test_v1_categories_returns_dict(self, client):
        resp = client.get("/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "CEA" in data

    def test_category_has_fields(self, client):
        data = client.get("/v1/categories").json()
        for code, info in data.items():
            assert "description" in info
            assert "agent" in info
            assert "keywords" in info

    def test_compat_categories(self, client):
        resp = client.get("/categories")
        assert resp.status_code == 200
        assert "CEA" in resp.json()

    def test_all_13_categories_present(self, client):
        data = client.get("/v1/categories").json()
        expected = {"CEA", "TRA", "EDU", "VEH", "PSI", "IQM", "CUL", "RPP", "LAB", "VIV", "APP", "SOC", "ATC"}
        assert expected == set(data.keys())


# ===================================================================
# POST /v1/register and /v1/heartbeat
# ===================================================================

class TestRegistrationEndpoints:
    """Test agent registration and heartbeat endpoints."""

    def test_register_agent(self, client):
        with patch("orchestrator.main.registry_register_agent", new_callable=AsyncMock, return_value=True):
            resp = client.post("/v1/register", json={
                "agent_id": "test-agent",
                "name": "Test Agent",
                "category_code": "CEA",
                "endpoint": "http://localhost:9999",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert data["agent_id"] == "test-agent"

    def test_register_agent_db_failure(self, client):
        with patch("orchestrator.main.registry_register_agent", new_callable=AsyncMock, return_value=False):
            resp = client.post("/v1/register", json={
                "agent_id": "test-agent",
                "name": "Test Agent",
                "category_code": "CEA",
                "endpoint": "http://localhost:9999",
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "failed"

    def test_heartbeat(self, client):
        with patch("orchestrator.main.registry_heartbeat", new_callable=AsyncMock, return_value=True):
            resp = client.post("/v1/heartbeat", json={"agent_id": "test-agent"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_compat_register(self, client):
        with patch("orchestrator.main.registry_register_agent", new_callable=AsyncMock, return_value=True):
            resp = client.post("/register", json={
                "agent_id": "test-agent",
                "name": "Test Agent",
                "category_code": "CEA",
                "endpoint": "http://localhost:9999",
            })
        assert resp.status_code == 200

    def test_compat_heartbeat(self, client):
        with patch("orchestrator.main.registry_heartbeat", new_callable=AsyncMock, return_value=True):
            resp = client.post("/heartbeat", json={"agent_id": "test-agent"})
        assert resp.status_code == 200
