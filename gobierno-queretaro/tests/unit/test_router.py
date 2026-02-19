"""
Unit tests for orchestrator.router

Tests context continuity, exit handling, error handling, and routing decisions.
All HTTP calls and LLM calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from orchestrator.router import (
    OrchestratorState,
    classify_intent_node,
    handle_error,
    handle_exit,
    route_to_agent,
    should_handle_error,
)


# ===================================================================
# Helpers
# ===================================================================

def _make_state(
    user_messages: list[str] | None = None,
    detected_category: str | None = None,
    metadata: dict | None = None,
    contract_number: str | None = None,
    error: str | None = None,
) -> OrchestratorState:
    """Build an OrchestratorState dict for testing."""
    messages = []
    if user_messages:
        for msg in user_messages:
            messages.append(HumanMessage(content=msg))
    return {
        "messages": messages,
        "detected_category": detected_category,
        "agent_response": None,
        "agent_id": None,
        "contract_number": contract_number,
        "task_type": None,
        "metadata": metadata or {},
        "error": error,
    }


# Patch all tracing helpers that are not relevant for unit tests
_TRACING_PATCHES = [
    "orchestrator.router.emit_annotation",
    "orchestrator.router.emit_message",
    "orchestrator.router.emit_reward",
    "orchestrator.router.operation",
    "orchestrator.router.get_reward_evaluator",
    "orchestrator.router.get_audit_logger",
]


def _noop_operation(**kwargs):
    """A no-op context manager replacement for operation()."""
    class _NoOp:
        def __enter__(self): return self
        def __exit__(self, *a): pass
    return _NoOp()


# ===================================================================
# classify_intent_node
# ===================================================================

class TestClassifyIntentNode:
    """Test the classification node of the orchestrator graph."""

    @pytest.mark.asyncio
    async def test_empty_messages_returns_atc(self):
        state = _make_state(user_messages=[])
        with patch("orchestrator.router.operation", side_effect=_noop_operation):
            result = await classify_intent_node(state)
        assert result["detected_category"] == "ATC"
        assert result.get("error") is not None

    @pytest.mark.asyncio
    async def test_context_continuity_ambiguous_message(self):
        """Ambiguous message with last_category should stay with that agent."""
        state = _make_state(
            user_messages=["ok"],
            metadata={"last_category": "CEA"},
        )
        with patch("orchestrator.router.operation", side_effect=_noop_operation), \
             patch("orchestrator.router.emit_annotation"), \
             patch("orchestrator.router.emit_message"):
            result = await classify_intent_node(state)

        assert result["detected_category"] == "CEA"

    @pytest.mark.asyncio
    async def test_context_continuity_preserves_contract(self):
        """When continuing with context, contract_number should be preserved."""
        state = _make_state(
            user_messages=["si"],
            metadata={"last_category": "CEA"},
            contract_number="123456",
        )
        with patch("orchestrator.router.operation", side_effect=_noop_operation), \
             patch("orchestrator.router.emit_annotation"), \
             patch("orchestrator.router.emit_message"):
            result = await classify_intent_node(state)

        assert result["contract_number"] == "123456"

    @pytest.mark.asyncio
    async def test_clear_message_reclassifies(self):
        """Clear messages should be reclassified even with last_category set."""
        state = _make_state(
            user_messages=["Necesito consultar mis placas y la tenencia de mi vehiculo"],
            metadata={"last_category": "CEA"},
        )
        with patch("orchestrator.router.operation", side_effect=_noop_operation), \
             patch("orchestrator.router.emit_annotation"), \
             patch("orchestrator.router.emit_message"), \
             patch("orchestrator.router.classify_intent", new_callable=AsyncMock) as mock_ci:
            mock_ci.return_value = {
                "category": "VEH",
                "confidence": 0.85,
                "method": "keyword",
            }
            result = await classify_intent_node(state)

        assert result["detected_category"] == "VEH"

    @pytest.mark.asyncio
    async def test_extracts_contract_number(self):
        """Contract numbers should be extracted from user messages."""
        state = _make_state(
            user_messages=["Mi contrato es 1234567"],
        )
        with patch("orchestrator.router.operation", side_effect=_noop_operation), \
             patch("orchestrator.router.emit_annotation"), \
             patch("orchestrator.router.emit_message"), \
             patch("orchestrator.router.classify_intent", new_callable=AsyncMock) as mock_ci:
            mock_ci.return_value = {
                "category": "CEA",
                "confidence": 0.85,
                "method": "keyword",
            }
            result = await classify_intent_node(state)

        assert result["contract_number"] == "1234567"


# ===================================================================
# route_to_agent
# ===================================================================

class TestRouteToAgent:
    """Test the routing decision node."""

    def test_route_exit(self):
        state = _make_state(detected_category="EXIT")
        assert route_to_agent(state) == "handle_exit"

    def test_route_to_agent_for_normal_category(self):
        state = _make_state(detected_category="CEA")
        assert route_to_agent(state) == "call_agent"

    def test_route_defaults_to_agent_when_none(self):
        state = _make_state(detected_category=None)
        # Defaults to ATC, which routes to call_agent
        assert route_to_agent(state) == "call_agent"

    @pytest.mark.parametrize("category", [
        "CEA", "TRA", "EDU", "VEH", "PSI", "IQM",
        "CUL", "RPP", "LAB", "VIV", "APP", "SOC", "ATC",
    ])
    def test_all_non_exit_categories_route_to_call_agent(self, category):
        state = _make_state(detected_category=category)
        assert route_to_agent(state) == "call_agent"


# ===================================================================
# handle_exit
# ===================================================================

class TestHandleExit:
    """Test exit/farewell handling."""

    def test_exit_returns_farewell(self):
        state = _make_state()
        result = handle_exit(state)
        assert "Gracias" in result["agent_response"]
        assert result["agent_id"] == "orchestrator"
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)


# ===================================================================
# handle_error
# ===================================================================

class TestHandleError:
    """Test error handling node."""

    def test_error_with_message(self):
        state = _make_state(error="Connection refused")
        result = handle_error(state)
        assert "problema" in result["agent_response"].lower()

    def test_error_without_message(self):
        state = _make_state(error=None)
        result = handle_error(state)
        assert "reformular" in result["agent_response"].lower()


# ===================================================================
# should_handle_error
# ===================================================================

class TestShouldHandleError:
    """Test error-check conditional edge."""

    def test_with_error_routes_to_handle_error(self):
        state = _make_state(error="something went wrong")
        assert should_handle_error(state) == "handle_error"

    def test_without_error_routes_to_end(self):
        state = _make_state(error=None)
        assert should_handle_error(state) == "end"
