"""Shared authentication utilities for Gobierno Queretaro services."""

from .jwt_validator import validate_paco_jwt

__all__ = ["validate_paco_jwt"]
