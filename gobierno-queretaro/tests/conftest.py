"""
PACO Test Suite - Shared fixtures and configuration.

Provides mock HTTP clients, mock Anthropic responses, sample conversation
histories, and request/response fixtures for all test modules.

IMPORTANT: This file stubs out heavy external dependencies (agentlightning,
shared.*) at the sys.modules level so tests can import orchestrator modules
without needing those packages installed.
"""

import json
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure the gobierno-queretaro root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MOCKS_DIR = Path(__file__).resolve().parent / "mocks"


# ---------------------------------------------------------------------------
# Stub external dependencies before any orchestrator imports
# ---------------------------------------------------------------------------

def _stub_module(name: str, attrs: dict | None = None) -> types.ModuleType:
    """Create and register a stub module in sys.modules."""
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _noop(*args, **kwargs):
    """No-op function for stubbing."""
    pass


def _noop_cm(*args, **kwargs):
    """No-op context manager for stubbing."""
    class _CM:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return _CM()


# agentlightning stubs
_stub_module("agentlightning")
_stub_module("agentlightning.agent", {
    "emit_annotation": _noop,
    "emit_message": _noop,
    "emit_reward": _noop,
    "operation": _noop_cm,
})

# shared stubs
_stub_module("shared")
_stub_module("shared.utils")
_stub_module("shared.utils.http_client", {
    "ResilientHTTPClient": MagicMock,
    "CircuitOpenError": type("CircuitOpenError", (Exception,), {}),
    "get_resilient_client": MagicMock,
    "get_circuit_breaker": MagicMock,
})
_stub_module("shared.security")
_stub_module("shared.security.audit", {
    "AuditEventType": MagicMock,
    "AuditLogger": MagicMock,
    "get_audit_logger": lambda: MagicMock(
        log_agent_call=AsyncMock(),
    ),
})
_stub_module("shared.tracing")
_stub_module("shared.tracing.auto_rewards", {
    "get_reward_evaluator": lambda: MagicMock(
        evaluate_routing_event=MagicMock(),
        evaluate_citizen_message=MagicMock(),
    ),
})
_stub_module("shared.tracing.setup", {
    "init_tracing": _noop,
    "shutdown_tracing": _noop,
})
_stub_module("shared.context", {
    "SessionStore": MagicMock,
    "get_session_store": MagicMock,
})
_stub_module("shared.a2a")
_stub_module("shared.a2a.card_builder", {
    "build_agent_card": MagicMock,
})
_stub_module("shared.memory", {
    "get_paco_memory": MagicMock,
})

# Also stub SecurityManager for orchestrator/main.py if it gets imported
_security_mod = sys.modules.get("shared.security")
if _security_mod:
    _security_mod.SecurityManager = MagicMock  # type: ignore
    _security_mod.get_security_manager = MagicMock  # type: ignore


# ---------------------------------------------------------------------------
# Mock data loaders
# ---------------------------------------------------------------------------

def _load_mock_xml(filename: str) -> str:
    """Load a mock XML file from mocks/cea_soap_responses/."""
    path = MOCKS_DIR / "cea_soap_responses" / filename
    return path.read_text(encoding="utf-8")


def _load_mock_json(filename: str) -> dict:
    """Load a mock JSON file from mocks/agent_responses/."""
    path = MOCKS_DIR / "agent_responses" / filename
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# CEA SOAP XML fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def deuda_success_xml() -> str:
    return _load_mock_xml("deuda_success.xml")


@pytest.fixture
def deuda_error_xml() -> str:
    return _load_mock_xml("deuda_error.xml")


@pytest.fixture
def deuda_empty_xml() -> str:
    return _load_mock_xml("deuda_empty.xml")


@pytest.fixture
def facturas_success_xml() -> str:
    return _load_mock_xml("facturas_success.xml")


@pytest.fixture
def consumos_success_xml() -> str:
    return _load_mock_xml("consumos_success.xml")


@pytest.fixture
def contrato_success_xml() -> str:
    return _load_mock_xml("contrato_success.xml")


# ---------------------------------------------------------------------------
# Agent response fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def standard_agent_response() -> dict:
    return _load_mock_json("standard_response.json")


