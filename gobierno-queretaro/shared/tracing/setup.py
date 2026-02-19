"""
Gobierno Querétaro - Agent-Lightning Tracing Setup
Centralized initialization for tracing across all services (orchestrator + agents).

Usage:
    from shared.tracing.setup import init_tracing, get_store

    # In service startup:
    tracer, store = init_tracing("orchestrator")

    # In request handlers, use agent-lightning emitters directly:
    from agentlightning.agent import emit_message, emit_annotation, emit_reward, operation
"""

import logging
import os

import agentlightning as agl
from agentlightning.store import InMemoryLightningStore, LightningStoreServer

logger = logging.getLogger(__name__)

_store = None
_tracer = None
_store_server = None


def init_tracing(
    service_name: str,
    otlp_endpoint: str | None = None,
    enable_server: bool = False,
    server_port: int = 4318,
) -> tuple:
    """
    Initialize agent-lightning tracing for a service.

    Args:
        service_name: Name of the service (e.g., "orchestrator", "agent-vehicles")
        otlp_endpoint: Optional OTLP endpoint for exporting traces (e.g., Jaeger).
                       If None, uses OTLP_ENDPOINT env var or defaults to in-memory only.
        enable_server: Whether to start an HTTP server exposing the store for remote access.
        server_port: Port for the store server if enabled.

    Returns:
        Tuple of (tracer_configured: bool, store: InMemoryLightningStore)
    """
    global _store, _tracer, _store_server

    if _store is not None:
        logger.debug(f"Tracing already initialized for {service_name}")
        return _tracer, _store

    # Resolve OTLP endpoint from env if not provided
    otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")

    # Initialize the store (in-memory for Phase 1, persistent backend later)
    _store = InMemoryLightningStore()
    logger.info(f"Initialized InMemoryLightningStore for {service_name}")

    # Set up logging
    agl.setup_logging()

    # If OTLP endpoint is provided, configure export
    # The store server can accept OTLP traces at /v1/traces
    if enable_server:
        _store_server = LightningStoreServer(store=_store, port=server_port)
        _store_server.start()
        logger.info(f"LightningStore server started on port {server_port}")

    _tracer = True  # Tracing is configured via agentlightning global state
    logger.info(
        f"Agent-Lightning tracing initialized for {service_name}"
        + (f" (OTLP endpoint: {otlp_endpoint})" if otlp_endpoint else "")
    )

    return _tracer, _store


def get_store() -> InMemoryLightningStore | None:
    """Get the current LightningStore instance."""
    return _store


def get_tracer():
    """Get the current tracer state."""
    return _tracer


async def shutdown_tracing():
    """Gracefully shut down tracing components."""
    global _store_server
    if _store_server is not None:
        _store_server.stop()
        _store_server = None
        logger.info("LightningStore server stopped")
