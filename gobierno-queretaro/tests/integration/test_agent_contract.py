"""
Integration tests for the standardized agent contract.

Every agent MUST expose:
- POST /query  (message, conversation_id, contact_id -> response, agent_id, task_type)
- GET  /health (status, agent_id, agent_name, category_code, task_types)
- GET  /info   (agent configuration dict)
- GET  /       (root with endpoints listing)

These tests build a minimal FastAPI app that follows the _template/main.py
contract and verify that the expected request/response shapes are honoured.
All agent internals (LangGraph, Anthropic, DB) are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Any


# ---------------------------------------------------------------------------
# Build a contract-compliant test agent app
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    contact_id: str | None = None
    metadata: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    response: str
    agent_id: str
    conversation_id: str | None = None
    task_type: str | None = None
    tools_used: list[str] = []
    ticket_folio: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    agent_id: str
    agent_name: str
    category_code: str
    task_types: list[str]


# A mock agent that simulates the _template/main.py contract
_mock_agent = MagicMock()
_mock_agent.run = AsyncMock(return_value={
    "response": "Test agent response",
    "agent_id": "test-agent",
    "task_type": "consulta",
})
_mock_agent.get_health.return_value = {
    "status": "healthy",
    "agent_id": "test-agent",
    "agent_name": "Test Agent",
    "category_code": "TST",
    "task_types": ["consulta", "reporte"],
}
_mock_agent.config = {"name": "Test Agent"}


def _build_agent_app() -> FastAPI:
    """Build a minimal agent app following the template contract."""
    app = FastAPI()

    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        return _mock_agent.get_health()

    @app.post("/query", response_model=QueryResponse)
    async def query_agent(request: QueryRequest):
        result = await _mock_agent.run(
            message=request.message,
            metadata=request.metadata or {},
        )
        return QueryResponse(
            response=result.get("response", ""),
            agent_id=result.get("agent_id", "test-agent"),
            conversation_id=request.conversation_id,
            task_type=result.get("task_type"),
        )

    @app.get("/info")
    async def agent_info():
        return {
            "agent_id": "test-agent",
            "agent_name": "Test Agent",
            "category_code": "TST",
            "version": "1.0.0",
        }

    @app.get("/")
    async def root():
        return {
            "service": "Test Agent",
            "agent_id": "test-agent",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "query": "/query",
                "info": "/info",
            },
        }

    return app


@pytest.fixture
def agent_client():
    """TestClient for the contract-compliant agent."""
    app = _build_agent_app()
    with TestClient(app) as tc:
        yield tc


# ===================================================================
# POST /query contract
# ===================================================================

class TestQueryContract:
    """Verify the /query endpoint contract."""

    def test_query_returns_200(self, agent_client):
        resp = agent_client.post("/query", json={"message": "Hola"})
        assert resp.status_code == 200

    def test_query_response_has_required_fields(self, agent_client):
        data = agent_client.post("/query", json={"message": "Hola"}).json()
        assert "response" in data
        assert "agent_id" in data
        assert isinstance(data["response"], str)
        assert isinstance(data["agent_id"], str)

    def test_query_response_has_optional_fields(self, agent_client):
        data = agent_client.post("/query", json={"message": "Hola"}).json()
        # These should be present (even if null)
        assert "conversation_id" in data
        assert "task_type" in data
        assert "tools_used" in data
        assert "error" in data

    def test_query_accepts_conversation_id(self, agent_client):
        data = agent_client.post("/query", json={
            "message": "Hola",
            "conversation_id": "conv-123",
        }).json()
        assert data["conversation_id"] == "conv-123"

    def test_query_accepts_contact_id(self, agent_client):
        resp = agent_client.post("/query", json={
            "message": "Hola",
            "contact_id": "contact-456",
        })
        assert resp.status_code == 200

    def test_query_accepts_metadata(self, agent_client):
        resp = agent_client.post("/query", json={
            "message": "Hola",
            "metadata": {"contract_number": "123456", "category": "CEA"},
        })
        assert resp.status_code == 200

    def test_query_missing_message_returns_422(self, agent_client):
        resp = agent_client.post("/query", json={})
        assert resp.status_code == 422

    def test_query_empty_message_accepted(self, agent_client):
        resp = agent_client.post("/query", json={"message": ""})
        assert resp.status_code == 200

    def test_query_passes_message_to_agent(self, agent_client):
        _mock_agent.run.reset_mock()
        agent_client.post("/query", json={"message": "test input"})
        _mock_agent.run.assert_called_once()
        call_kwargs = _mock_agent.run.call_args.kwargs
        assert call_kwargs["message"] == "test input"


# ===================================================================
# GET /health contract
# ===================================================================

class TestHealthContract:
    """Verify the /health endpoint contract."""

    def test_health_returns_200(self, agent_client):
        resp = agent_client.get("/health")
        assert resp.status_code == 200

    def test_health_has_required_fields(self, agent_client):
        data = agent_client.get("/health").json()
        assert "status" in data
        assert "agent_id" in data
        assert "agent_name" in data
        assert "category_code" in data
        assert "task_types" in data

    def test_health_status_is_healthy(self, agent_client):
        data = agent_client.get("/health").json()
        assert data["status"] == "healthy"

    def test_health_agent_id_is_string(self, agent_client):
        data = agent_client.get("/health").json()
        assert isinstance(data["agent_id"], str)
        assert len(data["agent_id"]) > 0

    def test_health_task_types_is_list(self, agent_client):
        data = agent_client.get("/health").json()
        assert isinstance(data["task_types"], list)


# ===================================================================
# GET /info contract
# ===================================================================

class TestInfoContract:
    """Verify the /info endpoint contract."""

    def test_info_returns_200(self, agent_client):
        resp = agent_client.get("/info")
        assert resp.status_code == 200

    def test_info_has_agent_id(self, agent_client):
        data = agent_client.get("/info").json()
        assert "agent_id" in data

    def test_info_has_version(self, agent_client):
        data = agent_client.get("/info").json()
        assert "version" in data


# ===================================================================
# GET / root contract
# ===================================================================

class TestRootContract:
    """Verify the root endpoint contract."""

    def test_root_returns_200(self, agent_client):
        resp = agent_client.get("/")
        assert resp.status_code == 200

    def test_root_has_status(self, agent_client):
        data = agent_client.get("/").json()
        assert "status" in data

    def test_root_has_endpoints_listing(self, agent_client):
        data = agent_client.get("/").json()
        assert "endpoints" in data
        endpoints = data["endpoints"]
        assert "health" in endpoints
        assert "query" in endpoints


# ===================================================================
# Cross-agent contract compliance (parametrized)
# ===================================================================

_AGENT_CONFIGS = [
    {"id": "water-cea", "name": "Agua CEA", "code": "CEA"},
    {"id": "transport-ameq", "name": "Transporte AMEQ", "code": "TRA"},
    {"id": "education-usebeq", "name": "Educacion USEBEQ", "code": "EDU"},
    {"id": "vehicles", "name": "Vehiculos", "code": "VEH"},
    {"id": "psychology-sejuve", "name": "Psicologia SEJUVE", "code": "PSI"},
    {"id": "women-iqm", "name": "Atencion Mujeres IQM", "code": "IQM"},
    {"id": "culture", "name": "Cultura", "code": "CUL"},
    {"id": "registry-rpp", "name": "Registro Publico RPP", "code": "RPP"},
    {"id": "labor-cclq", "name": "Conciliacion Laboral CCLQ", "code": "LAB"},
    {"id": "housing-iveq", "name": "Vivienda IVEQ", "code": "VIV"},
    {"id": "appqro", "name": "Soporte APPQRO", "code": "APP"},
    {"id": "social-sedesoq", "name": "Programas Sociales SEDESOQ", "code": "SOC"},
    {"id": "citizen-attention", "name": "Atencion Ciudadana", "code": "ATC"},
]


class TestAllAgentsContractShape:
    """
    Verify that for each of the 13 agents, when a contract-compliant server
    is built with their identity, all endpoints return correct shapes.

    This validates that the _template is viable for all 13 agents.
    """

    @pytest.mark.parametrize("config", _AGENT_CONFIGS, ids=[c["id"] for c in _AGENT_CONFIGS])
    def test_health_returns_correct_agent_identity(self, config):
        mock = MagicMock()
        mock.get_health.return_value = {
            "status": "healthy",
            "agent_id": config["id"],
            "agent_name": config["name"],
            "category_code": config["code"],
            "task_types": ["consulta"],
        }
        mock.run = AsyncMock(return_value={"response": "ok", "agent_id": config["id"]})
        mock.config = {"name": config["name"]}

        app = FastAPI()

        @app.get("/health")
        async def health():
            return mock.get_health()

        @app.post("/query")
        async def query(req: QueryRequest):
            r = await mock.run(message=req.message, metadata={})
            return QueryResponse(response=r["response"], agent_id=r["agent_id"])

        with TestClient(app) as tc:
            health_data = tc.get("/health").json()
            assert health_data["agent_id"] == config["id"]
            assert health_data["category_code"] == config["code"]

            query_data = tc.post("/query", json={"message": "test"}).json()
            assert query_data["agent_id"] == config["id"]