# ---------------------------------------------------------------------------
# Mock Anthropic client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_anthropic_client():
    """
    A mock Anthropic client that returns a configurable text response.

    Usage in tests:
        client, set_response = mock_anthropic_client
        set_response("CEA")
        # now any call to client.messages.create() returns "CEA"
    """
    client = MagicMock()
    response_text = "ATC"  # default

    def _make_response(text: str):
        msg = MagicMock()
        content_block = MagicMock()
        content_block.text = text
        msg.content = [content_block]
        return msg

    def _set_response(text: str):
        nonlocal response_text
        response_text = text
        client.messages.create.return_value = _make_response(text)

    # Set default
    _set_response(response_text)

    return client, _set_response


# ---------------------------------------------------------------------------
# Mock HTTP client (httpx)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_httpx_client():
    """
    A mock httpx.AsyncClient whose .post() returns configurable responses.

    Usage:
        client, set_post = mock_httpx_client
        set_post(status_code=200, text="<xml>...</xml>")
    """
    client = AsyncMock()

    def _set_post(status_code: int = 200, text: str = "", json_data: dict | None = None):
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        if json_data is not None:
            response.json.return_value = json_data
        else:
            response.json.return_value = {}
        client.post.return_value = response
        # Also support async context manager usage
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

    _set_post()
    return client, _set_post


# ---------------------------------------------------------------------------
# Sample conversation histories
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_water_conversation() -> list[dict[str, str]]:
    """A typical water service conversation history."""
    return [
        {"role": "user", "content": "Hola, quiero consultar mi recibo de agua"},
        {"role": "assistant", "content": "Claro, dame tu numero de contrato por favor."},
        {"role": "user", "content": "Es el 123456"},
    ]


@pytest.fixture
def sample_vehicle_conversation() -> list[dict[str, str]]:
    """A typical vehicle service conversation history."""
    return [
        {"role": "user", "content": "Necesito saber cuanto debo de placas"},
        {"role": "assistant", "content": "Dame el numero de placa de tu vehiculo."},
        {"role": "user", "content": "QRO-1234"},
    ]


@pytest.fixture
def sample_ambiguous_conversation() -> list[dict[str, str]]:
    """A conversation where the last message is ambiguous."""
    return [
        {"role": "user", "content": "Quiero consultar mi agua"},
        {"role": "assistant", "content": "Tu contrato 123456 tiene un adeudo de $3,450.50"},
        {"role": "user", "content": "ok"},
    ]


# ---------------------------------------------------------------------------
# Query request fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def water_query_request() -> dict[str, Any]:
    """Standard request payload for water agent."""
    return {
        "message": "Quiero saber cuanto debo de agua, mi contrato es 123456",
        "conversation_id": "conv-test-001",
        "contact_id": "contact-test-001",
        "metadata": {
            "contract_number": "123456",
            "category": "CEA",
        },
    }


@pytest.fixture
def vehicle_query_request() -> dict[str, Any]:
    """Standard request payload for vehicle agent."""
    return {
        "message": "Consulta de adeudo para placa QRO-1234",
        "conversation_id": "conv-test-002",
        "contact_id": "contact-test-002",
        "metadata": {
            "category": "VEH",
        },
    }


# ---------------------------------------------------------------------------
# Orchestrator config mock (prevents real env/DB lookups)
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_orchestrator_settings():
    """
    Patches get_settings to return a settings object with test defaults.
    Prevents any real API key or DB URL from being required.
    """
    settings = MagicMock()
    settings.anthropic_api_key = "test-key-not-real"
    settings.model = "claude-sonnet-4-5-20250929"
    settings.classification_temperature = 0.1
    settings.database_url = "sqlite+aiosqlite:///test.db"
    settings.redis_url = "redis://localhost:6379"
    settings.agent_timeout = 5.0
    settings.agent_water_url = "http://localhost:8001"
    settings.agent_transport_url = "http://localhost:8002"
    settings.agent_education_url = "http://localhost:8003"
    settings.agent_vehicles_url = "http://localhost:8004"
    settings.agent_psychology_url = "http://localhost:8005"
    settings.agent_women_url = "http://localhost:8006"
    settings.agent_culture_url = "http://localhost:8007"
    settings.agent_registry_url = "http://localhost:8008"
    settings.agent_labor_url = "http://localhost:8009"
    settings.agent_housing_url = "http://localhost:8010"
    settings.agent_appqro_url = "http://localhost:8011"
    settings.agent_social_url = "http://localhost:8012"
    settings.agent_citizen_url = "http://localhost:8013"
    settings.registry_cache_ttl = 30
    settings.health_sweep_interval = 60

    with patch("orchestrator.config.get_settings", return_value=settings):
        yield settings
