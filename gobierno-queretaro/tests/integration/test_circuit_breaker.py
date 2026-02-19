"""
Integration tests for the ResilientHTTPClient and CircuitBreaker.

Tests circuit state transitions (closed -> open -> half_open -> closed),
failure threshold behaviour, recovery timeout, and the ResilientHTTPClient
retry + circuit integration.

No real HTTP calls are made; httpx is mocked at the transport level.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Import from the real shared module (stubbed at sys.modules by conftest,
# but here we test the actual code so we import from file).
import importlib.util
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# We need the real http_client code, not the stub.
# Import it directly from file.
_http_client_path = PROJECT_ROOT / "shared" / "utils" / "http_client.py"
_spec = importlib.util.spec_from_file_location(
    "shared_http_client_real",
    _http_client_path,
)
http_client_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(http_client_mod)

CircuitBreaker = http_client_mod.CircuitBreaker
CircuitState = http_client_mod.CircuitState
CircuitOpenError = http_client_mod.CircuitOpenError
CircuitStats = http_client_mod.CircuitStats
ResilientHTTPClient = http_client_mod.ResilientHTTPClient


# ===================================================================
# CircuitBreaker - State Transitions
# ===================================================================

class TestCircuitBreakerStates:
    """Test circuit breaker state machine."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker()
        assert cb.get_state("svc") == CircuitState.CLOSED

    def test_service_available_when_closed(self):
        cb = CircuitBreaker()
        assert cb.is_available("svc") is True

    def test_stays_closed_under_threshold(self):
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.CLOSED

    def test_opens_at_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.OPEN

    def test_service_unavailable_when_open(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("svc")
        cb.record_failure("svc")
        assert cb.is_available("svc") is False

    def test_transitions_to_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0)
        cb.record_failure("svc")
        cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.OPEN

        # With recovery_timeout=0, next is_available check transitions
        assert cb.is_available("svc") is True
        assert cb.get_state("svc") == CircuitState.HALF_OPEN

    def test_half_open_closes_after_success_threshold(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0, success_threshold=2)
        # Open it
        cb.record_failure("svc")
        cb.record_failure("svc")
        # Transition to half-open
        cb.is_available("svc")
        assert cb.get_state("svc") == CircuitState.HALF_OPEN

        # Record successes
        cb.record_success("svc")
        assert cb.get_state("svc") == CircuitState.HALF_OPEN  # not yet
        cb.record_success("svc")
        assert cb.get_state("svc") == CircuitState.CLOSED  # recovered

    def test_half_open_reopens_on_failure(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0, success_threshold=3)
        # Open it
        cb.record_failure("svc")
        cb.record_failure("svc")
        # Transition to half-open
        cb.is_available("svc")
        assert cb.get_state("svc") == CircuitState.HALF_OPEN

        # One success, then failure -> re-open
        cb.record_success("svc")
        cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.OPEN

    def test_success_resets_failure_count_when_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure("svc")
        cb.record_failure("svc")
        # Almost at threshold but success resets
        cb.record_success("svc")
        cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.CLOSED  # only 1 failure after reset


# ===================================================================
# CircuitBreaker - Multiple Services
# ===================================================================

