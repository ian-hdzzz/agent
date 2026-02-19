"""
Gobierno Queretaro - Resilient HTTP Client
HTTP client with retry logic and circuit breaker pattern
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit."""

    failures: int = 0
    successes: int = 0
    last_failure: datetime | None = None
    last_success: datetime | None = None
    state: CircuitState = CircuitState.CLOSED
    state_changed_at: datetime = field(default_factory=datetime.utcnow)


class CircuitBreaker:
    """
    Circuit breaker implementation for service resilience.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service failing, requests are rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed

    Parameters:
    - failure_threshold: Number of failures before opening circuit
    - recovery_timeout: Seconds to wait before testing recovery
    - success_threshold: Successes needed in HALF_OPEN to close circuit
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._circuits: dict[str, CircuitStats] = {}

    def _get_circuit(self, service_id: str) -> CircuitStats:
        """Get or create circuit stats for a service."""
        if service_id not in self._circuits:
            self._circuits[service_id] = CircuitStats()
        return self._circuits[service_id]

    def is_available(self, service_id: str) -> bool:
        """
        Check if a service is available (circuit not open).

        Args:
            service_id: Service identifier

        Returns:
            True if requests should be allowed
        """
        circuit = self._get_circuit(service_id)

        if circuit.state == CircuitState.CLOSED:
            return True

        if circuit.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            time_since_change = datetime.utcnow() - circuit.state_changed_at
            if time_since_change.total_seconds() >= self.recovery_timeout:
                # Transition to HALF_OPEN
                circuit.state = CircuitState.HALF_OPEN
                circuit.state_changed_at = datetime.utcnow()
                circuit.successes = 0
                logger.info(f"Circuit {service_id} transitioning to HALF_OPEN")
                return True
            return False

        # HALF_OPEN - allow request
        return True

    def record_success(self, service_id: str) -> None:
        """
        Record a successful request.

        Args:
            service_id: Service identifier
        """
        circuit = self._get_circuit(service_id)
        circuit.last_success = datetime.utcnow()

        if circuit.state == CircuitState.HALF_OPEN:
            circuit.successes += 1
            if circuit.successes >= self.success_threshold:
                # Service recovered, close circuit
                circuit.state = CircuitState.CLOSED
                circuit.state_changed_at = datetime.utcnow()
                circuit.failures = 0
                logger.info(f"Circuit {service_id} CLOSED - service recovered")

        elif circuit.state == CircuitState.CLOSED:
            # Reset failure count on success
            circuit.failures = 0

    def record_failure(self, service_id: str) -> None:
        """
        Record a failed request.

        Args:
            service_id: Service identifier
        """
        circuit = self._get_circuit(service_id)
        circuit.failures += 1
        circuit.last_failure = datetime.utcnow()

        if circuit.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, re-open circuit
            circuit.state = CircuitState.OPEN
            circuit.state_changed_at = datetime.utcnow()
            logger.warning(f"Circuit {service_id} OPEN - failed during recovery")

        elif circuit.state == CircuitState.CLOSED:
            if circuit.failures >= self.failure_threshold:
                # Too many failures, open circuit
                circuit.state = CircuitState.OPEN
                circuit.state_changed_at = datetime.utcnow()
                logger.warning(
                    f"Circuit {service_id} OPEN - "
                    f"{circuit.failures} failures exceeded threshold"
                )

    def get_state(self, service_id: str) -> CircuitState:
        """Get current circuit state."""
        return self._get_circuit(service_id).state

    def get_stats(self, service_id: str) -> dict[str, Any]:
        """Get circuit statistics."""
        circuit = self._get_circuit(service_id)
        return {
            "state": circuit.state.value,
            "failures": circuit.failures,
            "successes": circuit.successes,
            "last_failure": circuit.last_failure.isoformat() if circuit.last_failure else None,
            "last_success": circuit.last_success.isoformat() if circuit.last_success else None,
            "state_changed_at": circuit.state_changed_at.isoformat(),
        }

    def reset(self, service_id: str) -> None:
        """Reset circuit to initial state."""
        self._circuits[service_id] = CircuitStats()
        logger.info(f"Circuit {service_id} reset to CLOSED")


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, service_id: str):
        self.service_id = service_id
        super().__init__(f"Circuit open for service: {service_id}")


class ResilientHTTPClient:
    """
    HTTP client with retry logic and circuit breaker.

    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker pattern for failing services
    - Configurable timeouts
    - Service-level isolation
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        """
        Initialize ResilientHTTPClient.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            circuit_breaker: Optional shared circuit breaker
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def _get_service_id(self, url: str) -> str:
        """Extract service ID from URL."""
        # Use host as service identifier
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.

        This is the core request method wrapped with tenacity retry.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

    async def request(
        self,
        method: str,
        url: str,
        service_id: str | None = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make HTTP request with circuit breaker and retry.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            service_id: Optional service identifier for circuit breaker
            **kwargs: Additional arguments passed to httpx

        Returns:
            HTTP response

        Raises:
            CircuitOpenError: If circuit is open
            RetryError: If all retries exhausted
            httpx.HTTPError: For HTTP errors after retries
        """
        service_id = service_id or self._get_service_id(url)

        # Check circuit breaker
        if not self.circuit_breaker.is_available(service_id):
            raise CircuitOpenError(service_id)

        try:
            # Create retry decorator dynamically with our settings
            @retry(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
                before_sleep=before_sleep_log(logger, logging.WARNING),
            )
            async def _request_with_retry():
                return await self._make_request(method, url, **kwargs)

            response = await _request_with_retry()
            self.circuit_breaker.record_success(service_id)
            return response

        except RetryError as e:
            self.circuit_breaker.record_failure(service_id)
            logger.error(f"All retries exhausted for {service_id}: {e}")
            raise

        except httpx.HTTPStatusError as e:
            # Record failure for 5xx errors
            if e.response.status_code >= 500:
                self.circuit_breaker.record_failure(service_id)
            raise

        except Exception as e:
            self.circuit_breaker.record_failure(service_id)
            raise

    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    async def post_json(
        self,
        url: str,
        data: dict[str, Any],
        service_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        POST JSON data and return parsed response.

        Args:
            url: Request URL
            data: JSON data to send
            service_id: Optional service identifier
            **kwargs: Additional arguments

        Returns:
            Parsed JSON response
        """
        response = await self.post(url, json=data, service_id=service_id, **kwargs)
        return response.json()

    def is_service_available(self, service_id: str) -> bool:
        """Check if a service is available."""
        return self.circuit_breaker.is_available(service_id)

    def get_service_stats(self, service_id: str) -> dict[str, Any]:
        """Get circuit statistics for a service."""
        return self.circuit_breaker.get_stats(service_id)

    def reset_service(self, service_id: str) -> None:
        """Reset circuit for a service."""
        self.circuit_breaker.reset(service_id)


# Singleton circuit breaker (shared across clients)
_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get or create the singleton CircuitBreaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker(
            failure_threshold=int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "5")),
            recovery_timeout=int(os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "30")),
            success_threshold=int(os.getenv("CIRCUIT_SUCCESS_THRESHOLD", "2")),
        )
    return _circuit_breaker


def get_resilient_client(timeout: float = 30.0, max_retries: int = 3) -> ResilientHTTPClient:
    """
    Create a ResilientHTTPClient with shared circuit breaker.

    Args:
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Configured ResilientHTTPClient
    """
    return ResilientHTTPClient(
        timeout=timeout,
        max_retries=max_retries,
        circuit_breaker=get_circuit_breaker(),
    )
