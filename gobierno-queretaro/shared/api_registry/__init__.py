"""
Gobierno Queretaro - Centralized API Registry
Unified catalog and client factory for all government service APIs.
"""

from .client import APIClientFactory, APIDefinition, get_api_client_factory

__all__ = [
    "APIClientFactory",
    "APIDefinition",
    "get_api_client_factory",
]