class TestCircuitBreakerIsolation:
    """Test that circuits are isolated per service."""

    def test_different_services_independent(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("svc-a")
        cb.record_failure("svc-a")
        assert cb.get_state("svc-a") == CircuitState.OPEN
        assert cb.get_state("svc-b") == CircuitState.CLOSED

    def test_one_service_failure_doesnt_affect_others(self):
        cb = CircuitBreaker(failure_threshold=2)
        for _ in range(5):
            cb.record_failure("svc-a")
        cb.record_success("svc-b")
        assert cb.is_available("svc-b") is True


# ===================================================================
# CircuitBreaker - Stats and Reset
# ===================================================================

class TestCircuitBreakerStats:
    """Test stats reporting and reset."""

    def test_get_stats_fields(self):
        cb = CircuitBreaker()
        cb.record_failure("svc")
        cb.record_success("svc")
        stats = cb.get_stats("svc")
        assert "state" in stats
        assert "failures" in stats
        assert "successes" in stats
        assert "last_failure" in stats
        assert "last_success" in stats
        assert "state_changed_at" in stats

    def test_stats_reflect_current_state(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("svc")
        cb.record_failure("svc")
        stats = cb.get_stats("svc")
        assert stats["state"] == "open"
        assert stats["failures"] == 2

    def test_reset_restores_closed(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure("svc")
        cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.OPEN

        cb.reset("svc")
        assert cb.get_state("svc") == CircuitState.CLOSED
        assert cb.is_available("svc") is True


# ===================================================================
# CircuitBreaker - Recovery Timeout (non-zero)
# ===================================================================

class TestCircuitBreakerRecoveryTimeout:
    """Test that circuit stays open until recovery timeout elapses."""

    def test_stays_open_before_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb.record_failure("svc")
        cb.record_failure("svc")
        # Still within timeout
        assert cb.is_available("svc") is False

    def test_transitions_after_timeout_by_manipulating_timestamp(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
        cb.record_failure("svc")
        cb.record_failure("svc")
        assert cb.get_state("svc") == CircuitState.OPEN

        # Manually backdate the state_changed_at to simulate timeout passing
        circuit = cb._get_circuit("svc")
        circuit.state_changed_at = datetime.utcnow() - timedelta(seconds=15)

        assert cb.is_available("svc") is True
        assert cb.get_state("svc") == CircuitState.HALF_OPEN


# ===================================================================
# ResilientHTTPClient - Circuit Integration
# ===================================================================

class TestResilientHTTPClient:
    """Test ResilientHTTPClient with circuit breaker integration."""

    def test_raises_circuit_open_error(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("localhost:9999")
        client = ResilientHTTPClient(circuit_breaker=cb, max_retries=1)
        assert client.is_service_available("localhost:9999") is False

    def test_service_available_when_closed(self):
        cb = CircuitBreaker()
        client = ResilientHTTPClient(circuit_breaker=cb)
        assert client.is_service_available("test-service") is True

    @pytest.mark.asyncio
    async def test_circuit_open_raises_on_post(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("test-svc")
        client = ResilientHTTPClient(circuit_breaker=cb, max_retries=1)

        with pytest.raises(CircuitOpenError):
            await client.post("http://test-svc/query", service_id="test-svc")

    @pytest.mark.asyncio
    async def test_successful_request_records_success(self):
        cb = CircuitBreaker()
        client = ResilientHTTPClient(circuit_breaker=cb, max_retries=1)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            await client.post("http://localhost:8001/query", service_id="agent-a")

        stats = cb.get_stats("agent-a")
        assert stats["last_success"] is not None

    @pytest.mark.asyncio
    async def test_5xx_error_records_failure(self):
        cb = CircuitBreaker()
        client = ResilientHTTPClient(circuit_breaker=cb, max_retries=1)

        mock_response = MagicMock()
        mock_response.status_code = 500
        exc = httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response)
        mock_response.raise_for_status.side_effect = exc

        with patch.object(client, "_make_request", new_callable=AsyncMock, side_effect=exc):
            with pytest.raises(httpx.HTTPStatusError):
                await client.post("http://localhost:8001/query", service_id="agent-a")

        stats = cb.get_stats("agent-a")
        assert stats["failures"] == 1

    def test_get_service_stats(self):
        cb = CircuitBreaker()
        client = ResilientHTTPClient(circuit_breaker=cb)
        stats = client.get_service_stats("test-svc")
        assert stats["state"] == "closed"

    def test_reset_service(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure("svc")
        client = ResilientHTTPClient(circuit_breaker=cb)
        assert not client.is_service_available("svc")

        client.reset_service("svc")
        assert client.is_service_available("svc")


# ===================================================================
# Full Cycle: Closed -> Open -> Half-Open -> Closed
# ===================================================================

class TestFullCircuitCycle:
    """Test the complete lifecycle of a circuit breaker."""

    def test_full_lifecycle(self):
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=0,  # instant recovery for testing
            success_threshold=2,
        )
        svc = "agent-water"

        # Phase 1: CLOSED, accumulating failures
        assert cb.get_state(svc) == CircuitState.CLOSED
        cb.record_failure(svc)
        cb.record_failure(svc)
        assert cb.get_state(svc) == CircuitState.CLOSED  # still under threshold

        # Phase 2: Hits threshold -> OPEN
        cb.record_failure(svc)
        assert cb.get_state(svc) == CircuitState.OPEN

        # Phase 3: Recovery timeout is 0s so is_available immediately
        # transitions to HALF_OPEN
        assert cb.is_available(svc) is True
        assert cb.get_state(svc) == CircuitState.HALF_OPEN

        # Phase 4: First success in HALF_OPEN
        cb.record_success(svc)
        assert cb.get_state(svc) == CircuitState.HALF_OPEN

        # Phase 5: Second success meets threshold -> CLOSED
        cb.record_success(svc)
        assert cb.get_state(svc) == CircuitState.CLOSED
        assert cb.is_available(svc) is True

        # Phase 6: Verify clean state
        stats = cb.get_stats(svc)
        assert stats["state"] == "closed"
        assert stats["failures"] == 0

    def test_half_open_failure_cycle(self):
        """Test that failing in HALF_OPEN re-opens and requires another timeout."""
        cb = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0,
            success_threshold=3,
        )
        svc = "agent-transport"

        # Open the circuit
        cb.record_failure(svc)
        cb.record_failure(svc)
        assert cb.get_state(svc) == CircuitState.OPEN

        # Transition to HALF_OPEN
        cb.is_available(svc)
        assert cb.get_state(svc) == CircuitState.HALF_OPEN

        # Fail during recovery -> back to OPEN
        cb.record_failure(svc)
        assert cb.get_state(svc) == CircuitState.OPEN

        # Need another recovery period
        # (recovery_timeout=0 so immediate)
        cb.is_available(svc)
        assert cb.get_state(svc) == CircuitState.HALF_OPEN

        # This time succeed enough times
        cb.record_success(svc)
        cb.record_success(svc)
        cb.record_success(svc)
        assert cb.get_state(svc) == CircuitState.CLOSED
